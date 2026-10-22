"""Words of diseases, symptoms and uses, in French, Arabic, Darija and English.

Safety net that does not depend on the language model: MedRadar never goes
from a disease or a symptom to a medicine. A query that contains one of these
words and no recognized medicine name gets no result ("دوا السكر",
"medicine for diabetes", "dwa ta3 rass").

Words are written as app/query_text.clean() writes them: lowercase, no accents,
Arabic hamza forms written as plain letters (رأس -> راس).
"""

FRENCH = {
    "diabete", "diabetique", "diabetiques", "sucre", "glycemie", "tension", "hypertension",
    "hypotension", "tete", "migraine", "migraines", "fievre", "toux", "douleur", "douleurs", "mal",
    "ventre", "estomac", "allergie", "allergies", "cholesterol", "thyroide", "hypothyroidie",
    "hyperthyroidie", "rhume", "grippe", "angine", "gorge", "asthme", "insomnie", "sommeil",
    "depression", "anxiete", "stress", "nausee", "nausees", "vomissement", "vomissements",
    "diarrhee", "constipation", "infection", "cancer", "coeur", "cardiaque", "epilepsie",
    "convulsions", "arthrose", "rhumatisme", "dos", "dents", "dentaire", "acne", "peau", "yeux",
    "otite", "oreille", "oreilles", "cystite", "urinaire", "regles", "grossesse", "maigrir",
    "dormir", "foie", "rein", "reins", "anemie", "fatigue", "vertige", "vertiges", "brulure",
    "brulures", "ulcere", "reflux", "gastrite", "hemorroides", "prostate", "colon", "colique",
}
ENGLISH = {
    "diabetes", "diabetic", "sugar", "pressure", "headache", "headaches", "head", "fever", "cough",
    "pain", "ache", "stomach", "stomachache", "belly", "allergy", "cholesterol", "thyroid",
    "cold", "flu", "asthma", "insomnia", "sleep", "anxiety", "nausea", "diarrhea", "diarrhoea",
    "heart", "epilepsy", "seizures", "back", "tooth", "toothache", "skin", "eyes", "ear", "period",
    "pregnancy", "weight", "liver", "kidney", "anemia", "tired", "dizziness", "heartburn", "ulcer",
    "sore", "throat",
}
# Darija in Latin letters (arabizi)
ARABIZI = {
    "sokar", "soukar", "sukar", "skar", "rass", "ras", "rassi", "skhana", "s5ana", "kohha", "ko77a",
    "ka77a", "kohba", "wja3", "waja3", "kerch", "karch", "dahri", "snan", "9alb", "galb", "dokha",
}
ARABIC = {
    "سكر", "سكري", "ضغط", "طونسيون", "تونسيون", "راس", "صداع", "سخانة", "سخانه", "حمى", "كحة",
    "كحه", "سعال", "وجع", "الم", "كرش", "بطن", "معدة", "معده", "حساسية", "حساسيه", "كوليسترول",
    "كولسترول", "غدة", "غده", "درقية", "زكام", "نزلة", "انفلونزا", "ربو", "نوم", "قلب", "سرطان",
    "صرع", "اسهال", "امساك", "غثيان", "دوخة", "دوخه", "ضهر", "ظهر", "اسنان", "سنين", "ضرس", "عين",
    "عينين", "اذن", "كلى", "كبد", "حرقة", "قولون",
}

HEALTH_TERMS = FRENCH | ENGLISH | ARABIZI | ARABIC

# "السكر" (the sugar), "بالراس", "للكحة": Arabic article and prepositions
ARABIC_PREFIXES = ("وال", "بال", "لل", "ال")


def _forms(word: str):
    yield word
    for prefix in ARABIC_PREFIXES:
        if word.startswith(prefix) and len(word) - len(prefix) >= 2:
            yield word[len(prefix):]
            break


def health_words(words: list[str]) -> list[str]:
    """The words of the query that name a disease, a symptom or a use."""
    return [w for w in words if any(form in HEALTH_TERMS for form in _forms(w))]
