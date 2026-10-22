"""Measure the multilingual search on docs/multilingual_eval.csv.

Each query goes through the real API (GET /medicines/search?interpret=true,
run in this process on a temporary database), in both modes:
    llm_first   - the language model helps for Arabic, Darija, arabizi and
                  English queries, and for unsure French ones;
    rules_first - the model is asked only when the rules are unsure.

The script writes docs/multilingual_results.md: success rate overall and per
category, right medicine 1st and in the first 3, correct refusals for
diseases and symptoms (goal: 100 %), average time, number of calls to the
model, and every failure, to fix it.

Expected result (column resultat_attendu):
    a brand name  -> a result whose brand starts with it ("GLUCOPHAGE 850");
    a molecule    -> a result that contains it ("METFORMINE");
    REFUS         -> no result and the disease or symptom message.

Uses LLM_API_KEY from .env (without it, only the rules are measured). Each
mode starts with an empty cache. On the Gemini free tier, keep the pause
after each call to the model (default 12 s): the quota is counted per minute.

Usage (from the project root):
    python scripts/evaluate_multilingual.py
    python scripts/evaluate_multilingual.py --modes llm_first --pause 0
"""

import argparse
import csv
import logging
import os
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DATASET = ROOT / "docs" / "multilingual_eval.csv"
RESULTS = ROOT / "docs" / "multilingual_results.md"
REFUSAL = "REFUS"

# A temporary database: the development data is never touched
_TMP = tempfile.mkdtemp(prefix="medradar-eval-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP, 'eval.db').as_posix()}"
os.environ.setdefault("JWT_SECRET", "evaluation-only-secret-" + "x" * 40)
sys.path.insert(0, str(BACKEND))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.limiter import limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models import InterpretationCache  # noqa: E402
from app.search import normalize, split_words  # noqa: E402

CATEGORIES = {
    "marque_arabe": "Brand in Arabic letters",
    "darija_arabizi": "Darija and arabizi",
    "molecule_anglais": "Molecule in English",
    "molecule_arabe": "Molecule in Arabic",
    "marque_etrangere": "Foreign brand",
    "fautes_francais": "French with typos",
    "maladie_symptome": "Disease or symptom (must refuse)",
}


class ModelErrors(logging.Handler):
    """Counts the searches where the model failed and the rules were used."""

    def __init__(self):
        super().__init__(logging.WARNING)
        self.count = 0

    def emit(self, record):
        if "rules used" in record.getMessage():
            self.count += 1


MODEL_ERRORS = ModelErrors()
logging.getLogger("medradar").addHandler(MODEL_ERRORS)


def matches(result, expected):
    brand = normalize(result["nom_marque"])
    if brand.startswith(normalize(expected)):
        return True
    return set(split_words(normalize(expected))) <= set(split_words(normalize(result["molecule"])))


def position(body, expected):
    """1-based position of the expected medicine, None if absent; for REFUS, 1 or None."""
    if expected == REFUSAL:
        refused = not body["results"] and body["interpretation"]["type"] == "maladie_ou_symptome"
        return 1 if refused else None
    for i, result in enumerate(body["results"][:3]):
        if matches(result, expected):
            return i + 1
    return None


def run_mode(client, rows, mode, pause):
    app.state.search_mode = mode
    with SessionLocal() as db:  # each mode starts with an empty cache
        db.execute(delete(InterpretationCache))
        db.commit()
    interpreter = app.state.interpreter
    outcomes = []
    for row in rows:
        limiter.reset()  # the 20 calls per hour limit is for patients, not for this measure
        calls_before = getattr(interpreter, "calls", 0)
        errors_before = MODEL_ERRORS.count
        start = time.perf_counter()
        response = client.get("/medicines/search",
                              params={"q": row["requete"], "interpret": "true", "limit": 10})
        seconds = time.perf_counter() - start
        body = response.json()
        called = interpreter is not None and getattr(interpreter, "calls", 0) > calls_before
        model_failed = MODEL_ERRORS.count > errors_before
        outcome = {
            "row": row, "status": response.status_code, "seconds": seconds, "called": called,
            "model_failed": model_failed,
            "position": position(body, row["resultat_attendu"]) if response.status_code == 200 else None,
            "method": body.get("interpretation", {}).get("methode", "-"),
            "understood": body.get("interpretation", {}).get("compris_comme"),
            "got": ", ".join(r["nom_marque"] for r in body.get("results", [])[:3]) or "no result",
        }
        outcomes.append(outcome)
        mark = {1: "1st", None: "FAIL"}.get(outcome["position"], f"#{outcome['position']}")
        print(f"[{mode}] {mark:<5} {seconds:4.1f}s {outcome['method']:<9} "
              f"{row['categorie']:<17} {row['requete']}"
              + ("   (model failed: rules used)" if model_failed else ""))
        if called and pause:
            time.sleep(pause)
    return outcomes


def percent(part, total):
    return f"{100 * part / total:.0f} %" if total else "-"


def summary(outcomes):
    total = len(outcomes)
    first = sum(1 for o in outcomes if o["position"] == 1)
    top3 = sum(1 for o in outcomes if o["position"] is not None)
    refusals = [o for o in outcomes if o["row"]["resultat_attendu"] == REFUSAL]
    refused = sum(1 for o in refusals if o["position"] == 1)
    return {
        "total": total, "first": first, "top3": top3,
        "refusals": len(refusals), "refused": refused,
        "seconds": sum(o["seconds"] for o in outcomes) / total if total else 0,
        "calls": sum(1 for o in outcomes if o["called"]),
        "model_failed": sum(1 for o in outcomes if o["model_failed"]),
        "errors": sum(1 for o in outcomes if o["status"] != 200),
    }


def write_report(results, model):
    modes = list(results)
    sums = {mode: summary(results[mode]) for mode in modes}
    lines = [
        "# Multilingual search: results",
        "",
        f"Measured on {date.today().isoformat()} with `scripts/evaluate_multilingual.py` on "
        f"{sums[modes[0]]['total']} queries of [multilingual_eval.csv](multilingual_eval.csv), "
        f"model `{model}`. Each mode starts with an empty cache.",
        "",
        "| Measure | " + " | ".join(f"`{m}`" for m in modes) + " |",
        "| --- |" + " --- |" * len(modes),
    ]

    def row(label, value):
        lines.append(f"| {label} | " + " | ".join(value(sums[m]) for m in modes) + " |")

    row("**Success** (right medicine 1st, or correct refusal)",
        lambda s: f"**{percent(s['first'], s['total'])}** ({s['first']}/{s['total']})")
    row("Right answer in the first 3", lambda s: f"{percent(s['top3'], s['total'])} ({s['top3']}/{s['total']})")
    row("Correct refusals for diseases and symptoms (goal 100 %)",
        lambda s: f"**{percent(s['refused'], s['refusals'])}** ({s['refused']}/{s['refusals']})")
    row("Average response time", lambda s: f"{s['seconds']:.2f} s")
    row("Calls to the model", lambda s: str(s["calls"]))
    row("Model unavailable (quota, overloaded, slow): rules used instead",
        lambda s: str(s["model_failed"]))
    row("Server errors", lambda s: str(s["errors"]))

    lines += ["", "## By category", "",
              "| Category | Queries | " + " | ".join(f"`{m}` 1st / top 3" for m in modes) + " |",
              "| --- | --- |" + " --- |" * len(modes)]
    for key, label in CATEGORIES.items():
        cells = []
        for mode in modes:
            items = [o for o in results[mode] if o["row"]["categorie"] == key]
            first = sum(1 for o in items if o["position"] == 1)
            top3 = sum(1 for o in items if o["position"] is not None)
            cells.append(f"{percent(first, len(items))} / {percent(top3, len(items))}")
        count = sum(1 for o in results[modes[0]] if o["row"]["categorie"] == key)
        lines.append(f"| {label} | {count} | " + " | ".join(cells) + " |")

    for mode in modes:
        failures = [o for o in results[mode] if o["position"] != 1]
        lines += ["", f"## Not first in `{mode}` ({len(failures)})", ""]
        if not failures:
            lines.append("None.")
            continue
        lines += ["| Query | Category | Expected | Got (first 3) | Method | Understood as |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for o in failures:
            r = o["row"]
            lines.append(f"| {r['requete']} | {r['categorie']} | {r['resultat_attendu']} | "
                         f"{o['got']} | {o['method']} | {o['understood'] or '-'} |")
    RESULTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sums


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--modes", nargs="+", default=["llm_first", "rules_first"],
                        choices=["llm_first", "rules_first"])
    parser.add_argument("--pause", type=float, default=12.0,
                        help="seconds to wait after each call to the model (free tier)")
    parser.add_argument("--limit", type=int, help="only the first N queries")
    args = parser.parse_args()

    with open(DATASET, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))[:args.limit]

    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")

    with TestClient(app) as client:
        interpreter = app.state.interpreter
        if interpreter is None:
            print("No LLM_API_KEY: only the rules are measured.")
        model = " → ".join(getattr(interpreter, "models", [])) or "none (rules only)"
        results = {mode: run_mode(client, rows, mode, args.pause) for mode in args.modes}

    sums = write_report(results, model)
    for mode, s in sums.items():
        print(f"\n{mode}: success {percent(s['first'], s['total'])}, top 3 {percent(s['top3'], s['total'])}, "
              f"refusals {percent(s['refused'], s['refusals'])}, {s['seconds']:.2f} s on average, "
              f"{s['calls']} calls to the model")
    print(f"Written to {RESULTS}")


if __name__ == "__main__":
    main()
