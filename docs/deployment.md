# Mettre MedRadar en ligne, gratuitement

Ce guide met MedRadar en ligne, **sans carte bancaire**, avec uniquement des offres gratuites :

| Service | Rôle | Offre |
| --- | --- | --- |
| [Neon](https://neon.tech) | Base de données PostgreSQL | Free |
| [Render](https://render.com) | API (FastAPI) | Free |
| [Vercel](https://vercel.com) | Site (Next.js) | Hobby |
| [UptimeRobot](https://uptimerobot.com) | Surveille le site et empêche l'API de s'endormir | Free |
| GitHub Actions | Remet la démo à zéro chaque nuit, vérifie le site toutes les 6 heures | gratuit (dépôt public) |

Comptez environ **1 h 30** la première fois. Suivez les étapes **dans l'ordre** : chacune utilise ce que la précédente a créé.

> **Avant de commencer.** La branche `chore/deploy` doit être fusionnée dans `main` sur GitHub : Render et Vercel déploient `main`, et les tâches automatiques de GitHub ne tournent que depuis `main`.

Dans ce guide :
- `<api>` = l'adresse de votre API sur Render, par exemple `https://medradar-api.onrender.com` ;
- `<site>` = l'adresse de votre site sur Vercel, par exemple `https://medradar.vercel.app`.

Toujours **sans `/` à la fin**.

---

## a. Préparer les secrets de production

Les secrets de production doivent être **différents** de ceux de votre `.env` local. Si votre ordinateur ou votre `.env` fuit, la version en ligne reste protégée.

1. **JWT_SECRET** (signe les connexions). Dans un terminal, à la racine du projet :
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
   Copiez la ligne affichée (64 caractères environ).
2. **Mot de passe admin** : au moins 8 caractères, avec au moins une lettre et un chiffre. Choisissez-en un **nouveau**, jamais utilisé ailleurs.
3. **Mot de passe des pharmaciens de démo** (`DEMO_PHARMACIST_PASSWORD`) : même règle. **Attention : il sera public**, affiché sur la page `/demo` pour les visiteurs. Il doit donc être différent du mot de passe admin.
4. **Email admin** : l'adresse avec laquelle vous vous connecterez à `/admin`.

Notez ces 4 valeurs dans un endroit sûr : un gestionnaire de mots de passe, ou une note privée sur votre téléphone. **Jamais** dans un fichier du projet, ni dans un message, ni dans une conversation.

✅ **Vérification** : vous avez 4 valeurs notées, et aucune n'est identique à votre `.env` local.

---

## b. Neon : la base de données

1. Allez sur [neon.tech](https://neon.tech) → **Sign up** → **Continue with GitHub**. Aucune carte n'est demandée.
2. Créez un projet :
   - **Project name** : `medradar` ;
   - **Postgres version** : la version proposée par défaut ;
   - **Region** : **AWS Europe Central 1 (Frankfurt)**, la plus proche de l'Algérie.

   Cliquez **Create project**.
3. Sur la page du projet, cliquez **Connect** (en haut à droite).
   - **Désactivez « Connection pooling »**. L'adresse ne doit **pas** contenir `-pooler`. MedRadar a besoin de l'adresse directe pour ses migrations.
   - Copiez l'adresse qui commence par `postgresql://`. Elle ressemble à :
     `postgresql://neondb_owner:MOTDEPASSE@ep-xxx-yyy.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
   - Elle doit contenir `sslmode=require` : Neon refuse les connexions non chiffrées.
4. Cette adresse contient un mot de passe : notez-la avec vos secrets.

   > Si vous l'avez déjà collée quelque part (message, conversation, capture d'écran), changez le mot de passe : **Branches → main → Roles → neondb_owner → Reset password**, puis copiez la nouvelle adresse.
5. Testez la connexion depuis votre ordinateur.

   **Windows (PowerShell)**, à la racine du projet :
   ```powershell
   pip install -r backend/requirements.txt
   $env:DATABASE_URL = "COLLEZ_ICI_L_ADRESSE_NEON"
   python -c "import os, psycopg; print(psycopg.connect(os.environ['DATABASE_URL']).execute('select version()').fetchone()[0])"
   ```
   **Mac / Linux** :
   ```bash
   pip install -r backend/requirements.txt
   export DATABASE_URL="COLLEZ_ICI_L_ADRESSE_NEON"
   python -c "import os, psycopg; print(psycopg.connect(os.environ['DATABASE_URL']).execute('select version()').fetchone()[0])"
   ```

✅ **Vérification** : une ligne `PostgreSQL 17.x ...` s'affiche. Gardez ce terminal ouvert pour l'étape c.

---

## c. Préparer la base de production (depuis votre ordinateur)

Dans le **même terminal** que l'étape b : `DATABASE_URL` n'y existe que tant qu'il reste ouvert. Votre `.env` local n'est pas modifié, et votre version locale reste sur SQLite.

Les variables du terminal passent **avant** celles de `.env`. Les scripts utilisent donc bien vos valeurs de production.

**Windows (PowerShell)** :
```powershell
git checkout main
git pull
$env:DATABASE_URL = "COLLEZ_ICI_L_ADRESSE_NEON"     # déjà fait à l'étape b
$env:ADMIN_EMAIL = "votre-email-admin"
$env:ADMIN_PASSWORD = "MOT_DE_PASSE_ADMIN_DE_PRODUCTION"
$env:DEMO_PHARMACIST_PASSWORD = "MOT_DE_PASSE_DEMO_DE_PRODUCTION"

cd backend
python -m alembic upgrade head
cd ..
python scripts/create_admin.py
python scripts/reset_demo_data.py
```

**Mac / Linux** :
```bash
git checkout main && git pull
export DATABASE_URL="COLLEZ_ICI_L_ADRESSE_NEON"
export ADMIN_EMAIL="votre-email-admin"
export ADMIN_PASSWORD="MOT_DE_PASSE_ADMIN_DE_PRODUCTION"
export DEMO_PHARMACIST_PASSWORD="MOT_DE_PASSE_DEMO_DE_PRODUCTION"

cd backend && python -m alembic upgrade head && cd ..
python scripts/create_admin.py
python scripts/reset_demo_data.py
```

Ce que font ces commandes :
- `alembic upgrade head` crée les tables. Sans danger si elles existent déjà.
- `create_admin.py` crée votre compte admin. Relancé, il change seulement son mot de passe.
- `reset_demo_data.py` crée les 43 pharmacies de démo (dont 2 en attente de validation) et les 4 comptes `pharmacien1@medradar.demo` à `pharmacien4@medradar.demo`. Il ne touche jamais aux vraies pharmacies ni à l'admin.

✅ **Vérification** : la dernière ligne affichée est `Demo data reset: OK`. Dans Neon, ouvrez **Tables** : `pharmacies` contient 43 lignes et `users` en contient 5.

Fermez ensuite le terminal : les mots de passe tapés disparaissent avec lui.

---

## d. Render : l'API

1. Allez sur [render.com](https://render.com) → **Get Started** → **GitHub**. Aucune carte n'est demandée pour l'offre Free.
2. **Ne créez qu'UN SEUL service gratuit sur ce compte.** L'offre Free donne 750 heures par mois en tout. Un service allumé jour et nuit en utilise 720 à 744. Avec deux services, l'API serait arrêtée avant la fin du mois.
3. Cliquez **New → Blueprint**, autorisez Render à lire votre dépôt GitHub, puis choisissez **MedRadar**. Render lit le fichier `render.yaml`, qui décrit déjà tout :
   - offre **Free** ;
   - région **Frankfurt** ;
   - Python 3.12 ;
   - commande d'installation et de démarrage ;
   - vérification de santé sur `/health`.
4. Render demande la valeur des secrets. Remplissez :

   | Nom | Valeur à mettre | Où la trouver |
   | --- | --- | --- |
   | `DATABASE_URL` | L'adresse Neon **directe** (sans `-pooler`) | Étape b |
   | `JWT_SECRET` | La longue valeur générée | Étape a |
   | `FRONTEND_URL` | Laissez vide pour l'instant | Rempli à l'étape f |
   | `LLM_API_KEY` | Votre clé Gemini, ou vide (IA désactivée, tout le reste marche) | [Google AI Studio](https://aistudio.google.com/apikey) |
   | `EMAIL_API_KEY` | Votre clé Brevo, ou vide (alertes email cachées) | Brevo → SMTP & API → API keys |
   | `EMAIL_FROM` | L'adresse d'envoi vérifiée dans Brevo, ou vide | Brevo → Senders |

   Les autres variables (`PYTHON_VERSION`, `LLM_MODEL`…) ont déjà leur valeur dans `render.yaml`.
5. Cliquez **Apply**. Le premier déploiement prend 3 à 6 minutes.
6. Ouvrez le service **medradar-api** → onglet **Logs**. Vous devez voir dans l'ordre :
   ```
   INFO medradar: Database is up to date (migration ...)
   INFO:     Application startup complete.
   ```
   Sans `-pooler`, aucun avertissement ne doit apparaître sur le verrou des migrations.
7. En haut de la page du service, copiez l'adresse : c'est `<api>`.

✅ **Vérification** : ouvrez `<api>/health` dans le navigateur. Vous devez voir `"status":"ok"`, `"medicines":4384` et la liste des fonctionnalités. Ouvrez aussi `<api>/health/deep` : vous devez voir `"database":"ok"`.

---

## e. Vercel : le site

1. Allez sur [vercel.com](https://vercel.com) → **Sign Up** → **Hobby** → **Continue with GitHub**.
2. **Add New… → Project** → à côté de **MedRadar**, cliquez **Import**.
3. **Root Directory** : cliquez **Edit**, choisissez **`frontend`**, puis **Continue**. Le framework **Next.js** est détecté tout seul. Ne changez pas les commandes.
4. Ouvrez **Environment Variables** et ajoutez :

   | Nom | Valeur | Où la trouver |
   | --- | --- | --- |
   | `NEXT_PUBLIC_API_URL` | `<api>` (sans `/` final) | Étape d |
   | `NEXT_PUBLIC_DEMO_PHARMACIST_EMAIL` | `pharmacien1@medradar.demo` | Compte de démo avec historique |
   | `NEXT_PUBLIC_DEMO_PHARMACIST_PASSWORD` | Le mot de passe de démo | Étape a. Public, affiché sur `/demo` |
   | `NEXT_PUBLIC_GITHUB_URL` | `https://github.com/MessaoudiRym/MedRadar` | Votre dépôt |
   | `NEXT_PUBLIC_VIDEO_URL` | Le lien de la vidéo, ou vide | Plus tard. Vide = lien caché |
   | `NEXT_PUBLIC_SITE_URL` | Facultatif | Vercel donne sa propre adresse |

5. Cliquez **Deploy** (environ 2 minutes).
6. Cliquez **Continue to Dashboard**, puis copiez l'adresse sous **Domains** : c'est `<site>`.

✅ **Vérification** : ouvrez `<site>`. L'accueil s'affiche. Le bandeau « Starting the service… » peut apparaître quelques secondes si l'API dormait.

> Les variables `NEXT_PUBLIC_*` sont lues **au moment de la construction**. Si vous en changez une, allez dans **Deployments**, cliquez **⋯** sur le dernier déploiement, puis **Redeploy**.

---

## f. Relier le site et l'API

L'API refuse les appels des sites qu'elle ne connaît pas (CORS). Il faut lui donner l'adresse de votre site.

1. Render → **medradar-api** → **Environment** → `FRONTEND_URL` → **Edit**. Mettez `<site>`, par exemple `https://medradar.vercel.app`, **sans `/` à la fin**. Pour plusieurs adresses, séparez-les par des virgules.
2. Cliquez **Save, rebuild and deploy**, puis attendez « Live » (2 à 4 minutes).
3. Ouvrez `<site>/medicament/55c9557e1e81`, la fiche de Glucophage 850.
4. Ouvrez la console du navigateur : **F12** (ou clic droit → **Inspecter**) → onglet **Console**.

✅ **Vérification** :
- la fiche affiche 13 équivalents et la carte ;
- la console ne contient **aucune** ligne rouge `blocked by CORS policy`.

Si cette ligne apparaît, `FRONTEND_URL` ne correspond pas exactement à l'adresse du site : `https` ou `http`, un `/` en trop, ou une faute de frappe.

---

## g. GitHub : les vérifications automatiques

1. Sur GitHub, ouvrez votre dépôt → **Settings** → **Secrets and variables** → **Actions**.
2. Onglet **Secrets** → **New repository secret**, deux fois :

   | Nom | Valeur |
   | --- | --- |
   | `DATABASE_URL` | L'adresse Neon directe (étape b) |
   | `DEMO_PHARMACIST_PASSWORD` | Le mot de passe de démo (étape a) |

3. Onglet **Variables** → **New repository variable**, deux fois :

   | Nom | Valeur |
   | --- | --- |
   | `API_URL` | `<api>` |
   | `SITE_URL` | `<site>` |

4. Onglet **Actions** du dépôt. Si GitHub le demande, cliquez **I understand my workflows, go ahead and enable them**.
5. Choisissez **reset-demo** → **Run workflow** → **Run workflow**. Attendez la coche verte (environ 2 minutes).
6. Choisissez **smoke-test** → **Run workflow** → **Run workflow**.

✅ **Vérification** :
- les deux tâches sont vertes ;
- dans les logs de **smoke-test**, toutes les lignes commencent par ✅ et la dernière dit `12/12 checks passed`.

À partir de là :
- **reset-demo** remet la démo à zéro chaque nuit à **03:00 heure d'Alger** ;
- **smoke-test** vérifie le site toutes les **6 heures**. S'il échoue, GitHub vous envoie un email.

---

## h. UptimeRobot : surveiller et garder l'API éveillée

Sur l'offre Free, Render endort l'API après 15 minutes sans visite. Le réveil prend environ une minute. Un appel toutes les 5 minutes la garde éveillée.

1. Allez sur [uptimerobot.com](https://uptimerobot.com) → **Register for FREE**, puis confirmez votre email.
2. **+ New monitor** (ou **Add New Monitor**) :
   - **Monitor Type** : **HTTP(s)** ;
   - **Friendly Name** : `MedRadar API` ;
   - **URL** : `<api>/health` (surtout pas `/health/deep`, qui réveillerait la base Neon toutes les 5 minutes et userait son quota gratuit) ;
   - **Monitoring Interval** : **5 minutes** ;
   - **Alert contacts** : cochez votre email.

   Cliquez **Create Monitor**.
3. Créez un second moniteur de la même façon : `MedRadar site`, URL `<site>`, 5 minutes, alerte par email.

✅ **Vérification** : après quelques minutes, les deux moniteurs sont **Up** (en vert).

---

## i. Vérifications finales

Faites-les **en navigation privée**, une fois sur **ordinateur** et une fois sur **téléphone** (en 4G, sans le Wi-Fi de la maison).

| ✔ | Vérification | Ordinateur | Téléphone |
| --- | --- | --- | --- |
| ☐ | L'accueil s'affiche en moins de 5 secondes | ☐ | ☐ |
| ☐ | Une recherche avec une faute (`glucofage`) propose Glucophage | ☐ | ☐ |
| ☐ | La fiche Glucophage 850 s'ouvre | ☐ | ☐ |
| ☐ | 13 équivalents sont listés | ☐ | ☐ |
| ☐ | La carte affiche des pharmacies | ☐ | ☐ |
| ☐ | « Use my position » demande la position et trie par distance | ☐ | ☐ |
| ☐ | L'alerte email : formulaire présent si Brevo est configuré, et l'email arrive (regardez les spams) | ☐ | ☐ |
| ☐ | La page `/demo` s'ouvre, avec les onglets English et Français | ☐ | ☐ |
| ☐ | « Log in in one click » sur `/demo` connecte le pharmacien de démo | ☐ | ☐ |
| ☐ | Le pharmacien marque un médicament « Out of stock », et la fiche patient l'affiche (rechargez) | ☐ | ☐ |
| ☐ | Remettre ce médicament « In stock » | ☐ | ☐ |
| ☐ | La connexion admin sur `/pharmacien/connexion` mène à `/admin`, avec 2 pharmacies en attente | ☐ | ☐ |
| ☐ | IA, si la clé est mise : photo d'une boîte, recherche en arabe, scan du bon de démo | ☐ | ☐ |
| ☐ | La page `/confidentialite` s'ouvre | ☐ | ☐ |
| ☐ | Une adresse inconnue (`<site>/nimporte`) affiche « Page not found » | ☐ | ☐ |
| ☐ | **Test de veille** : ne visitez rien pendant 20 minutes, puis ouvrez `<site>`. La page s'affiche sans bandeau « Starting the service » : UptimeRobot a gardé l'API éveillée | ☐ | ☐ |

Vous pouvez aussi lancer les vérifications automatiques depuis votre ordinateur :
```powershell
# Windows (PowerShell), à la racine du projet
$env:DEMO_PHARMACIST_PASSWORD = "MOT_DE_PASSE_DEMO"
python scripts/smoke_test.py <api> <site>
cd frontend
$env:BASE_URL = "<site>"
npm run test:prod
```
```bash
# Mac / Linux
DEMO_PHARMACIST_PASSWORD="MOT_DE_PASSE_DEMO" python scripts/smoke_test.py <api> <site>
cd frontend && BASE_URL="<site>" DEMO_PHARMACIST_PASSWORD="MOT_DE_PASSE_DEMO" npm run test:prod
```

---

## j. Que faire si…

| Problème | Cause probable | Solution |
| --- | --- | --- |
| Le build **Vercel** échoue | Root Directory n'est pas `frontend` | Vercel → Settings → General → Root Directory = `frontend`, puis Redeploy |
| Le build **Render** échoue sur `pip install` | Version de Python | Vérifiez que `PYTHON_VERSION` = `3.12.8` dans Environment |
| La console affiche **`blocked by CORS policy`** | `FRONTEND_URL` différent de l'adresse du site | Étape f : adresse exacte, `https://`, sans `/` final, puis redéployer |
| Le site affiche « We can't reach MedRadar » | `NEXT_PUBLIC_API_URL` faux, ou l'API est arrêtée | Ouvrez `<api>/health`. S'il répond, corrigez la variable sur Vercel et faites **Redeploy** |
| Les logs Render disent **`DATABASE MIGRATION FAILED`** | `DATABASE_URL` faux, ou mot de passe Neon changé | Recopiez l'adresse Neon (directe, avec `sslmode=require`), puis Save and deploy |
| `<api>/health/deep` donne `"database":"unreachable"` | Neon inaccessible, ou mauvaise adresse | Vérifiez le projet dans Neon (pas suspendu), puis l'adresse |
| Avertissement **`pooled address`** dans les logs | L'adresse contient `-pooler` | Mettez l'adresse directe (Connect → pooling désactivé) |
| **502** ou « Service waking up » sur Render | L'API dormait ou redémarre | Attendez une minute : le site réessaie tout seul. Si cela revient souvent, vérifiez UptimeRobot (étape h) |
| Render dit **`Exited with status 1`** au démarrage | Variable obligatoire manquante, par exemple `JWT_SECRET` (32 caractères minimum) | Lisez la dernière ligne rouge des Logs : elle nomme la variable |
| La carte est vide, **aucune pharmacie** | Données de démo absentes | GitHub → Actions → **reset-demo** → Run workflow |
| « Log in in one click » répond « Incorrect email or password » | Mot de passe différent entre Vercel et la base | Même valeur dans Vercel (`NEXT_PUBLIC_DEMO_PHARMACIST_PASSWORD`) et dans GitHub (`DEMO_PHARMACIST_PASSWORD`), puis relancez **reset-demo** et faites Redeploy sur Vercel |
| Photo ou recherche en arabe : « try again later » | Quota Gemini gratuit dépassé | Attendre le lendemain. Le reste du site marche. `LLM_MODEL=gemini-3.5-flash-lite` a le plus grand quota |
| Une variable manque ou est mal écrite | Faute de frappe dans un nom | Comparez avec `render.yaml` (API) et `frontend/.env.example` (site) |
| **smoke-test** échoue sur GitHub | Une des vérifications | Ouvrez le log : la ligne ❌ dit laquelle et pourquoi |

---

## k. Pendant une période de démonstration

**Chaque matin (5 minutes)** :
1. Vos emails : aucune alerte UptimeRobot ni échec **smoke-test** de GitHub ?
2. GitHub → **Actions** : **reset-demo** de la nuit est vert ?
3. Ouvrez `<site>`, faites une recherche et ouvrez une fiche.
4. Render → **Logs** : pas de série d'erreurs `500`.
5. Neon → **Monitoring** : la base n'approche pas les limites de l'offre gratuite.

**Si un visiteur a modifié la démo** (adresse changée, pharmacie en attente…) : GitHub → Actions → **reset-demo** → **Run workflow**. Tout revient en 2 minutes.

**Règle d'or : AUCUN push sur `main` pendant la période de démonstration, ni la veille.** Chaque push sur `main` redéploie l'API et le site pendant que des visiteurs testent. Seule exception : une correction **urgente**, d'abord testée en local (`pytest`, `npm run test:e2e`, `npm run build`), puis vérifiée avec `scripts/smoke_test.py` juste après le déploiement.
