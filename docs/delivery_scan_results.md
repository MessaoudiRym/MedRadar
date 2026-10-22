# Delivery note scan: results

Measured on 2026-10-22 with `scripts/evaluate_delivery_scan.py`, model `gemini-3.8-flash → gemini-3.5-flash-lite`, on 2 note(s). Matching by MedRadar's rules; the model only reads.

| Measure | Result |
| --- | --- |
| Lines read correctly | **100 %** (40/40) |
| Medicines matched exactly (ticked by default, right medicine) | **100 %** (32/32) |
| **False positives** (a wrong medicine ticked by default: the most serious error) | **0** |
| Lines left "to check" with the right medicine among the 3 proposed | 2/2 |
| Back orders detected (never put in stock) | 100 % (4/4) |
| Supplier / number / date read | 2/2 · 2/2 · 2/2 |
| Average reading time per note | 15.3 s |

## demo (sharp)

20 lines read in 20.4 s; exact 16/16, false positives 0, back orders 2/2. Read: supplier "GROSSISTE DÉMO OUEST", number "BL-2026-10458", date 2026-10-20.

| Expected line | Read as (brand / dose / form fields) | MedRadar's match | Verdict |
| --- | --- | --- | --- |
| GLUCOPH 850 CP B/30 | GLUCOPH 850 CP B/30 (GLUCOPH / 850 / CP) | exacte: GLUCOPHAGE 850 850MG | ok |
| GLUCOPHAGE 1000MG CP B/30 | GLUCOPHAGE 1000MG CP B/30 (GLUCOPHAGE / 1000 / CP) | exacte: GLUCOPHAGE 1000MG | ok |
| LEVOTHYROX 50MCG CP B/30 | LEVOTHYROX 50MCG CP B/30 (LEVOTHYROX / 50 / CP) | exacte: LEVOTHYROX 50MCG | ok |
| LEVOTHYROX 75MCG CP B/30 | LEVOTHYROX 75MCG CP B/30 (LEVOTHYROX / 75 / CP) | non_livre: LEVOTHYROX 75MCG | ok |
| AMLOR 5MG GEL B/30 | AMLOR 5MG GEL B/30 (AMLOR / 5 / GEL) | exacte: AMLOR 5MG | ok |
| DIAMICRON 30MG LM CP B/30 | DIAMICRON 30MG LM CP B/30 (DIAMICRON / 30 / CP) | exacte: DIAMICRON 30MG | ok |
| TEGRETOL 200MG CP B/50 | TEGRETOL 200MG CP B/50 (TEGRETOL / 200 / CP) | exacte: TEGRETOL 200MG | ok |
| DEPAKINE CHRONO 500 CP B/30 | DEPAKINE CHRONO 500 CP B/30 (DEPAKINE / 500 / CP) | non_livre: DEPAKINE 500MG | ok |
| COZZAR 50MG CP B/28 | COZZAR 50MG CP B/28 (COZZAR / 50 / CP) | exacte: COZZAR 50MG | ok |
| DETENSIEL 10MG CP B/30 | DETENSIEL 10MG CP B/30 (DETENSIEL / 10 / CP) | exacte: DETENSIEL 10MG | ok |
| TAHOR CP B/30 | TAHOR CP B/30 (TAHOR / - / CP) | a_verifier: TAHOR 20MG | to check, as expected (no dose on the note) |
| KARDEGIC 160MG SACH B/30 | KARDEGIC 160MG SACH B/30 (KARDEGIC / 160 / SACH) | exacte: KARDEGIC 160MG | ok |
| INEXIUM 20MG CP B/14 | INEXIUM 20MG CP B/14 (INEXIUM / 20 / CP) | exacte: INEXIUM 20MG | ok |
| DOLIPRANE 1000MG CP B/8 | DOLIPRANE 1000MG CP B/8 (DOLIPRANE / 1000 / CP) | exacte: DOLIPRANE 1000MG | ok |
| CLAMOXYL 1G CP DISP B/6 | CLAMOXYL 1G CP DISP B/6 (CLAMOXYL / 1 / CP) | exacte: CLAMOXYL 1000MG | ok |
| SMECTA FRAISE 3G SACH B/30 | SMECTA FRAISE 3G SACH B/30 (SMECTA / 3 / SACH) | exacte: SMECTA FRAISE 3000MG/SACHET | ok |
| ASPEGIC 1000MG SACH B/20 | ASPEGIC 1000MG SACH B/20 (ASPEGIC / 1000 / SACH) | exacte: ASPEGIC ADULTE 1000MG | ok |
| VOLTARENE EMULGEL 1% TB 50G | VOLTARENE EMULGEL 1% TB 50G (VOLTARENE / 1 / TB) | exacte: VOLTARENE EMULGEL 1% | ok |
| GLUCOPH 850 CP B/30 | GLUCOPH 850 CP B/30 (GLUCOPH / 850 / CP) | exacte: GLUCOPHAGE 850 850MG | ok |
| ECRAN SOLAIRE SPF50+ 50ML | ECRAN SOLAIRE SPF50+ 50ML (ECRAN SOLAIRE / - / -) | non_trouve: - | ok |

## demo (photo-like, tilted)

20 lines read in 10.3 s; exact 16/16, false positives 0, back orders 2/2. Read: supplier "GROSSISTE DÉMO OUEST", number "BL-2026-10458", date 2026-10-20.

| Expected line | Read as (brand / dose / form fields) | MedRadar's match | Verdict |
| --- | --- | --- | --- |
| GLUCOPH 850 CP B/30 | GLUCOPH 850 CP B/30 (GLUCOPH / 850 / CP) | exacte: GLUCOPHAGE 850 850MG | ok |
| GLUCOPHAGE 1000MG CP B/30 | GLUCOPHAGE 1000MG CP B/30 (GLUCOPHAGE / 1000 / CP) | exacte: GLUCOPHAGE 1000MG | ok |
| LEVOTHYROX 50MCG CP B/30 | LEVOTHYROX 50MCG CP B/30 (LEVOTHYROX / 50 / CP) | exacte: LEVOTHYROX 50MCG | ok |
| LEVOTHYROX 75MCG CP B/30 | LEVOTHYROX 75MCG CP B/30 (LEVOTHYROX / 75 / CP) | non_livre: LEVOTHYROX 75MCG | ok |
| AMLOR 5MG GEL B/30 | AMLOR 5MG GEL B/30 (AMLOR / 5 / GEL) | exacte: AMLOR 5MG | ok |
| DIAMICRON 30MG LM CP B/30 | DIAMICRON 30MG LM CP B/30 (DIAMICRON / 30 / CP) | exacte: DIAMICRON 30MG | ok |
| TEGRETOL 200MG CP B/50 | TEGRETOL 200MG CP B/50 (TEGRETOL / 200 / CP) | exacte: TEGRETOL 200MG | ok |
| DEPAKINE CHRONO 500 CP B/30 | DEPAKINE CHRONO 500 CP B/30 (DEPAKINE / 500 / CP) | non_livre: DEPAKINE 500MG | ok |
| COZZAR 50MG CP B/28 | COZZAR 50MG CP B/28 (COZZAR / 50 / CP) | exacte: COZZAR 50MG | ok |
| DETENSIEL 10MG CP B/30 | DETENSIEL 10MG CP B/30 (DETENSIEL / 10 / CP) | exacte: DETENSIEL 10MG | ok |
| TAHOR CP B/30 | TAHOR CP B/30 (TAHOR / - / CP) | a_verifier: TAHOR 20MG | to check, as expected (no dose on the note) |
| KARDEGIC 160MG SACH B/30 | KARDEGIC 160MG SACH B/30 (KARDEGIC / 160 / SACH) | exacte: KARDEGIC 160MG | ok |
| INEXIUM 20MG CP B/14 | INEXIUM 20MG CP B/14 (INEXIUM / 20 / CP) | exacte: INEXIUM 20MG | ok |
| DOLIPRANE 1000MG CP B/8 | DOLIPRANE 1000MG CP B/8 (DOLIPRANE / 1000 / CP) | exacte: DOLIPRANE 1000MG | ok |
| CLAMOXYL 1G CP DISP B/6 | CLAMOXYL 1G CP DISP B/6 (CLAMOXYL / 1 / CP) | exacte: CLAMOXYL 1000MG | ok |
| SMECTA FRAISE 3G SACH B/30 | SMECTA FRAISE 3G SACH B/30 (SMECTA / 3 / SACH) | exacte: SMECTA FRAISE 3000MG/SACHET | ok |
| ASPEGIC 1000MG SACH B/20 | ASPEGIC 1000MG SACH B/20 (ASPEGIC / 1000 / SACH) | exacte: ASPEGIC ADULTE 1000MG | ok |
| VOLTARENE EMULGEL 1% TB 50G | VOLTARENE EMULGEL 1% TB 50G (VOLTARENE / 1 / -) | exacte: VOLTARENE EMULGEL 1% | ok |
| GLUCOPH 850 CP B/30 | GLUCOPH 850 CP B/30 (GLUCOPH / 850 / CP) | exacte: GLUCOPHAGE 850 850MG | ok |
| ECRAN SOLAIRE SPF50+ 50ML | ECRAN SOLAIRE SPF50+ 50ML (- / 50 / -) | non_trouve: - | ok |
