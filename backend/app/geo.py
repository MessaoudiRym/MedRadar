"""Distances and places."""

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0

# Rough bounding box of Algeria
ALGERIA_LAT = (18.9, 37.2)
ALGERIA_LNG = (-8.7, 12.0)

ORAN_CENTER = (35.697, -0.633)

# District centres in Oran, used for the demo data and to record the
# district of a search (never the exact position)
ORAN_DISTRICTS = {
    "Bir El Djir": (35.720, -0.555),
    "Es Senia": (35.648, -0.623),
    "Centre-ville": (35.697, -0.633),
    "USTO": (35.705, -0.585),
    "Akid Lotfi": (35.703, -0.598),
    "Canastel": (35.732, -0.582),
    "Gambetta": (35.700, -0.612),
    "Maraval": (35.690, -0.650),
    "El Hamri": (35.688, -0.620),
    "Hai Sabah": (35.705, -0.545),
}
DISTRICT_MAX_KM = 3.0


def haversine_km(lat1, lng1, lat2, lng2):
    """Distance between two points on Earth, in kilometres."""
    lat1, lng1, lat2, lng2 = map(radians, (lat1, lng1, lat2, lng2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def in_algeria(lat, lng):
    return ALGERIA_LAT[0] <= lat <= ALGERIA_LAT[1] and ALGERIA_LNG[0] <= lng <= ALGERIA_LNG[1]


def nearest_district(lat, lng):
    """Name of the closest known district, or None if none is within 3 km."""
    name, (d_lat, d_lng) = min(
        ORAN_DISTRICTS.items(), key=lambda item: haversine_km(lat, lng, *item[1]))
    return name if haversine_km(lat, lng, d_lat, d_lng) <= DISTRICT_MAX_KM else None
