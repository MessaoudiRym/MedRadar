# Raw data

Original file, exactly as downloaded from the official source. Never edit it by hand: all cleaning is done by scripts in `scripts/`, which write to `data/clean/`.

## Source

- **Publisher:** Ministry of Pharmaceutical Industry, Algeria (Ministère de l'Industrie Pharmaceutique)
- **Page:** https://www.miph.gov.dz/fr/nomenclature-nationale-des-produits-pharmaceutiques/
- **Direct link:** https://www.miph.gov.dz/fr/wp-content/uploads/2026/09/clean_NOMENCLATURE.VERSION.AOUT_.2026-.xlsx
- **Version:** August 2026
- **Downloaded on:** 18 October 2026

## File

`clean_NOMENCLATURE.VERSION.AOUT_.2026-.xlsx` contains three sheets:

| Sheet | Content | Medicines | Header row |
| --- | --- | --- | --- |
| `Nomenclature Aout 2026` | Registered medicines for human use | 5,425 | 16 |
| `Non Renouvelés ` (trailing space) | Registrations not renewed | 1,491 | 12 |
| `Retraits` | Medicines withdrawn from the market | 2,679 | 11 |

Each sheet starts with an official header block (Republic, Ministry, Directorate) above the table, so scripts must skip those rows.

## Main columns

| Original column | Used for |
| --- | --- |
| `DENOMINATION COMMUNE INTERNATIONALE` | Active ingredient (INN / DCI) |
| `NOM DE MARQUE` | Brand name searched by patients |
| `FORME` | Pharmaceutical form |
| `DOSAGE` | Dose |
| `CONDITIONNEMENT` | Pack size |
| `N°ENREGISTREMENT` | Unique registration number |
| `LABORATOIRES DETENTEUR...` / `PAYS...` | Manufacturer and country |
| `TYPE` | Brand or generic |
| `STATUT` | Made in Algeria or imported |

## How MedRadar uses it

- The `Nomenclature Aout 2026` sheet is the reference list used to find equivalents: same active ingredient, same dose, same form.
- Medicines listed in `Non Renouvelés ` or `Retraits` are never suggested as equivalents.