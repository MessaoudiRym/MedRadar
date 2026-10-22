"""Content of the FICTIONAL demo delivery note.

Used by scripts/generate_demo_delivery_note.py (to draw the image), by the
simulated reader (tests and end-to-end demo) and by the accuracy measure.
The medicines are real (they exist in the nomenclature); the wholesaler, the
note, the batch numbers, the expiry dates and the prices are made up. The
prices are printed on the image only to check that they are never kept.
"""

SUPPLIER = "Grossiste Démo Ouest"
NOTE_NUMBER = "BL-2026-10458"
NOTE_DATE = "2026-10-20"
PHARMACY = "Pharmacie Démo 1"

# designation (as a wholesaler writes it), quantity, batch, expiry, unit price (DA), status,
# then what a perfect reading should give: expected brand and dose ("" = none expected)
LINES = [
    ("GLUCOPH 850 CP B/30", 20, "GL8501", "2028-05", 168.50, "livre", "GLUCOPHAGE 850", "850MG"),
    ("GLUCOPHAGE 1000MG CP B/30", 10, "GL1002", "2028-03", 214.00, "livre", "GLUCOPHAGE", "1000MG"),
    ("LEVOTHYROX 50MCG CP B/30", 15, "LV5003", "2027-11", 98.40, "livre", "LEVOTHYROX", "50MCG"),
    ("LEVOTHYROX 75MCG CP B/30", 0, None, None, 98.40, "reliquat", "LEVOTHYROX", "75MCG"),
    ("AMLOR 5MG GEL B/30", 12, "AM0504", "2028-01", 312.00, "livre", "AMLOR", "5MG"),
    ("DIAMICRON 30MG LM CP B/30", 10, "DM3005", "2027-09", 254.30, "livre", "DIAMICRON", "30MG"),
    ("TEGRETOL 200MG CP B/50", 6, "TG2006", "2028-02", 410.00, "livre", "TEGRETOL", "200MG"),
    ("DEPAKINE CHRONO 500 CP B/30", 0, None, None, 520.00, "reliquat", "DEPAKINE CHRONO", "500MG"),
    ("COZZAR 50MG CP B/28", 8, "CZ5007", "2027-12", 640.00, "livre", "COZZAR", "50MG"),
    ("DETENSIEL 10MG CP B/30", 10, "DT1008", "2028-04", 389.90, "livre", "DETENSIEL", "10MG"),
    ("TAHOR CP B/30", 12, "TH2009", "2028-06", 980.00, "livre", "TAHOR", ""),
    ("KARDEGIC 160MG SACH B/30", 20, "KD1610", "2028-08", 145.00, "livre", "KARDEGIC", "160MG"),
    ("INEXIUM 20MG CP B/14", 10, "IN2011", "2027-10", 455.00, "livre", "INEXIUM", "20MG"),
    ("DOLIPRANE 1000MG CP B/8", 40, "DP1012", "2028-09", 52.00, "livre", "DOLIPRANE", "1000MG"),
    ("CLAMOXYL 1G CP DISP B/6", 10, "CL1013", "2027-08", 286.00, "livre", "CLAMOXYL", "1000MG"),
    ("SMECTA FRAISE 3G SACH B/30", 15, "SM3014", "2028-07", 330.00, "livre", "SMECTA FRAISE",
     "3000MG/SACHET"),
    ("ASPEGIC 1000MG SACH B/20", 8, "AS1015", "2028-01", 190.00, "livre", "ASPEGIC ADULTE", "1000MG"),
    ("VOLTARENE EMULGEL 1% TB 50G", 6, "VE0116", "2027-07", 420.00, "livre", "VOLTARENE EMULGEL",
     "1%"),
    ("GLUCOPH 850 CP B/30", 10, "GL8517", "2028-05", 168.50, "livre", "GLUCOPHAGE 850", "850MG"),
    ("ECRAN SOLAIRE SPF50+ 50ML", 5, "ES5018", "2028-12", 1450.00, "livre", "", ""),
]


def reader_answer():
    """What a perfect model answer looks like for this note: no price, ever."""
    return {
        "document": {
            "type_document": "bon_de_livraison",
            "fournisseur": SUPPLIER,
            "numero_bon": NOTE_NUMBER,
            "date_bon": NOTE_DATE,
            "nombre_lignes_visibles": len(LINES),
        },
        "lignes": [
            {
                "designation": designation,
                "nom_marque": None, "dosage": None, "forme": None,  # left to our parser
                "quantite_livree": quantity,
                "numero_lot": batch,
                "date_peremption": expiry,
                "statut_ligne": status,
                "lisible": True,
            }
            for designation, quantity, batch, expiry, _price, status, _brand, _dose in LINES
        ],
    }
