# Privacy

MedRadar stores only the data it needs to work.

## Patients

Patients do not need an account.

| Data | Why | Details |
| --- | --- | --- |
| Searches | Know which medicines are hard to find, and where | **Anonymous**: the medicine and, at most, the district (e.g. "USTO"). No name, no account, no IP address, no exact position. |
| Position sent with a search | Sort pharmacies by distance | Used for the answer, then forgotten. Only the nearest district may be kept (see above). |
| Alerts (email, medicine, area) | Tell the patient when the medicine is back nearby | The position is rounded to about 1 km. At most 5 active alerts per email. |

### Photos of medicine boxes

| What happens | Details |
| --- | --- |
| The photo is sent to Google (Gemini API, free tier) | **Only to read the box**: brand name, active ingredient, dose and form. Before sending, it is reduced and its metadata (such as the GPS position) is removed. |
| MedRadar does not keep it | The photo stays in memory for the time of the request: never written to disk, to the database or to the logs. Only an anonymous "recognition succeeded: yes / no" is kept, for statistics. |
| Google may use it | Data sent to the Gemini API free tier may be used by Google to improve its services. |
| Prescriptions are refused | This is why only medicine boxes are accepted. **Do not photograph your prescription**: it contains your name and your health information. When the model sees a prescription, MedRadar stops, searches nothing and sends nothing back. |

### Searches in Arabic, Darija or English

| What happens | Details |
| --- | --- |
| Some validated searches are sent to Google (Gemini API, free tier) | Only searches validated with Enter or the Search button, written in Arabic, Darija, arabizi or English (or a French search the normal search is unsure about), **only to understand the name of the medicine**. Suggestions shown while typing are never sent. |
| No personal data | Only the text of the search is sent: no name, no account, no IP address, no position. |
| Kept 30 days, without the person | What the model understood of a search is kept 30 days so the same search is never sent twice. Only the search text and the answer: nothing that links them to a person. Logs do not contain the text of searches. |
| Google may use it | Data sent to the Gemini API free tier may be used by Google to improve its services. Do not type personal information in the search. |

## Pharmacists

| Data | Why |
| --- | --- |
| Email, password, name, phone | Log in, and let the MedRadar team contact the pharmacist during verification |
| Pharmacy name, address, position, phone, opening hours | Show the pharmacy to patients |
| Professional number | Check that the pharmacy is real. Never shown to patients |
| Stock declarations (who, when, what) | Show availability; the history helps detect errors or abuse |

Passwords are never stored: only a bcrypt hash is kept, and passwords are never sent back by the API.

## What patients can see

Public routes only show validated pharmacies, with their business details (name, address, phone, opening hours). They never show an email, a professional number or the account behind a pharmacy.

## Demo data

The demo pharmacies, accounts and stock levels are fictional and contain no real personal data.
