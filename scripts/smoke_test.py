"""Check that the online version of MedRadar works, from the outside.

Waits for the API to wake up (free plan: up to about a minute), then checks the
API, the site and the link between them. Nothing is written in the database,
except the demo pharmacist login. One line per check, and exit code 1 if one fails.

Usage:
    python scripts/smoke_test.py https://medradar-api.onrender.com https://medradar.vercel.app

The demo login uses DEMO_PHARMACIST_EMAIL (default pharmacien1@medradar.demo) and
DEMO_PHARMACIST_PASSWORD from the environment.
"""

import os
import sys
import time

import httpx

GLUCOPHAGE_850 = "55c9557e1e81"
ORAN = {"lat": 35.697, "lng": -0.633}
WAKE_SECONDS = 90
# Not counted in the search statistics (see backend/app/routers/public.py)
CHECK_HEADERS = {"X-MedRadar-Check": "1", "User-Agent": "medradar-smoke-test"}
PERSONAL_FIELDS = ("email", "numero_professionnel", "professional_number", "owner_id",
                   "proprietaire", "mot_de_passe", "password_hash")

results = []


def check(name):
    """Decorator: runs the check, prints ✅ or ❌ with the reason."""
    def run(function):
        try:
            detail = function()
            ok = True
        except Exception as error:  # every failure is reported, the next checks still run
            detail, ok = f"{type(error).__name__}: {error}", False
        results.append(ok)
        print(f"{'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else ""), flush=True)
        return function
    return run


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def wake_up(api):
    """Call /health until it answers, for up to 90 s (Render, then Neon, wake up)."""
    start = time.monotonic()
    while True:
        try:
            response = api.get("/health", timeout=30)
            if response.status_code == 200:
                return time.monotonic() - start
        except httpx.HTTPError:
            pass
        if time.monotonic() - start > WAKE_SECONDS:
            return None
        time.sleep(5)


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python scripts/smoke_test.py <API URL> <SITE URL>")
    api_url, site_url = (url.rstrip("/") for url in sys.argv[1:])
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # ✅ and ❌ on Windows too

    api = httpx.Client(base_url=api_url, headers=CHECK_HEADERS, timeout=30)
    site = httpx.Client(base_url=site_url, headers=CHECK_HEADERS, timeout=30, follow_redirects=True)
    print(f"API  : {api_url}\nSite : {site_url}\n")

    @check("The API answers (woken up if it was asleep)")
    def _():
        seconds = wake_up(api)
        expect(seconds is not None, f"no answer after {WAKE_SECONDS} s")
        return f"{seconds:.0f} s"

    @check("/health")
    def _():
        body = api.get("/health").json()
        expect(body["status"] == "ok", body)
        expect(body["medicines"] > 4000, f"only {body['medicines']} medicines loaded")
        on = [name for name, value in body["features"].items() if value]
        return f"{body['medicines']} medicines, version {body['version']}, AI on: {', '.join(on) or 'none'}"

    @check("/health/deep (database)")
    def _():
        response = api.get("/health/deep", timeout=60)
        expect(response.status_code == 200, f"{response.status_code} {response.text[:200]}")
        return f"database answered in {response.json()['database_ms']} ms"

    @check("Search with a typo: “glucofage” finds GLUCOPHAGE")
    def _():
        found = api.get("/medicines/search", params={"q": "glucofage"}).json()
        names = [m["nom_marque"] for m in found]
        expect(any(n.startswith("GLUCOPHAGE") for n in names), names)

    @check("GLUCOPHAGE 850 has 13 equivalents")
    def _():
        body = api.get(f"/medicines/{GLUCOPHAGE_850}/equivalents").json()
        expect(body["count"] == 13, f"{body['count']} equivalents")

    @check("Availability: pharmacies sorted by distance")
    def _():
        body = api.get(f"/medicines/{GLUCOPHAGE_850}/availability", params=ORAN).json()
        lists = [g[kind] for g in body["resultats"] for kind in ("en_stock", "rupture")]
        expect(any(lists), "no pharmacy at all: run the demo reset (docs/deployment.md)")
        for entries in lists:
            distances = [e["distance_km"] for e in entries]
            expect(distances == sorted(distances), f"not sorted: {distances}")
        return f"{sum(map(len, lists))} answers, {body['nb_pharmacies_en_stock']} pharmacies with it in stock"

    @check("/pharmacies shows no personal data")
    def _():
        response = api.get("/pharmacies")
        pharmacies = response.json()
        expect(pharmacies, "no validated pharmacy")
        expect("@" not in response.text, "an email address is visible")
        leaked = {f for p in pharmacies for f in PERSONAL_FIELDS if f in p}
        expect(not leaked, f"personal fields: {leaked}")
        return f"{len(pharmacies)} pharmacies"

    @check("Demo pharmacist login")
    def _():
        email = os.environ.get("DEMO_PHARMACIST_EMAIL", "").strip() or "pharmacien1@medradar.demo"
        password = os.environ.get("DEMO_PHARMACIST_PASSWORD", "")
        expect(password, "DEMO_PHARMACIST_PASSWORD is not set")
        response = api.post("/auth/login", json={"email": email, "mot_de_passe": password})
        expect(response.status_code == 200, f"{response.status_code} {response.text[:200]}")
        token = response.json()["access_token"]
        me = api.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        expect(me["utilisateur"]["role"] == "pharmacien", me["utilisateur"]["role"])
        pharmacy = me["pharmacie"]
        return f"{email}, {pharmacy['nom']} ({pharmacy['statut']})" if pharmacy else email

    for path in ("/", "/demo", f"/medicament/{GLUCOPHAGE_850}"):
        @check(f"Site page {path}")
        def _(path=path):
            response = site.get(path)
            expect(response.status_code == 200, response.status_code)
            expect("MedRadar" in response.text, "MedRadar is not in the page")

    @check("CORS: the API accepts the site")
    def _():
        response = api.options("/medicines/search", headers={
            "Origin": site_url, "Access-Control-Request-Method": "GET"})
        allowed = response.headers.get("access-control-allow-origin")
        expect(allowed == site_url, f"allowed: {allowed!r}; set FRONTEND_URL={site_url} on Render")

    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
