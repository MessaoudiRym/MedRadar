# Multilingual search: results

Measured on 2026-10-21 with `scripts/evaluate_multilingual.py` on 69 queries of [multilingual_eval.csv](multilingual_eval.csv), model `gemini-3.5-flash-lite → gemini-3.8-flash`. Each mode starts with an empty cache.

| Measure | `llm_first` | `rules_first` |
| --- | --- | --- |
| **Success** (right medicine 1st, or correct refusal) | **100 %** (69/69) | **100 %** (69/69) |
| Right answer in the first 3 | 100 % (69/69) | 100 % (69/69) |
| Correct refusals for diseases and symptoms (goal 100 %) | **100 %** (16/16) | **100 %** (16/16) |
| Average response time | 0.76 s | 0.19 s |
| Calls to the model | 41 | 12 |
| Model unavailable (quota, overloaded, slow): rules used instead | 1 | 0 |
| Server errors | 0 | 0 |

## By category

| Category | Queries | `llm_first` 1st / top 3 | `rules_first` 1st / top 3 |
| --- | --- | --- | --- |
| Brand in Arabic letters | 16 | 100 % / 100 % | 100 % / 100 % |
| Darija and arabizi | 10 | 100 % / 100 % | 100 % / 100 % |
| Molecule in English | 8 | 100 % / 100 % | 100 % / 100 % |
| Molecule in Arabic | 5 | 100 % / 100 % | 100 % / 100 % |
| Foreign brand | 6 | 100 % / 100 % | 100 % / 100 % |
| French with typos | 8 | 100 % / 100 % | 100 % / 100 % |
| Disease or symptom (must refuse) | 16 | 100 % / 100 % | 100 % / 100 % |

## Not first in `llm_first` (0)

None.

## Not first in `rules_first` (0)

None.
