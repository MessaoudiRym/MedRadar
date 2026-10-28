# Putting MedRadar online, for free

This guide puts MedRadar online **without a credit card**, using free plans only:

| Service | Role | Plan |
| --- | --- | --- |
| [Neon](https://neon.tech) | PostgreSQL database | Free |
| [Render](https://render.com) | API (FastAPI) | Free |
| [Vercel](https://vercel.com) | Website (Next.js) | Hobby |
| [UptimeRobot](https://uptimerobot.com) | Monitors the site and keeps the API from sleeping | Free |
| GitHub Actions | Resets the demo every night, checks the site every 6 hours | free (public repository) |

Allow about **1 h 30** the first time. Follow the steps **in order**: each one uses what the previous one created.

> **Before you start.** Render and Vercel deploy the `main` branch, and GitHub's scheduled tasks only run from `main`: everything below must already be merged into `main`.

In this guide:
- `<api>` = the address of your API on Render, for example `https://medradar-api.onrender.com`;
- `<site>` = the address of your site on Vercel, for example `https://medradar.vercel.app`.

Always **without a `/` at the end**.

---

## a. Prepare the production secrets

Production secrets must be **different** from the ones in your local `.env`. If your computer or your `.env` leaks, the online version stays protected.

1. **JWT_SECRET** (signs logins). In a terminal, at the root of the project:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
   Copy the line it prints (about 64 characters).
2. **Admin password**: at least 8 characters, with at least one letter and one digit. Choose a **new** one, never used anywhere else.
3. **Demo pharmacist password** (`DEMO_PHARMACIST_PASSWORD`): same rule. **Careful: it will be public**, shown on the `/demo` page for visitors. It must therefore be different from the admin password.
4. **Admin email**: the address you will use to log in to `/admin`.

Write these 4 values down somewhere safe: a password manager, or a private note on your phone. **Never** in a project file, a message or a conversation.

✅ **Check**: you have 4 values written down, and none of them is the same as in your local `.env`.

---

## b. Neon: the database

1. Go to [neon.tech](https://neon.tech) → **Sign up** → **Continue with GitHub**. No card is asked for.
2. Create a project:
   - **Project name**: `medradar`;
   - **Postgres version**: the default one;
   - **Region**: **AWS Europe Central 1 (Frankfurt)**, the closest to Algeria.

   Click **Create project**.
3. On the project page, click **Connect** (top right).
   - **Turn off "Connection pooling"**. The address must **not** contain `-pooler`: MedRadar needs the direct address for its migrations.
   - Copy the address that starts with `postgresql://`. It looks like:
     `postgresql://neondb_owner:PASSWORD@ep-xxx-yyy.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
   - It must contain `sslmode=require`: Neon refuses unencrypted connections.
4. This address contains a password: keep it with your secrets.

   > If you have already pasted it somewhere (a message, a conversation, a screenshot), change the password: **Branches → main → Roles → neondb_owner → Reset password**, then copy the new address.
5. Test the connection from your computer.

   **Windows (PowerShell)**, at the root of the project:
   ```powershell
   pip install -r backend/requirements.txt
   $env:DATABASE_URL = "PASTE_THE_NEON_ADDRESS_HERE"
   python -c "import os, psycopg; print(psycopg.connect(os.environ['DATABASE_URL']).execute('select version()').fetchone()[0])"
   ```
   **Mac / Linux**:
   ```bash
   pip install -r backend/requirements.txt
   export DATABASE_URL="PASTE_THE_NEON_ADDRESS_HERE"
   python -c "import os, psycopg; print(psycopg.connect(os.environ['DATABASE_URL']).execute('select version()').fetchone()[0])"
   ```

✅ **Check**: a line `PostgreSQL 17.x ...` is printed. Keep this terminal open for step c.

---

## c. Prepare the production database (from your computer)

Use the **same terminal** as in step b: `DATABASE_URL` only exists there while it stays open. Your local `.env` is not changed, and your local version stays on SQLite.

Variables set in the terminal win over the ones in `.env`, so the scripts really use your production values.

**Windows (PowerShell)**:
```powershell
git checkout main
git pull
$env:DATABASE_URL = "PASTE_THE_NEON_ADDRESS_HERE"     # already done in step b
$env:ADMIN_EMAIL = "your-admin-email"
$env:ADMIN_PASSWORD = "PRODUCTION_ADMIN_PASSWORD"
$env:DEMO_PHARMACIST_PASSWORD = "PRODUCTION_DEMO_PASSWORD"

cd backend
python -m alembic upgrade head
cd ..
python scripts/create_admin.py
python scripts/reset_demo_data.py
```

**Mac / Linux**:
```bash
git checkout main && git pull
export DATABASE_URL="PASTE_THE_NEON_ADDRESS_HERE"
export ADMIN_EMAIL="your-admin-email"
export ADMIN_PASSWORD="PRODUCTION_ADMIN_PASSWORD"
export DEMO_PHARMACIST_PASSWORD="PRODUCTION_DEMO_PASSWORD"

cd backend && python -m alembic upgrade head && cd ..
python scripts/create_admin.py
python scripts/reset_demo_data.py
```

What these commands do:
- `alembic upgrade head` creates the tables. Safe if they already exist.
- `create_admin.py` creates your admin account. Run again, it only changes its password.
- `reset_demo_data.py` creates the 43 demo pharmacies (2 of them waiting for validation) and the 4 accounts `pharmacien1@medradar.demo` to `pharmacien4@medradar.demo`. It never touches real pharmacies or the admin.

✅ **Check**: the last line printed is `Demo data reset: OK`. In Neon, open **Tables**: `pharmacies` has 43 rows and `users` has 5.

Then close the terminal: the passwords you typed disappear with it.

---

## d. Render: the API

1. Go to [render.com](https://render.com) → **Get Started** → **GitHub**. No card is asked for on the Free plan.
2. **Create only ONE free service on this account.** The Free plan gives 750 hours a month in total. One service running day and night uses 720 to 744. With two services, the API would be stopped before the end of the month.
3. Click **New → Blueprint**, let Render read your GitHub repository, then choose **MedRadar**. Render reads the `render.yaml` file, which already describes everything:
   - **Free** plan;
   - **Frankfurt** region;
   - Python 3.12;
   - install and start commands;
   - health check on `/health`.
4. Render asks for the value of the secrets. Fill in:

   | Name | Value | Where to find it |
   | --- | --- | --- |
   | `DATABASE_URL` | The **direct** Neon address (without `-pooler`) | Step b |
   | `JWT_SECRET` | The long generated value | Step a |
   | `FRONTEND_URL` | Leave empty for now | Filled in at step f |
   | `LLM_API_KEY` | Your Gemini key, or empty (AI off, everything else works) | [Google AI Studio](https://aistudio.google.com/apikey) |
   | `EMAIL_API_KEY` | Your Brevo key, or empty (email alerts hidden) | Brevo → SMTP & API → API keys |
   | `EMAIL_FROM` | The sender address verified in Brevo, or empty | Brevo → Senders |

   The other variables (`PYTHON_VERSION`, `LLM_MODEL`…) already have their value in `render.yaml`.
5. Click **Apply**. The first deploy takes 3 to 6 minutes.
6. Open the **medradar-api** service → **Logs** tab. You should see, in this order:
   ```
   INFO medradar: Database is up to date (migration ...)
   INFO:     Application startup complete.
   ```
   Without `-pooler`, no warning about the migration lock should appear.
7. At the top of the service page, copy the address: this is `<api>`.

✅ **Check**: open `<api>/health` in the browser. You should see `"status":"ok"`, `"medicines":4384` and the list of features. Also open `<api>/health/deep`: you should see `"database":"ok"`.

---

## e. Vercel: the website

1. Go to [vercel.com](https://vercel.com) → **Sign Up** → **Hobby** → **Continue with GitHub**.
2. **Add New… → Project** → next to **MedRadar**, click **Import**.
3. **Root Directory**: click **Edit**, choose **`frontend`**, then **Continue**. The **Next.js** framework is detected automatically. Do not change the commands.
4. Open **Environment Variables** and add:

   | Name | Value | Where to find it |
   | --- | --- | --- |
   | `NEXT_PUBLIC_API_URL` | `<api>` (no `/` at the end) | Step d |
   | `NEXT_PUBLIC_DEMO_PHARMACIST_EMAIL` | `pharmacien1@medradar.demo` | Demo account with a history |
   | `NEXT_PUBLIC_DEMO_PHARMACIST_PASSWORD` | The demo password | Step a. Public, shown on `/demo` |
   | `NEXT_PUBLIC_GITHUB_URL` | `https://github.com/MessaoudiRym/MedRadar` | Your repository |
   | `NEXT_PUBLIC_VIDEO_URL` | The video link, or empty | Later. Empty = link hidden |
   | `NEXT_PUBLIC_SITE_URL` | Optional | Vercel gives its own address |

5. Click **Deploy** (about 2 minutes).
6. Click **Continue to Dashboard**, then copy the address under **Domains**: this is `<site>`.

✅ **Check**: open `<site>`. The home page shows. The "Starting the service…" banner may appear for a few seconds if the API was asleep.

> `NEXT_PUBLIC_*` variables are read **when the site is built**. If you change one, go to **Deployments**, click **⋯** on the latest deployment, then **Redeploy**.

---

## f. Connect the site and the API

The API refuses calls from sites it does not know (CORS). It needs the address of your site.

1. Render → **medradar-api** → **Environment** → `FRONTEND_URL` → **Edit**. Put `<site>`, for example `https://medradar.vercel.app`, **without a `/` at the end**. For several addresses, separate them with commas.
2. Click **Save, rebuild and deploy**, then wait for "Live" (2 to 4 minutes).
3. Open `<site>/medicament/55c9557e1e81`, the page of Glucophage 850.
4. Open the browser console: **F12** (or right click → **Inspect**) → **Console** tab.

✅ **Check**:
- the page shows 13 equivalents and the map;
- the console has **no** red line `blocked by CORS policy`.

If that line appears, `FRONTEND_URL` does not match the address of the site exactly: `https` or `http`, an extra `/`, or a typo.

---

## g. GitHub: the automatic checks

1. On GitHub, open your repository → **Settings** → **Secrets and variables** → **Actions**.
2. **Secrets** tab → **New repository secret**, twice:

   | Name | Value |
   | --- | --- |
   | `DATABASE_URL` | The direct Neon address (step b) |
   | `DEMO_PHARMACIST_PASSWORD` | The demo password (step a) |

3. **Variables** tab → **New repository variable**, twice:

   | Name | Value |
   | --- | --- |
   | `API_URL` | `<api>` |
   | `SITE_URL` | `<site>` |

4. **Actions** tab of the repository. If GitHub asks, click **I understand my workflows, go ahead and enable them**.
5. Choose **reset-demo** → **Run workflow** → **Run workflow**. Wait for the green tick (about 2 minutes).
6. Choose **smoke-test** → **Run workflow** → **Run workflow**.

✅ **Check**:
- both runs are green;
- in the **smoke-test** logs, every line starts with ✅ and the last one says `12/12 checks passed`.

From then on:
- **reset-demo** resets the demo every night at **03:00 Algiers time**;
- **smoke-test** checks the site every **6 hours**. If it fails, GitHub emails you.

---

## h. UptimeRobot: monitor and keep the API awake

On the Free plan, Render puts the API to sleep after 15 minutes without visits, and waking up takes about a minute. A call every 5 minutes keeps it awake.

1. Go to [uptimerobot.com](https://uptimerobot.com) → **Register for FREE**, then confirm your email.
2. **+ New monitor** (or **Add New Monitor**):
   - **Monitor Type**: **HTTP(s)**;
   - **Friendly Name**: `MedRadar API`;
   - **URL**: `<api>/health` (never `/health/deep`, which would wake the Neon database every 5 minutes and use up its free quota);
   - **Monitoring Interval**: **5 minutes**;
   - **Alert contacts**: tick your email.

   Click **Create Monitor**.
3. Create a second monitor the same way: `MedRadar site`, URL `<site>`, 5 minutes, email alert.

✅ **Check**: after a few minutes, both monitors are **Up** (green).

---

## i. Final checks

Do them **in a private window**, once on a **computer** and once on a **phone** (on mobile data, not your home Wi-Fi).

| ✔ | Check | Computer | Phone |
| --- | --- | --- | --- |
| ☐ | The home page shows in less than 5 seconds | ☐ | ☐ |
| ☐ | A search with a typo (`glucofage`) suggests Glucophage | ☐ | ☐ |
| ☐ | The Glucophage 850 page opens | ☐ | ☐ |
| ☐ | 13 equivalents are listed | ☐ | ☐ |
| ☐ | The map shows pharmacies | ☐ | ☐ |
| ☐ | "Use my position" asks for the position and sorts by distance | ☐ | ☐ |
| ☐ | Email alert: the form is there when Brevo is set up, and the email arrives (check the spam folder) | ☐ | ☐ |
| ☐ | The `/demo` page opens, with the English and Français tabs | ☐ | ☐ |
| ☐ | "Log in in one click" on `/demo` logs the demo pharmacist in | ☐ | ☐ |
| ☐ | The pharmacist marks a medicine "Out of stock", and the patient page shows it (reload) | ☐ | ☐ |
| ☐ | Put that medicine back "In stock" | ☐ | ☐ |
| ☐ | The admin login on `/pharmacien/connexion` leads to `/admin`, with 2 pharmacies waiting | ☐ | ☐ |
| ☐ | AI, if the key is set: photo of a box, search in Arabic, scan of the demo note | ☐ | ☐ |
| ☐ | The `/confidentialite` page opens | ☐ | ☐ |
| ☐ | An unknown address (`<site>/anything`) shows "Page not found" | ☐ | ☐ |
| ☐ | **Sleep test**: visit nothing for 20 minutes, then open `<site>`. The page shows without the "Starting the service" banner: UptimeRobot kept the API awake | ☐ | ☐ |

You can also run the automatic checks from your computer:
```powershell
# Windows (PowerShell), at the root of the project
$env:DEMO_PHARMACIST_PASSWORD = "DEMO_PASSWORD"
python scripts/smoke_test.py <api> <site>
cd frontend
$env:BASE_URL = "<site>"
npm run test:prod
```
```bash
# Mac / Linux
DEMO_PHARMACIST_PASSWORD="DEMO_PASSWORD" python scripts/smoke_test.py <api> <site>
cd frontend && BASE_URL="<site>" DEMO_PHARMACIST_PASSWORD="DEMO_PASSWORD" npm run test:prod
```

---

## j. What to do if…

| Problem | Likely cause | Solution |
| --- | --- | --- |
| The **Vercel** build fails | Root Directory is not `frontend` | Vercel → Settings → General → Root Directory = `frontend`, then Redeploy |
| The **Render** build fails on `pip install` | Python version | Check that `PYTHON_VERSION` = `3.12.8` in Environment |
| The console shows **`blocked by CORS policy`** | `FRONTEND_URL` differs from the address of the site | Step f: exact address, `https://`, no `/` at the end, then redeploy |
| The site shows "We can't reach MedRadar" | `NEXT_PUBLIC_API_URL` is wrong, or the API is stopped | Open `<api>/health`. If it answers, fix the variable on Vercel and **Redeploy** |
| The Render logs say **`DATABASE MIGRATION FAILED`** | Wrong `DATABASE_URL`, or the Neon password was changed | Copy the Neon address again (direct, with `sslmode=require`), then Save and deploy |
| `<api>/health/deep` gives `"database":"unreachable"` | Neon cannot be reached, or wrong address | Check the project in Neon (not suspended), then the address |
| **`pooled address`** warning in the logs | The address contains `-pooler` | Use the direct address (Connect → pooling turned off) |
| **502** or "Service waking up" on Render | The API was asleep or is restarting | Wait a minute: the site retries by itself. If it happens often, check UptimeRobot (step h) |
| Render says **`Exited with status 1`** at startup | A required variable is missing, for example `JWT_SECRET` (32 characters minimum) | Read the last red line of the Logs: it names the variable |
| The map is empty, **no pharmacy** | Demo data missing | GitHub → Actions → **reset-demo** → Run workflow |
| "Log in in one click" answers "Incorrect email or password" | Different password on Vercel and in the database | Same value on Vercel (`NEXT_PUBLIC_DEMO_PHARMACIST_PASSWORD`) and on GitHub (`DEMO_PHARMACIST_PASSWORD`), then run **reset-demo** again and Redeploy on Vercel |
| Photo or Arabic search: "try again later" | Free Gemini quota used up | Wait until the next day: the rest of the site works. `LLM_MODEL=gemini-3.5-flash-lite` has the largest quota |
| A variable is missing or misspelt | Typo in a name | Compare with `render.yaml` (API) and `frontend/.env.example` (site) |
| **smoke-test** fails on GitHub | One of the checks | Open the log: the ❌ line says which one and why |

---

## k. During a demo period

**Every morning (5 minutes)**:
1. Your emails: no UptimeRobot alert and no failed GitHub **smoke-test**?
2. GitHub → **Actions**: is last night's **reset-demo** green?
3. Open `<site>`, run a search and open a medicine page.
4. Render → **Logs**: no series of `500` errors.
5. Neon → **Monitoring**: the database is not close to the limits of the free plan.

**If a visitor changed the demo** (address changed, pharmacy waiting for verification…): GitHub → Actions → **reset-demo** → **Run workflow**. Everything is back in 2 minutes.

**Golden rule: NO push to `main` during the demo period, nor the day before.** Every push to `main` redeploys the API and the site while visitors are testing. Only exception: an **urgent** fix, first tested locally (`pytest`, `npm run test:e2e`, `npm run build`), then checked with `scripts/smoke_test.py` right after the deploy.
