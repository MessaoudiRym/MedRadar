// Medicines shown as "Try:" examples on the home page. They are out of stock
// in many demo pharmacies (scripts/generate_demo_data.py), so a visitor sees
// at once why equivalents matter. Ids are stable (scripts/clean_nomenclature.py).

export const EXAMPLES = [
  { id: "55c9557e1e81", name: "Glucophage 850", use: "diabetes" },
  { id: "4a10b192b825", name: "Levothyrox 50 µg", use: "thyroid" },
  { id: "5e350d483b2c", name: "Amlor 5 mg", use: "blood pressure" },
];
