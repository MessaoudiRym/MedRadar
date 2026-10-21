"""Start the API for the end-to-end tests, on a fresh database.

Used by frontend/playwright.config.ts. Each run:
  1. deletes and recreates backend/e2e.db (never the development database),
  2. runs the migrations, creates the admin and the demo data,
  3. starts the API on port 8100, with the simulated photo reader.

Test credentials come from the environment set by the Playwright config.

Usage (normally started by Playwright):
    python scripts/run_e2e_api.py
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DATABASE = BACKEND / "e2e.db"
PORT = os.environ.get("E2E_API_PORT", "8100")


def main():
    DATABASE.unlink(missing_ok=True)
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": f"sqlite:///{DATABASE.as_posix()}",
        "JWT_SECRET": env.get("E2E_JWT_SECRET", "e2e-only-secret-" + "x" * 40),
        "FRONTEND_URL": env.get("E2E_FRONTEND_URL", "http://localhost:3100"),
        # Photo recognition with the simulated reader: it always "reads" GLUCOPHAGE 850,
        # and no photo is sent to a real model
        "LLM_PROVIDER": "fake",
    })
    for name in ("ADMIN_EMAIL", "ADMIN_PASSWORD", "DEMO_PHARMACIST_PASSWORD"):
        if not env.get(name):
            sys.exit(f"{name} must be set (the Playwright config sets it).")

    run = lambda *args, cwd=ROOT: subprocess.run([sys.executable, *args], cwd=cwd, env=env, check=True)
    run("-m", "alembic", "upgrade", "head", cwd=BACKEND)
    run(str(ROOT / "scripts" / "create_admin.py"))
    run(str(ROOT / "scripts" / "generate_demo_data.py"))

    # Runs until Playwright stops it at the end of the tests
    run("-m", "uvicorn", "app.main:app", "--port", PORT, cwd=BACKEND)


if __name__ == "__main__":
    main()
