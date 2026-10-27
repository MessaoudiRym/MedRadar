# Rapport d'audit qualité — MedRadar

Audit du 27 octobre 2026, branche `fix/qa-audit` (partie de `main` au commit `04a546c`, après la fusion de la PR #5).

## Verdict : PAS ENCORE PRÊT

Aucun problème **bloquant**. Le parcours du juge (chercher un médicament, voir ses équivalents et la carte, se connecter comme pharmacien et changer un stock) fonctionne sur ordinateur et sur mobile, sans erreur.

Il reste **4 problèmes majeurs**. Chacun demande une décision de votre part, car il touche au produit ou au déploiement :

1. **Les alertes par email ne sont jamais envoyées.** L'alerte est enregistrée, et le patient lit « We will email you… », mais aucun service d'email n'existe dans le code.
2. **Les comptes de démo sont partagés et modifiables.** Un juge qui change l'adresse de la pharmacie de démo la renvoie « en vérification » : le juge suivant ne peut plus changer de stock. Le mot de passe peut aussi être changé par l'API.
3. **Quota Gemini.** La photo de boîte et le scan de bon utilisent `gemini-3.8-flash`, dont l'offre gratuite n'autorise que 20 requêtes par jour, sans modèle de secours en cas de quota dépassé (429).
4. **La base PostgreSQL de production n'a jamais été testée.** Son pilote (`psycopg`) n'est pas dans `requirements.txt` : l'API ne démarrerait pas avec une `DATABASE_URL` PostgreSQL.

Le détail et mes recommandations figurent dans la section « Problèmes restants ».

## Résultats des tests (après les corrections)

| Contrôle | Résultat |
| --- | --- |
| Tests backend (`python -m pytest`) | **197 réussis**. Seul avertissement : une dépréciation dans Starlette, la bibliothèque, pas dans le code du projet |
| Tests de bout en bout (`npm run test:e2e`, ordinateur et mobile) | **52 réussis**, dont 4 nouveaux tests de non-régression |
| `npm run lint` | 0 erreur, 0 avertissement |
| `npx tsc --noEmit` | OK |
| `npm run build` | OK, sans avertissement |
| axe-core (WCAG 2.1 A et AA), 16 pages × 2 appareils | **0 violation**, toutes gravités confondues |
| `scripts/check_equivalents.py` (10 marques) | **Identique** à `docs/verification_equivalents.md` (161 équivalents) |
| Secrets dans le dépôt et dans tout l'historique git | **Aucun** (détails plus bas) |

### Lighthouse (mobile, version de production locale)

| Page | Performance | Accessibilité | Bonnes pratiques | SEO |
| --- | --- | --- | --- | --- |
| Accueil | 79 à 85 | 100 | 100 | 100 |
| Fiche médicament (GLUCOPHAGE 850), avant correction | 47 | 97 | 100 | 91 |
| Fiche médicament, après correction | **64** | 97 | 100 | 91 |

- Sur la fiche, le décalage de mise en page (CLS) passe de 0,339 à **0**.
- Ce qui reste :
  - le temps de JavaScript (TBT d'environ 800 ms), dû à la carte Leaflet et à Next.js ;
  - des marqueurs de carte trop proches pour le doigt : la liste des pharmacies, juste au-dessus, offre les mêmes actions ;
  - une « meta description » que Lighthouse ne voit pas. Elle existe, mais Next 16 l'envoie en flux, après le `<head>`.
- Les mesures sont faites en local, sans réseau mobile réel. Les scores varient de ±5 points d'une mesure à l'autre.

## Corrections faites

| # | Commit | Problème | Gravité |
| --- | --- | --- | --- |
| 1 | `b1e1dff` | **Plantage de la carte avec le bouton Retour du navigateur.** Le scénario : fiche → clic sur un équivalent → Retour, et la page affichait « Something went wrong ». Next 16 garde les pages visitées en mémoire, et la carte Leaflet était réutilisée alors qu'elle avait été détruite. Le problème touchait aussi la carte de l'inscription, de « Edit my pharmacy » et de l'admin. Test e2e ajouté | Majeur |
| 2 | `7ec31bb` | **Carte vide pour un visiteur hors d'Oran.** Un juge à Alger ou en France qui partageait sa position voyait « No pharmacy within 10 km » et une carte vide. Si la permission était déjà accordée, cela arrivait même sans clic. La page reste maintenant sur le centre d'Oran et l'explique. Test e2e ajouté | Majeur |
| 3 | `4f1133e` | Une recherche de plus de 100 caractères affichait « Something went wrong ». Le champ est maintenant limité à 100 caractères, comme l'API, et un lien plus long est raccourci | Mineur |
| 4 | `b754151` | Quand l'API est injoignable, la page du scanner disait à une pharmacie approuvée « Available once your pharmacy is approved ». Elle affiche maintenant l'erreur de connexion, avec « Try again » | Mineur |
| 5 | `9b1b27c` | Le pied de page sautait au chargement de la fiche (Lighthouse : CLS 0,34 → 0) | Mineur |
| 6 | `41bebd0` | Le texte indicatif du champ de recherche était coupé sur téléphone (« Medicine name (Fr ») | Mineur |
| 7 | `25bed4d` | README : installation depuis zéro (détails plus bas) | Majeur pour un développeur ou un juge |
| 8 | `abdc307` | `.env.example` : variables facultatives non décrites | Mineur |

## Problèmes restants

### Majeurs (à décider avant la mise en ligne)

| Problème | Ce qui se passe | Ma recommandation |
| --- | --- | --- |
| Alertes email non envoyées | `POST /alerts` enregistre l'alerte. Le message dit « Alerte enregistrée. Vous serez prévenu(e) par email », et l'écran dit « We will email … », mais rien n'est jamais envoyé : il n'y a ni service d'email ni tâche d'envoi (`EMAIL_API_KEY` n'est lu nulle part). | Soit implémenter l'envoi, ce qui est une **nouvelle fonctionnalité** à faire sur sa propre branche. Soit, pour la soutenance, changer le texte en « Alert saved. Email sending will be added soon » et le dire dans « Not finished yet ». Je ne l'ai pas changé : c'est un choix de produit. |
| Comptes de démo modifiables par tous | Avec `pharmacien1` ou `pharmacien2`, « Edit my pharmacy » permet de changer l'adresse : la pharmacie repasse « en vérification », et le juge suivant ne peut plus déclarer de stock. Je l'ai vérifié pendant l'audit. `POST /auth/change-password` permet aussi de changer le mot de passe. | Au minimum, relancer `python scripts/generate_demo_data.py` juste avant la soutenance et donner `pharmacien1` au juge. Mieux : interdire ces deux modifications aux comptes `@medradar.demo` (une petite modification côté API, à valider par vous). |
| Quota Gemini 20 par jour | Photo de boîte et scan de bon passent par `gemini-3.8-flash` (20 requêtes par jour sur l'offre gratuite). Le modèle de secours n'est essayé que sur une erreur 503, pas sur un quota dépassé (429). Pendant l'audit, 4 lectures réelles ont réussi (scan : 11 et 24 s ; photo : 28 s). | Mettre `LLM_MODEL=gemini-3.5-flash-lite` sur le serveur de production, ou essayer le modèle de secours aussi sur une erreur 429. À valider : l'évaluation du scan (100 %) a été faite avec 3.8-flash. |
| PostgreSQL non testé | Le README et `.env.example` annoncent PostgreSQL en production, mais `psycopg` n'est dans aucun `requirements.txt` et rien n'a été testé sur PostgreSQL (migrations, recherche). | Ajouter `psycopg[binary]` aux dépendances et lancer `alembic upgrade head` puis les tests sur une vraie base PostgreSQL, ou déployer avec SQLite sur un disque persistant. J'ai ajouté l'information dans le README, sans toucher aux dépendances. |

### Mineurs

| Problème | Recommandation |
| --- | --- |
| La dose est répétée dans les titres quand le nom officiel la contient déjà : « Glucophage 850 850 mg » | Ne pas ajouter la dose si le nom se termine déjà par ce nombre. Cela touche 8 composants, donc je ne l'ai pas fait. |
| En tapant « gluco », les 8 suggestions ne contiennent pas GLUCOPHAGE (ordre alphabétique : Glucobay, Glucoformine…). Il apparaît dès « glucop », et la recherche validée le met en premier | Classer les noms les plus connus en premier, si vous le souhaitez |
| `/admin` sans connexion renvoie vers « Pharmacist login », avec « Register your pharmacy » | Ajouter une phrase « Admin? Log in here too », ou un titre neutre |
| Sans clé Gemini, l'onglet « Scan a note » reste dans le menu pharmacien. La page explique alors que le scan n'est pas disponible | Acceptable |
| La fiche d'un médicament inconnu lance 3 requêtes qui échouent en 404 (visibles dans la console), mais le message à l'écran est clair | Acceptable |
| Le CSV exporté sans filtre s'appelle `medradar-delivery-notes-start-today.csv` | Cosmétique |
| La limite de 5 connexions par minute est comptée par adresse IP : un jury entier derrière le même Wi-Fi qui se trompe plusieurs fois attend une minute | Acceptable, et le message est clair : « Too many attempts. Please try again in a minute. » |

## Tableau de tous les contrôles

Résultat : **OK**, **corrigé** (avec le numéro de correction), ou **problème restant**. Gravité : seulement pour ce qui n'était pas OK.

### 1. Installation depuis zéro

| Fonctionnalité | Étape | Résultat | Gravité |
| --- | --- | --- | --- |
| Clone | `git clone` depuis GitHub dans un dossier vide | Corrigé (7) : l'URL du README était `<your-username>` | Mineur |
| Prérequis | Versions de Python et de Node | Corrigé (7) : absentes, ajoutées (Python 3.12, Node 20, testés) | Mineur |
| Données | `clean_nomenclature.py`, puis `check_equivalents.py` | OK : le CSV produit est identique à celui du dépôt, le fichier officiel n'est pas modifié | — |
| `.env` | `cp .env.example .env` et `JWT_SECRET` | OK | — |
| Backend | `pip install`, `alembic upgrade head` (4 migrations), `create_admin.py`, `generate_demo_data.py` | OK, dans un environnement Python neuf | — |
| Comptes de démo | Quels identifiants utiliser ? | Corrigé (7) : le README ne les donnait pas (emails, mot de passe, quelle pharmacie est approuvée ou en attente, où l'admin se connecte) | Majeur |
| API | `uvicorn`, `/health`, `/medicines/search?q=glucofage` | OK | — |
| Frontend | `npm install` (0 vulnérabilité), `.env.local`, `npm run dev` | OK | — |
| README | Pile technique | Corrigé (7) : « PostgreSQL (pg_trgm) » était faux (SQLite en développement, recherche en mémoire avec RapidFuzz), et la ligne IA ne citait que la photo | Mineur |
| README | Tableaux des routes et des pages | Corrigé (7) : `/features` renvoie aussi `delivery_scan`, la page `/pharmacien/pharmacie` manquait | Mineur |
| `.env.example` | Toutes les variables du code y figurent, aucune vraie valeur | OK. Corrigé (8) : `MEDICINES_CSV` manquait (facultative), le commentaire de la clé ne citait que la photo, et `EMAIL_API_KEY` est maintenant marquée « not read by the code yet » | Mineur |
| PostgreSQL | Pilote installé ? | Problème restant : `psycopg` absent. Information ajoutée au README | Majeur |

### 2. Qualité et secrets

| Fonctionnalité | Étape | Résultat | Gravité |
| --- | --- | --- | --- |
| Tests backend | `pytest` | OK : 197 réussis | — |
| Tests e2e | `npm run test:e2e` | OK : 52 réussis | — |
| Lint, TypeScript, build | `npm run lint`, `tsc`, `npm run build` | OK, sans avertissement | — |
| Secrets | Clés (`AIza…`, `sk-…`, `ghp_…`, clés privées) dans tout l'historique (`git log --all -p`) | OK : aucune | — |
| Secrets | Fichiers `.env`, `.db`, `.pem` ou `.key` jamais commités | OK : seuls `.env.example` et `frontend/.env.example` | — |
| Secrets | Mots de passe dans le code | OK : seulement des valeurs de test (`Admin2026x` dans `backend/tests/conftest.py`, `E2eDemo2026` dans `frontend/e2e/config.ts`), utilisées sur des bases temporaires. Vos vrais mots de passe du `.env` sont différents, et `JWT_SECRET` fait 64 caractères | — |
| Secrets | `.env`, `*.db` et `.env.local` ignorés par git | OK | — |

### 3. Parcours patient

| Fonctionnalité | Étape | Résultat | Gravité |
| --- | --- | --- | --- |
| Accueil | Textes, champ, bouton Search, « or », bouton photo | OK | — |
| Accueil | Suggestions pendant la frappe, flèches et Entrée | OK | — |
| Accueil | Exemples « Try » (Glucophage 850, Levothyrox 50 µg, Amlor 5 mg) | OK : ouvrent la bonne fiche | — |
| Accueil | Mention de démonstration | OK : « Pharmacy stock shown in this demo is simulated » (accueil), et un encadré « Simulated availability » sur chaque fiche | — |
| Accueil | Pied de page : lien du ministère (200) et confidentialité (200) | OK | — |
| Accueil | Texte indicatif coupé sur mobile | Corrigé (6) | Mineur |
| Recherche | « GLUCOPHAGE », « glucofage », « levotirox », « metformine » | OK : le bon médicament en tête | — |
| Recherche | Champ vide, 1 caractère | OK : « Type the name of a medicine — At least 2 letters » | — |
| Recherche | `%%%'"<script>` | OK : affiché comme du texte, « No medicine found » | — |
| Recherche | Texte de 150 caractères | Corrigé (3) | Mineur |
| Recherche | Nom inexistant « zzzqqqwww » | OK : « No medicine found for … Try the name written on the box, or take a photo » | — |
| Multilingue | « غلوكوفاج », « dwa ta3 glucophage » | OK : « we understood: GLUCOPHAGE » (Gemini en 0,9 s et 1,5 s) | — |
| Multilingue | « metformin » | OK : METFORMINE (1,6 s) | — |
| Multilingue | « دوا السكر », « medicine for diabetes » | OK : refusées par nos règles, sans appel à Gemini, avec un message clair | — |
| Multilingue | Arabe de droite à gauche | OK : le champ passe en `rtl` (`dir="auto"`), le texte cité est dans `<bdi lang="ar" dir="auto">` | — |
| Photo | Bouton visible avec la clé, masqué sans (selon `/features`) | OK | — |
| Photo | Boîte (image de test), avec le vrai Gemini | OK : « We read: GLUCOPHAGE 850 mg », 3 propositions, « Exact match » (28 s) | — |
| Photo | Ordonnance fictive | OK : « This looks like a prescription », rien n'est cherché | — |
| Photo | Fichier PDF ; fichier de 12 Mo | OK : « This file is not a photo we can read » ; « This photo is too large » | — |
| Fiche | Informations (molécule, dose, forme, labo, origine, type) | OK | — |
| Fiche | Équivalents et message de prudence | OK : GLUCOPHAGE 850 a 13 équivalents, et « Ask your pharmacist or doctor first » | — |
| Fiche | Dose non vérifiée | OK : « Dose not checked automatically » (par ex. Neo-Codion Nourrissons) | — |
| Fiche | Sans équivalent (DIAMICRON 60 mg LM) | OK : « No equivalent registered … Talk to your doctor » | — |
| Fiche | Dose en double dans le titre | Problème restant | Mineur |
| Carte | Géolocalisation acceptée, à Oran | OK : « Pharmacies around your position », distances croissantes (2,1 / 3,0 / 4,7 / 6,0 / 7,7 km) | — |
| Carte | Géolocalisation acceptée, hors d'Oran | Corrigé (2) | Majeur |
| Carte | Géolocalisation refusée | OK : « You did not share your position. We show pharmacies around Oran city centre » | — |
| Carte | Choix d'un quartier (USTO) | OK : la pharmacie la plus proche est à 480 m | — |
| Carte | Rayon (3 km) | OK : « 1 pharmacy has it within 3 km » | — |
| Carte | Couleurs et légende | OK : en stock, en rupture, sans information, votre position | — |
| Carte | Mention « à confirmer » | OK : « To be confirmed by phone » après 7 jours (testé par l'API et par les tests e2e) | — |
| Carte | « Call » et « Directions » | OK : `tel:0550000021`, Google Maps avec destination, OpenStreetMap avec trajet | — |
| Carte | Bouton Retour, puis Avance | Corrigé (1) | Majeur |
| Alerte | Email invalide | OK : bloqué avant l'envoi (« Enter a valid email address ») | — |
| Alerte | Email valide, avec double clic | OK : une seule requête, « Your alert is saved » | — |
| Alerte | Limite de 5 | OK : « You already have 5 alerts with this email » | — |
| Alerte | Envoi de l'email | Problème restant : jamais envoyé | Majeur |
| Confidentialité | Page `/confidentialite` | OK, y compris la photo et les bons de livraison | — |
| Navigation | Retour depuis une fiche vers la recherche | OK : la requête et les résultats sont gardés | — |
| Navigation | Recharger la recherche, la confidentialité, la connexion, l'inscription et une fiche | OK | — |
| Navigation | Lien direct vers une fiche | OK | — |
| Navigation | Page 404 (`/nimportequoi`) ; médicament inconnu | OK : « Page not found » ; « Medicine not found » | — |
| Console | Erreurs JavaScript ou requêtes en échec sur les 17 pages publiques | OK : seulement les 404 voulus | — |
| Mise en page | Défilement horizontal ou texte coupé, à 1280 px et sur Pixel 7 | OK : aucun | — |

### 4. Parcours pharmacien

| Fonctionnalité | Étape | Résultat | Gravité |
| --- | --- | --- | --- |
| Inscription | Les 2 étapes et la carte pour placer la pharmacie | OK (les tests e2e les couvrent, ainsi que les captures) | — |
| Inscription | Email déjà pris (409), mot de passe faible, téléphone invalide (personnel et pharmacie), champ vide | OK : un message clair pour chaque règle | — |
| Inscription | Message final « en attente » | OK : « Your pharmacy is waiting for verification » | — |
| Connexion | Mauvais mot de passe et email inconnu | OK : le même message, « Incorrect email or password. » | — |
| Connexion | Champs vides | OK : « Enter your email and your password. » | — |
| Connexion | Limite de tentatives | OK : 429 au bout de 5 par minute, « Too many attempts… » | — |
| Connexion | Déconnexion, puis `/pharmacien` | OK : retour à la connexion | — |
| Connexion | Token expiré (refusé par l'API) et token qui expire page ouverte | OK : retour propre, « Your session has ended. Please log in again. » | — |
| Connexion | Token falsifié en admin | OK : 401 | — |
| En attente | Connexion possible | OK : « Your pharmacy is being verified » | — |
| En attente | Déclarer un stock, scanner un bon | OK : 403 « Votre pharmacie est en cours de vérification », et le scan affiche « Available once approved » | — |
| Tableau de bord | « In stock » et « Out of stock » sur 3 médicaments | OK : retour visuel en 73 à 87 ms, et « Saved: … » | — |
| Tableau de bord | Double clic | OK : une seule requête | — |
| Tableau de bord | Ordre « à actualiser d'abord » | OK : jamais mis à jour d'abord, puis du plus ancien au plus récent. Un médicament mis à jour passe en fin de liste au rechargement | — |
| Tableau de bord | Ajouter un médicament suivi, puis l'arrêter (avec confirmation) | OK | — |
| Modification | Téléphone invalide ; téléphone et horaires valides | OK : message d'erreur ; « Changes saved » | — |
| Modification | Changement d'adresse | OK : la pharmacie repasse « Being verified » | — |
| Modification | Comptes de démo partagés | Problème restant | Majeur |
| Patient | Un stock déclaré apparaît sur la fiche et la carte | OK : par l'API (pharmacie nouvellement approuvée) et dans le navigateur | — |
| Scan de bon | Bon de démonstration, avec le vrai Gemini | OK : 20 lignes lues (15 reconnues, 1 à vérifier, 2 non livrées, 1 hors liste), en 11 s | — |
| Scan de bon | Correction d'une ligne (TAHOR, choix du dosage) | OK : « Corrected by you » | — |
| Scan de bon | Reliquats | OK : « Not delivered (2) », jamais mis en stock | — |
| Scan de bon | Confirmation par double clic | OK : une seule confirmation, « Stock updated » | — |
| Historique | Photo gardée, puis supprimée | OK | — |
| Historique | Aucun prix affiché | OK | — |
| Historique | « When did I receive… ? » | OK | — |
| Historique | Export CSV | OK : séparateur « ; », BOM, 9 colonnes sans prix | — |
| Historique | Annulation sous 24 h | OK : « Note cancelled » | — |
| Historique | Suppression du bon | OK | — |
| Historique | Sans historique | OK : la case photo est désactivée, « 15 medicines updated », rien n'est gardé | — |
| Sécurité | Pharmacie 2 sur un bon de la pharmacie 1 (lecture, photo, modification, suppression, annulation) | OK : 404 « Bon introuvable » | — |
| Sécurité | `pharmacie_id` ou `id` ajouté dans la requête | OK : 422, champ refusé | — |
| Sécurité | Pharmacien sur `/admin` et sur l'API admin | OK : page « This page is for administrators only », et 403 | — |
| Sécurité | Admin sur un bon | OK : 403 | — |

### 5. Parcours admin

| Fonctionnalité | Étape | Résultat | Gravité |
| --- | --- | --- | --- |
| Connexion | Admin, puis redirection vers `/admin` | OK | — |
| Connexion | Titre « Pharmacist login » pour l'admin | Problème restant | Mineur |
| Liste | En attente, approuvées, refusées ou suspendues | OK | — |
| Validation | Valider | OK : la pharmacie apparaît dans `/pharmacies` et sur la fiche | — |
| Validation | Refuser sans motif | OK : 422, motif obligatoire | — |
| Validation | Suspendre | OK : la pharmacie disparaît de `/pharmacies` et de la carte | — |
| Accès | Sans token ; avec un token de pharmacien | OK : 401 ; 403 | — |

### 6. Robustesse

| Fonctionnalité | Étape | Résultat | Gravité |
| --- | --- | --- | --- |
| API arrêtée | Accueil, recherche, suggestions, fiche, tableau de bord, historique, connexion | OK : « We can't reach MedRadar right now. Check your internet connection and try again. », jamais de page blanche | — |
| API arrêtée | Page du scanner | Corrigé (4) | Mineur |
| Sans `LLM_API_KEY` | `/features` | OK : tout est à `false` | — |
| Sans `LLM_API_KEY` | Accueil | OK : le bouton photo est masqué | — |
| Sans `LLM_API_KEY` | Scanner | OK : « Reading delivery notes is not available » | — |
| Sans `LLM_API_KEY` | `/medicines/recognize` | OK : 503 avec un message clair | — |
| Sans `LLM_API_KEY` | Recherche arabe et darija | OK : par les règles, en 130 ms | — |
| Sans `LLM_API_KEY` | Déclaration de stock et historique | OK | — |
| API lente (+3 s) | Indicateurs de chargement | OK : « Loading the medicine… », « Searching… », « Broader search… », « Saving… », « Logging in… », « Loading your pharmacy… », « Reading the note… » | — |
| API lente (+3 s) | Boutons pendant l'envoi | OK : désactivés | — |
| Double clic | Alerte, déclaration, confirmation du bon | OK : aucune action en double | — |
| Quota Gemini | Photo et scan | Problème restant | Majeur |

### 7. Accessibilité et performance

| Fonctionnalité | Étape | Résultat | Gravité |
| --- | --- | --- | --- |
| axe-core | Accueil, 3 recherches, fiche, fiche sans équivalent, 404, confidentialité, connexion, inscription (et ses erreurs), tableau de bord, modification, scanner, historique, détail d'un bon, admin, sur ordinateur et mobile | OK : 0 violation | — |
| Clavier | Accueil | OK : lien d'évitement, champ, Search, photo, exemples, pied de page ; focus toujours visible | — |
| Clavier | Fiche | OK : choix au clavier (flèches et Entrée), ancres, « Use my position », quartier, distance, « Call », « Directions », équivalents, alerte ; focus visible | — |
| Clavier | Tableau de bord | OK : menu, modification, déconnexion, scan, ajout, « In stock », « Out of stock » et Entrée | — |
| Lighthouse | Accueil | OK : 79 à 85 en performance, 100 ailleurs | — |
| Lighthouse | Fiche | Corrigé (5) : CLS 0,34 → 0, performance 47 → 64. TBT et taille des marqueurs : problème restant | Mineur |
| Arabe | Affichage de droite à gauche | OK | — |

### 8. Exactitude des données

| Fonctionnalité | Étape | Résultat | Gravité |
| --- | --- | --- | --- |
| Référence | GLUCOPHAGE 850 | OK : 13 équivalents | — |
| Référence | DIAMICRON 60 mg LM | OK : 0 (et 4 pour DIAMICRON 30 mg LM) | — |
| Référence | AMLOR 10 mg | OK : 8 équivalents, tous « AMLODIPINE SOUS FORME BESYLATE » (AMLOCARDINE, DIMLOR, LOTENSE…) | — |
| Exclusion | 1 039 médicaments hospitaliers ou retirés | OK : 400 identifiants testés, tous en 404 ; 200 noms cherchés, jamais dans les résultats | — |
| Version | Nomenclature | OK : « August 2026 » dans le pied de page et dans le README | — |
| Équivalents | `check_equivalents.py` sur les 10 marques du document | OK : aucun changement par rapport à `docs/verification_equivalents.md` | — |

### 9. Simulation de juge

| Étape | Résultat | Gravité |
| --- | --- | --- |
| Arriver par le lien, comprendre le site | OK : le titre dit le problème, « Try: Glucophage 850 · diabetes » propose un exemple concret, et la démo est annoncée comme simulée | — |
| Chercher un médicament en rupture | OK : on tape le nom et on choisit une suggestion, ou on clique sur l'exemple | — |
| Voir les équivalents et la carte | OK : liens d'ancre « Pharmacies near you » et « Equivalents (13) », carte avec légende | — |
| Juge hors d'Oran qui partage sa position | Corrigé (2) : il voyait une carte vide | Majeur |
| Trouver l'espace pharmacien | OK : lien « Pharmacist area » en haut de chaque page | — |
| Se connecter et changer un stock | OK : boutons « In stock » et « Out of stock » larges, et « Saved: … » | — |
| Durée | OK : 4 écrans, 4,5 s à vitesse robot, environ 1 à 2 minutes pour un humain (sur mobile, il faut défiler sous le bloc « Scan a delivery note ») | — |
| Juge suivant, si un juge a modifié la pharmacie de démo | Problème restant | Majeur |

## Méthode

- **Installation.** Clone neuf depuis GitHub dans un dossier temporaire, avec un environnement Python neuf, en suivant uniquement le README.
- **Environnement d'audit.**
  - L'API du dépôt de travail tournait sur une base séparée, créée par les scripts du README : votre base de développement n'a pas été touchée.
  - La vraie clé Gemini était utilisée, sauf pour le test « sans clé ».
  - Le frontend tournait en version de production (`npm run build` puis `next start`).
- **Tests du navigateur.** Scripts Playwright temporaires, sur ordinateur (Chrome) et sur mobile (Pixel 7). Ils relevaient les erreurs de console, les requêtes en échec, le défilement horizontal et le texte coupé. Ils n'ont pas été commités.
- **Appels réels à Gemini** pendant l'audit : 2 photos, 2 bons et quelques recherches.

## Captures d'écran

Elles se trouvent dans [docs/qa_screenshots/](qa_screenshots/) et ont été prises sur la version corrigée.
- Pour chaque page principale : `desktop-*.png` et `mobile-*.png` (accueil, recherches, fiche, fiche sans équivalent, 404, confidentialité, connexion, inscription, tableau de bord, modification de la pharmacie, scanner, historique, détail d'un bon, admin).
- Les étapes de la simulation de juge : `judge-*.png`.
- Les pages très longues sont coupées à 9 000 pixels.

| Accueil (mobile) | Fiche médicament (mobile) |
| --- | --- |
| ![Accueil sur mobile](qa_screenshots/mobile-home.png) | ![Fiche GLUCOPHAGE 850 sur mobile](qa_screenshots/mobile-medicine.png) |
