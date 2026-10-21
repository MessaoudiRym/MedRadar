"""Measure how often photo recognition finds the right medicine.

Reads real photos from docs/recognition_samples/photos/ (never committed) and
the expected answers from docs/recognition_samples/expected.csv:

    nom_fichier,nom_marque_attendu,dosage_attendu
    glucophage_850.jpg,GLUCOPHAGE 850,850 mg

Each photo goes through the real recognition (same preparation, same model,
same ranking as the API). The script prints, and writes to
docs/recognition_results.md (without the photos):
    - the share of boxes where the right medicine is 1st,
    - the share where it is in the first 3,
    - the average time per photo.

Needs LLM_API_KEY in .env. On the Gemini free tier, keep the pause between
photos (default 7 s) to stay under the requests-per-minute limit.

Usage (from the project root):
    python scripts/evaluate_recognition.py
    python scripts/evaluate_recognition.py --pause 0 --limit 5
"""

import argparse
import csv
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.data import load_store  # noqa: E402
from app.images import ImageRejected, prepare_image  # noqa: E402
from app.recognition import normalize_dose, rank  # noqa: E402
from app.search import SearchIndex, normalize  # noqa: E402
from app.vision import make_reader  # noqa: E402
from app.vision.base import BOX, ReaderError, read_box  # noqa: E402

SAMPLES = ROOT / "docs" / "recognition_samples"
PHOTOS = SAMPLES / "photos"
EXPECTED = SAMPLES / "expected.csv"
RESULTS = ROOT / "docs" / "recognition_results.md"


def read_expected(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    needed = {"nom_fichier", "nom_marque_attendu", "dosage_attendu"}
    if rows and not needed <= set(rows[0]):
        sys.exit(f"{path} must have the columns: {', '.join(sorted(needed))}")
    return rows


def is_expected(medicine, row):
    return (normalize(medicine["nom_marque"]) == normalize(row["nom_marque_attendu"])
            and medicine["dosage_norm"] == normalize_dose(row["dosage_attendu"])[0])


def evaluate_one(reader, store, index, row):
    """Returns (position of the right medicine or None, what happened, seconds)."""
    photo = PHOTOS / row["nom_fichier"]
    if not photo.exists():
        return None, "photo not found", 0.0
    start = time.perf_counter()
    try:
        reading = read_box(reader, prepare_image(photo.read_bytes()))
    except ImageRejected as error:
        return None, f"file refused ({error.code})", time.perf_counter() - start
    except ReaderError as error:
        return None, f"model error: {type(error).__name__}", time.perf_counter() - start
    if reading.type_image != BOX or not reading.lisible:
        return None, f"not read ({reading.type_image})", time.perf_counter() - start

    best = rank(reading, store, index)
    seconds = time.perf_counter() - start
    position = next((i + 1 for i, (m, _) in enumerate(best) if is_expected(m, row)), None)
    shown = ", ".join(f"{m['nom_marque']} {m['dosage_norm']}" for m, _ in best) or "no result"
    return position, shown, seconds


def percent(part, total):
    return f"{100 * part / total:.0f} %" if total else "-"


def write_report(rows, results, model):
    total = len(results)
    top1 = sum(1 for p, _, _ in results if p == 1)
    top3 = sum(1 for p, _, _ in results if p is not None)
    timed = [s for _, _, s in results if s > 0]
    average = sum(timed) / len(timed) if timed else 0

    lines = [
        "# Photo recognition: results",
        "",
        f"Measured on {date.today().isoformat()} with `scripts/evaluate_recognition.py`, "
        f"model `{model}`, on {total} real box photos (the photos are not published).",
        "",
        "| Measure | Result |",
        "| --- | --- |",
        f"| Right medicine in 1st position | **{percent(top1, total)}** ({top1}/{total}) |",
        f"| Right medicine in the first 3 | **{percent(top3, total)}** ({top3}/{total}) |",
        f"| Average time per photo | {average:.1f} s |",
        "",
        "## Detail",
        "",
        "| Photo | Expected | Position | Proposed |",
        "| --- | --- | --- | --- |",
    ]
    for row, (position, shown, _) in zip(rows, results):
        expected = f"{row['nom_marque_attendu']} {row['dosage_attendu']}"
        lines.append(f"| {row['nom_fichier']} | {expected} | {position or '-'} | {shown} |")
    RESULTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return top1, top3, total, average


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pause", type=float, default=7.0, help="seconds between photos (free tier)")
    parser.add_argument("--limit", type=int, help="only the first N photos")
    args = parser.parse_args()

    reader = make_reader()
    if reader is None:
        sys.exit("Photo recognition is off: set LLM_API_KEY in .env (see README).")
    if reader.name == "fake":
        sys.exit("LLM_PROVIDER=fake gives made-up answers: use a real provider to measure.")
    if not EXPECTED.exists():
        sys.exit(f"{EXPECTED} not found (see README, 'Measure the accuracy').")

    rows = read_expected(EXPECTED)[:args.limit]
    store = load_store()
    index = SearchIndex(store.records)

    results = []
    for i, row in enumerate(rows):
        if i and args.pause:
            time.sleep(args.pause)
        position, shown, seconds = evaluate_one(reader, store, index, row)
        results.append((position, shown, seconds))
        mark = {1: "1st", None: "MISSED"}.get(position, f"#{position}")
        print(f"{row['nom_fichier']:<30} {mark:<7} {seconds:5.1f} s   {shown}")

    top1, top3, total, average = write_report(rows, results, getattr(reader, "model", reader.name))
    print(f"\nRight medicine 1st:      {percent(top1, total)} ({top1}/{total})")
    print(f"Right medicine in top 3: {percent(top3, total)} ({top3}/{total})")
    print(f"Average time per photo:  {average:.1f} s")
    print(f"Summary written to {RESULTS}")


if __name__ == "__main__":
    main()
