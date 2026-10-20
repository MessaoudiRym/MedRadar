// Values used only by the end-to-end tests (fresh database at each run).

export const API_PORT = 8100;
export const WEB_PORT = 3100;
export const API_URL = `http://localhost:${API_PORT}`;
export const WEB_URL = `http://localhost:${WEB_PORT}`;

export const ADMIN = { email: "e2e-admin@example.com", password: "E2eAdmin2026" };
export const DEMO_PASSWORD = "E2eDemo2026";
export const DEMO_PHARMACIST = { email: "pharmacien1@medradar.demo", password: DEMO_PASSWORD };

// Stable ids from scripts/clean_nomenclature.py
export const GLUCOPHAGE_850 = "55c9557e1e81";
