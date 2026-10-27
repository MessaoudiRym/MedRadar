"""Draw the FICTIONAL demo delivery note, for the jury and the demo accounts.

Writes two images in frontend/public/demo/:
    bon-livraison-demo.png       photo-like: slightly tilted, uneven light, noise
    bon-livraison-demo-net.png   the same note, straight and sharp

The content comes from backend/app/delivery/demo_note.py: real medicines of the
nomenclature written as a wholesaler does ("GLUCOPH 850 CP B/30"), 2 back orders
(RELIQUAT), 1 parapharmacy product, and made-up batches, expiry dates and
prices (printed only to check that they are ignored). The header says clearly
that the document is fictional.

Usage (from the project root):
    python scripts/generate_demo_delivery_note.py
"""

import random
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.delivery.demo_note import LINES, NOTE_DATE, NOTE_NUMBER, PHARMACY, SUPPLIER  # noqa: E402

OUT = ROOT / "frontend" / "public" / "demo"
WIDTH, HEIGHT = 1240, 1754  # A4 at 150 dpi
INK = (30, 32, 40)
GREY = (110, 112, 120)
RED = (170, 30, 30)


def font(size, bold=False):
    names = (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"])
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def money(value):
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def draw_note(lines=LINES, supplier=SUPPLIER, number=NOTE_NUMBER, note_date=NOTE_DATE,
              pharmacy=PHARMACY) -> Image.Image:
    """lines: (designation, quantity, batch, expiry, unit price, status, ...)."""
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    d = ImageDraw.Draw(image)
    x0, x1 = 70, WIDTH - 70

    # Header: clearly fictional
    d.rectangle((x0, 50, x1, 120), fill=(235, 238, 245), outline=INK, width=2)
    d.text((WIDTH // 2, 85), "GROSSISTE DÉMO — DOCUMENT FICTIF POUR DÉMONSTRATION",
           font=font(30, True), fill=RED, anchor="mm")
    d.text((x0, 150), supplier.upper(), font=font(34, True), fill=INK)
    d.text((x0, 195), "Zone d'activité fictive, Oran — Tél. 0550 00 00 00 (fictif)",
           font=font(20), fill=GREY)
    d.text((x1, 150), "BON DE LIVRAISON", font=font(34, True), fill=INK, anchor="ra")
    shown_date = date.fromisoformat(note_date).strftime("%d/%m/%Y")
    d.text((x1, 198), f"N° {number}", font=font(24, True), fill=INK, anchor="ra")
    d.text((x1, 232), f"Date : {shown_date}", font=font(24), fill=INK, anchor="ra")
    d.rectangle((x0, 270, x0 + 520, 350), outline=INK, width=2)
    d.text((x0 + 15, 282), "Client", font=font(18), fill=GREY)
    d.text((x0 + 15, 308), pharmacy, font=font(26, True), fill=INK)

    # Table
    columns = [("Code", 85), ("Désignation", 385), ("Lot", 115), ("Pér.", 85), ("Qté", 65),
               ("P.U. (DA)", 115), ("Montant", 120), ("Obs.", 130)]
    top, row_height = 380, 50
    d.rectangle((x0, top, x1, top + row_height), fill=(225, 228, 235))
    x = x0
    for title, width in columns:
        d.text((x + 8, top + 14), title, font=font(19, True), fill=INK)
        x += width
    total = 0.0
    for i, (designation, quantity, batch, expiry, price, status, *_expected) in enumerate(lines):
        y = top + row_height * (i + 1)
        amount = quantity * price
        total += amount
        expiry_text = f"{expiry[5:]}/{expiry[2:4]}" if expiry else ""
        values = [f"{4100 + i * 7:06d}", designation, batch or "", expiry_text, str(quantity),
                  money(price), money(amount) if quantity else "", "RELIQUAT" if status != "livre" else ""]
        x = x0
        for (title, width), value in zip(columns, values):
            colour = RED if value == "RELIQUAT" else INK
            size = 15 if title == "Obs." else 19
            d.text((x + 8, y + 15), value, font=font(size, title in ("Désignation", "Obs.")), fill=colour)
            x += width
        d.line((x0, y + row_height, x1, y + row_height), fill=(200, 202, 210), width=1)
    bottom = top + row_height * (len(LINES) + 1)
    x = x0
    for _title, width in columns:
        d.line((x, top, x, bottom), fill=(170, 172, 180), width=1)
        x += width
    d.rectangle((x0, top, x1, bottom), outline=INK, width=2)

    # Totals (fictional) and signature: never read
    vat = total * 0.09
    for k, (label, value) in enumerate([("Total HT", total), ("TVA", vat), ("Total TTC", total + vat)]):
        d.text((x1 - 260, bottom + 25 + k * 34), label, font=font(21, k == 2), fill=INK)
        d.text((x1, bottom + 25 + k * 34), f"{money(value)} DA", font=font(21, k == 2), fill=INK,
               anchor="ra")
    back_orders = sum(1 for line in lines if line[5] != "livre")
    d.text((x0, bottom + 30), f"{len(lines)} lignes — {back_orders} reliquat(s) à livrer",
           font=font(20), fill=GREY)
    d.text((x0, bottom + 120), "Signature et cachet du client :", font=font(20), fill=GREY)
    d.text((WIDTH // 2, HEIGHT - 60), "Document fictif généré pour la démonstration de MedRadar",
           font=font(18), fill=GREY, anchor="mm")
    return image


def photo_like(note: Image.Image) -> Image.Image:
    """A slight angle, a desk around the page, uneven light and a bit of noise."""
    rng = random.Random(2026)
    rotated = note.rotate(2.2, resample=Image.Resampling.BICUBIC, expand=True,
                          fillcolor=(120, 110, 95))
    desk = Image.new("RGB", (rotated.width + 80, rotated.height + 80), (120, 110, 95))
    desk.paste(rotated, (40, 40))
    # Uneven light: brighter in the middle, darker towards the corners
    light = Image.radial_gradient("L").resize(desk.size).point(lambda v: 255 - v // 5)
    desk = Image.composite(desk, Image.new("RGB", desk.size, (60, 56, 50)), light)
    desk = desk.filter(ImageFilter.GaussianBlur(0.7))
    pixels = desk.load()
    for _ in range(desk.width * desk.height // 40):
        x, y = rng.randrange(desk.width), rng.randrange(desk.height)
        n = rng.randint(-28, 28)
        r, g, b = pixels[x, y]
        pixels[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))
    return desk


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    note = draw_note()
    note.save(OUT / "bon-livraison-demo-net.png", optimize=True)
    photo_like(note).save(OUT / "bon-livraison-demo.png", optimize=True)
    for name in ("bon-livraison-demo.png", "bon-livraison-demo-net.png"):
        print(f"{OUT / name} ({(OUT / name).stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
