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

// Drawn test image; the API's simulated reader "reads" GLUCOPHAGE 850 mg on any photo
export const TEST_BOX_PHOTO = "e2e/fixtures/test-box.jpg";

// Delivery note demo: the API's simulated reader always "reads" the demo note
export const TAHOR_20 = "52225f9e6226";
export const TEGRETOL_200 = "f2c551ada27c";
