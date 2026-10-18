# Privacy

MedRadar stores only the data it needs to work.

## Patients

Patients do not need an account.

| Data | Why | Details |
| --- | --- | --- |
| Searches | Know which medicines are hard to find, and where | **Anonymous**: the medicine and, at most, the district (e.g. "USTO"). No name, no account, no IP address, no exact position. |
| Position sent with a search | Sort pharmacies by distance | Used for the answer, then forgotten. Only the nearest district may be kept (see above). |
| Alerts (email, medicine, area) | Tell the patient when the medicine is back nearby | The position is rounded to about 1 km. At most 5 active alerts per email. |

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
