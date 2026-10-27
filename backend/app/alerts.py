"""Alert emails: tell patients when their medicine is declared in stock near them.

An alert is sent once, for the first pharmacy that declares the medicine or one of
its exact equivalents (same key) in stock, within the radius chosen by the patient. It is then
finished: the patient is never emailed twice for the same alert.
"""

import logging
from html import escape

from sqlalchemy import select, update

from .config import FRONTEND_URL
from .db import SessionLocal, utcnow
from .geo import haversine_km
from .mail import MailError
from .models import PHARMACY_VALIDATED, STOCK_IN, Alert, Pharmacy
from .stock import latest_declarations

logger = logging.getLogger("medradar")


def send_alerts(mailer, store, pharmacy_id, medicine_ids=None):
    """Email the active alerts that this pharmacy can now answer.

    Runs after the response (background task), with its own session. medicine_ids:
    the medicines just declared; None checks everything the pharmacy has in stock
    (a pharmacy just approved). Errors are logged, never raised: the declaration
    itself is already saved.
    """
    if mailer is None:
        return
    try:
        with SessionLocal() as db:
            _send(db, mailer, store, pharmacy_id, medicine_ids)
    except Exception:
        logger.exception("Sending the alert emails failed")


def _send(db, mailer, store, pharmacy_id, medicine_ids):
    pharmacy = db.get(Pharmacy, pharmacy_id)
    if pharmacy is None or pharmacy.status != PHARMACY_VALIDATED:
        return
    # What the pharmacy has in stock now (its latest declarations)
    in_stock = [store.get(r.medicine_id) for r in latest_declarations(
        db, medicine_ids=medicine_ids, pharmacy_id=pharmacy_id) if r.status == STOCK_IN]

    # An alert on a medicine is answered by any presentation with the same key
    answers = {}  # alert medicine id -> medicine in stock
    for medicine in filter(None, in_stock):
        for same in store.same_key(medicine):
            answers.setdefault(same["id"], medicine)
    if not answers:
        return

    alerts = db.scalars(select(Alert).where(Alert.medicine_id.in_(list(answers)),
                                            Alert.sent_at.is_(None))).all()
    for alert in alerts:
        distance = haversine_km(alert.latitude, alert.longitude,
                                pharmacy.latitude, pharmacy.longitude)
        if distance > alert.radius_km:
            continue
        medicine = answers[alert.medicine_id]

        # Claimed first, so two declarations at the same time cannot send it twice
        claimed = db.execute(update(Alert).where(Alert.id == alert.id, Alert.sent_at.is_(None))
                             .values(sent_at=utcnow()))
        db.commit()
        if claimed.rowcount != 1:
            continue
        requested = store.get(alert.medicine_id) or medicine
        try:
            mailer.send(alert.email, *alert_email(requested, medicine, pharmacy, distance))
        except MailError as error:
            # Kept active: it will be tried again at the next declaration
            db.execute(update(Alert).where(Alert.id == alert.id).values(sent_at=None))
            db.commit()
            logger.warning("Alert %s not sent: %s", alert.id, error)


def _name(medicine):
    return f"{medicine['nom_marque'].title()} ({medicine['dosage'].lower()})"


def alert_email(requested, found, pharmacy, distance_km):
    """(subject, text, html) of the email that answers an alert."""
    link = f"{FRONTEND_URL}/medicament/{requested['id']}" if FRONTEND_URL else None
    same_brand = found["nom_marque"] == requested["nom_marque"]
    what = _name(found) if same_brand else (
        f"{_name(found)}, an exact equivalent of {_name(requested)}")
    subject = f"{requested['nom_marque'].title()} is available near you – MedRadar"

    details = [pharmacy.name, pharmacy.address]
    if pharmacy.phone:
        details.append(f"Phone: {pharmacy.phone}")
    if pharmacy.opening_hours:
        details.append(f"Opening hours: {pharmacy.opening_hours}")
    paragraphs = [
        "Hello,",
        f"Good news: a pharmacy about {distance_km:.1f} km from you has declared {what} in stock.",
        "\n".join(details),
        "Stock can change quickly: call the pharmacy before you go.",
    ]
    if not same_brand:
        paragraphs.append("It contains the same active substance, at the same dose and in the "
                          "same form. Always ask your pharmacist or doctor before changing "
                          "medicine.")
    if link:
        paragraphs.append(f"See every pharmacy that has it: {link}")
    paragraphs.append("You receive this email because you asked MedRadar to tell you when this "
                      "medicine is back. This alert is now finished: we will not email you "
                      "again about it.")

    text = "\n\n".join(paragraphs)
    html = "".join(f"<p>{escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)
    if link:
        html = html.replace(escape(link), f'<a href="{escape(link)}">{escape(link)}</a>')
    return subject, text, html
