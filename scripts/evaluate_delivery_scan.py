"""Measure the delivery note scan on real photos (or the demo note).

Each note to measure has:
    docs/delivery_samples/photos/<note>.jpg      (or <note>_1.jpg, <note>_2.jpg... for pages;
                                                   this folder is never committed)
    docs/delivery_samples/<note>.expected.csv    designation,nom_marque_attendu,dosage_attendu,livre
                                                   (nom_marque_attendu empty for parapharmacy,
                                                   livre = oui / non)
    docs/delivery_samples/<note>.document.json   {"fournisseur": ..., "numero_bon": ...,
                                                  "date_bon": "YYYY-MM-DD"}   (optional)

With --demo, the demo note (frontend/public/demo/, sharp and photo-like) is
measured against its known content (backend/app/delivery/demo_note.py).

Each note goes through the REAL reading (same preparation, model and matching
as the API). The script writes docs/delivery_scan_results.md: lines read,
exact matches, false positives (a wrong medicine ticked by default: the most
serious error), back orders detected, supplier, number and date read, and the
average time. Needs LLM_API_KEY in .env.

Usage (from the project root):
    python scripts/evaluate_delivery_scan.py --demo
    python scripts/evaluate_delivery_scan.py            (notes in docs/delivery_samples)
"""

import argparse
import csv
import json
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.data import load_store  # noqa: E402
from app.delivery import make_delivery_reader  # noqa: E402
from app.delivery import demo_note  # noqa: E402
from app.delivery.matching import EXACT, NOT_DELIVERED, LineMatcher  # noqa: E402
from app.delivery.reader import read_note  # noqa: E402
from app.images import ImageRejected, prepare_image  # noqa: E402
from app.llm.errors import LLMError, LLMTimeout, ProviderBusy  # noqa: E402
from app.routers.delivery import MAX_PAGE_BYTES, MAX_SIDE  # noqa: E402
from app.search import SearchIndex, normalize  # noqa: E402

SAMPLES = ROOT / "docs" / "delivery_samples"
PHOTOS = SAMPLES / "photos"
DEMO = ROOT / "frontend" / "public" / "demo"
RESULTS = ROOT / "docs" / "delivery_scan_results.md"
SAME_LINE = 80  # a read designation is "the same line" from this similarity (0-100)


def simple(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).upper().split())


def demo_notes():
    expected = [{"designation": d, "nom_marque_attendu": brand, "dosage_attendu": dose,
                 "livre": "oui" if status == "livre" else "non"}
                for d, _q, _b, _e, _p, status, brand, dose in demo_note.LINES]
    document = {"fournisseur": demo_note.SUPPLIER, "numero_bon": demo_note.NOTE_NUMBER,
                "date_bon": demo_note.NOTE_DATE}
    return [("demo (sharp)", [DEMO / "bon-livraison-demo-net.png"], expected, document),
            ("demo (photo-like, tilted)", [DEMO / "bon-livraison-demo.png"], expected, document)]


def sample_notes():
    notes = []
    for csv_path in sorted(SAMPLES.glob("*.expected.csv")):
        name = csv_path.name.removesuffix(".expected.csv")
        pages = sorted(PHOTOS.glob(f"{name}.*")) or sorted(PHOTOS.glob(f"{name}_*.*"))
        with open(csv_path, encoding="utf-8", newline="") as f:
            expected = list(csv.DictReader(f))
        doc_path = SAMPLES / f"{name}.document.json"
        document = json.loads(doc_path.read_text(encoding="utf-8")) if doc_path.exists() else {}
        notes.append((name, pages, expected, document))
    return notes


def is_expected(medicine, row):
    return (medicine is not None
            and normalize(medicine["nom_marque"]).startswith(normalize(row["nom_marque_attendu"]))
            and medicine["dosage_norm"] == row["dosage_attendu"])


RETRY_PAUSE = 60  # the free tier is sometimes overloaded: one more try, reported


def evaluate(reader, matcher, name, pages, expected, document):
    if not pages:
        return {"name": name, "error": "no photo found"}
    try:
        prepared = [prepare_image(p.read_bytes(), max_bytes=MAX_PAGE_BYTES, max_side=MAX_SIDE)
                    for p in pages]
    except ImageRejected as error:
        return {"name": name, "error": f"{type(error).__name__}: {error}"}
    failures = []
    for attempt in range(2):
        start = time.perf_counter()
        try:
            reading = read_note(reader, prepared)
            break
        except (LLMTimeout, ProviderBusy) as error:
            failures.append(f"{type(error).__name__} after {time.perf_counter() - start:.0f} s")
            if attempt == 0:
                time.sleep(RETRY_PAUSE)
        except LLMError as error:
            return {"name": name, "error": f"{type(error).__name__}: {error}"}
    else:
        return {"name": name, "error": "; ".join(failures)}
    seconds = time.perf_counter() - start

    read_lines = list(reading.lignes)
    used, details = set(), []
    stats = {"expected": len(expected), "read": 0, "exact_expected": 0, "exact_ok": 0,
             "false_positive": 0, "back_orders": 0, "back_orders_ok": 0, "to_check": 0,
             "to_check_first_ok": 0}
    for row in expected:
        # The read line that is the same as this expected line (each read line used once)
        best, score = None, 0
        for i, line in enumerate(read_lines):
            if i not in used:
                s = fuzz.ratio(simple(line.designation), simple(row["designation"]))
                if s > score:
                    best, score = i, s
        delivered = row["livre"].strip().lower() == "oui"
        # No dose written on the note (e.g. "TAHOR CP B/30"): the pharmacist must choose,
        # so the right answer is "to check" with the right medicine among the candidates
        choice_needed = bool(row["nom_marque_attendu"]) and not row["dosage_attendu"]
        if not delivered:
            stats["back_orders"] += 1
        if row["nom_marque_attendu"] and delivered and not choice_needed:
            stats["exact_expected"] += 1
        if best is None or score < SAME_LINE:
            details.append((row["designation"], "-", "not read", ""))
            continue
        used.add(best)
        stats["read"] += 1
        line = read_lines[best]
        result = matcher.match(line)
        medicine, status = result["medicament"], result["correspondance"]
        got = f"{medicine['nom_marque']} {medicine['dosage_norm']}" if medicine else "-"
        verdict = "ok"
        if not delivered:
            if status == NOT_DELIVERED:
                stats["back_orders_ok"] += 1
            else:
                verdict = "back order missed"
        elif not row["nom_marque_attendu"]:
            if status == EXACT:  # a product outside the list ticked as a medicine
                stats["false_positive"] += 1
                verdict = "FALSE POSITIVE"
        elif choice_needed:
            stats["to_check"] += 1
            brand_ok = [c for c in result["candidats"]
                        if normalize(c["nom_marque"]).startswith(normalize(row["nom_marque_attendu"]))]
            if status == EXACT:
                stats["false_positive"] += 1  # ticked although the dose is not written
                verdict = "FALSE POSITIVE"
            elif brand_ok:
                stats["to_check_first_ok"] += 1
                verdict = "to check, as expected (no dose on the note)"
            else:
                verdict = "to check (right one not proposed)"
        elif status == EXACT:
            if is_expected(medicine, row):
                stats["exact_ok"] += 1
            else:
                stats["false_positive"] += 1
                verdict = "FALSE POSITIVE"
        elif status == "a_verifier":
            stats["to_check"] += 1
            if is_expected(medicine, row) or any(is_expected(c, row) for c in result["candidats"]):
                stats["to_check_first_ok"] += 1
                verdict = "to check (right one proposed)"
            else:
                verdict = "to check (right one not proposed)"
        else:
            verdict = status
        fields = f"{line.nom_marque or '-'} / {line.dosage or '-'} / {line.forme or '-'}"
        details.append((row["designation"], f"{line.designation} ({fields})", f"{status}: {got}",
                        verdict))

    read_doc = reading.document
    doc_ok = {
        "fournisseur": bool(document.get("fournisseur")) and fuzz.partial_ratio(
            simple(document["fournisseur"]), simple(read_doc.fournisseur)) >= 85,
        "numero_bon": bool(document.get("numero_bon")) and simple(read_doc.numero_bon).replace(" ", "")
        == simple(document["numero_bon"]).replace(" ", ""),
        "date_bon": bool(document.get("date_bon")) and read_doc.date_bon is not None
        and read_doc.date_bon.isoformat() == document["date_bon"],
    }
    return {"name": name, "seconds": seconds, "stats": stats, "details": details,
            "failed_tries": failures,
            "document": doc_ok, "read_count": len(read_lines),
            "read_document": (read_doc.fournisseur, read_doc.numero_bon, read_doc.date_bon)}


def pct(a, b):
    return f"{100 * a / b:.0f} %" if b else "-"


def write_report(results, model):
    ok = [r for r in results if "error" not in r]
    total = {k: sum(r["stats"][k] for r in ok) for k in (ok[0]["stats"] if ok else {})}
    lines = [
        "# Delivery note scan: results",
        "",
        f"Measured on {date.today().isoformat()} with `scripts/evaluate_delivery_scan.py`, "
        f"model `{model}`, on {len(results)} note(s). Matching by MedRadar's rules; the model "
        "only reads.",
        "",
    ]
    if ok:
        lines += [
            "| Measure | Result |",
            "| --- | --- |",
            f"| Lines read correctly | **{pct(total['read'], total['expected'])}** "
            f"({total['read']}/{total['expected']}) |",
            f"| Medicines matched exactly (ticked by default, right medicine) | "
            f"**{pct(total['exact_ok'], total['exact_expected'])}** "
            f"({total['exact_ok']}/{total['exact_expected']}) |",
            f"| **False positives** (a wrong medicine ticked by default: the most serious error) "
            f"| **{total['false_positive']}** |",
            f"| Lines left \"to check\" with the right medicine among the 3 proposed | "
            f"{total['to_check_first_ok']}/{total['to_check']} |",
            f"| Back orders detected (never put in stock) | "
            f"{pct(total['back_orders_ok'], total['back_orders'])} "
            f"({total['back_orders_ok']}/{total['back_orders']}) |",
            f"| Supplier / number / date read | "
            f"{sum(r['document']['fournisseur'] for r in ok)}/{len(ok)} · "
            f"{sum(r['document']['numero_bon'] for r in ok)}/{len(ok)} · "
            f"{sum(r['document']['date_bon'] for r in ok)}/{len(ok)} |",
            f"| Average reading time per note | "
            f"{sum(r['seconds'] for r in ok) / len(ok):.1f} s |",
            "",
        ]
    for r in results:
        lines += [f"## {r['name']}", ""]
        if "error" in r:
            lines += [f"Not measured: {r['error']}", ""]
            continue
        s = r["stats"]
        lines += [
            ("First try failed (" + "; ".join(r["failed_tries"]) + "): measured on the second "
             "try. " if r["failed_tries"] else "") +
            f"{r['read_count']} lines read in {r['seconds']:.1f} s; exact {s['exact_ok']}/"
            f"{s['exact_expected']}, false positives {s['false_positive']}, back orders "
            f"{s['back_orders_ok']}/{s['back_orders']}. Read: supplier "
            f"\"{r['read_document'][0]}\", number \"{r['read_document'][1]}\", date "
            f"{r['read_document'][2]}.",
            "",
            "| Expected line | Read as (brand / dose / form fields) | MedRadar's match | Verdict |",
            "| --- | --- | --- | --- |",
        ]
        lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in r["details"]]
        lines.append("")
    RESULTS.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--demo", action="store_true", help="measure the demo note")
    parser.add_argument("--pause", type=float, default=60.0,
                        help="seconds between notes (the free tier quota is per minute)")
    args = parser.parse_args()

    reader = make_delivery_reader()
    if reader is None:
        sys.exit("The scan is off: set LLM_API_KEY in .env (see README).")
    if reader.name == "fake":
        sys.exit("LLM_PROVIDER=fake gives made-up answers: use a real provider to measure.")
    notes = demo_notes() if args.demo else sample_notes()
    if not notes:
        sys.exit(f"No note to measure: add {SAMPLES}/<note>.expected.csv and its photos, "
                 "or use --demo.")

    store = load_store()
    matcher = LineMatcher(store, SearchIndex(store.records))
    results = []
    for i, note in enumerate(notes):
        if i and args.pause:
            time.sleep(args.pause)
        result = evaluate(reader, matcher, *note)
        results.append(result)
        if "error" in result:
            print(f"{result['name']}: {result['error']}")
        else:
            s = result["stats"]
            print(f"{result['name']}: {s['read']}/{s['expected']} lines read, exact "
                  f"{s['exact_ok']}/{s['exact_expected']}, false positives {s['false_positive']}, "
                  f"back orders {s['back_orders_ok']}/{s['back_orders']}, {result['seconds']:.1f} s")
    write_report(results, " → ".join(getattr(reader, "models", [reader.name])))
    print(f"Written to {RESULTS}")


if __name__ == "__main__":
    main()
