# Intelligent Helpdesk — API & Moteur ML

Backend et moteur d'intelligence artificielle de la plateforme **Intelligent
Helpdesk** : classification, priorisation et routage automatiques des tickets
de support client.

**PFA 2025–2026 · ALEXSYS SOLUTIONS**
Filière Ingénierie — Spécialité Intelligence Artificielle & Data

L'interface Next.js se trouve dans un dépôt distinct : [`intelligent-helpdesk-web`](https://github.com/fakhreddine-jadib/intelligent-helpdesk-web).

---

## Ce que fait le système

Un ticket soumis par un client traverse un pipeline automatisé :

1. **Prétraitement** — nettoyage du texte, vectorisation TF-IDF (20 000 dimensions)
2. **Inférence** — deux modèles parallèles prédisent le département et l'urgence
3. **Routage** — des règles métier appliquent un seuil de confiance et une
   escalade sur vocabulaire critique
4. **Persistance** — le ticket enrichi est stocké dans MongoDB
5. **Diffusion** — les tableaux de bord agents sont mis à jour en temps réel (SSE)

Latence mesurée de bout en bout : **7,55 ms**.

## Performances des modèles

| Indicateur | Valeur | Référence |
|---|---|---|
| Exactitude du routage | 55,6 % | 28,6 % (classe majoritaire) |
| Macro-F1 du routage | 0,544 | — |
| Exactitude de la priorisation | 60,2 % | 53,1 % (table département → priorité) |
| Macro-F1 de la priorisation | 0,547 | 0,433 |
| Rappel sur tickets critiques | 64,8 % | — |
| Critiques classés en priorité faible | 3,1 % | — |

Ces chiffres doivent être lus à la lumière de la qualité du corpus : une
annotation manuelle de 300 tickets donne un accord inter-annotateurs de
**κ = 0,174**, dont 46,7 % des désaccords examinés correspondent à des erreurs
manifestes du corpus. Voir `notebooks/09_gold_analysis.ipynb`.

---

## Démarrage rapide (Docker)

Prérequis : Docker Desktop.

Depuis le répertoire parent contenant les deux dépôts :

```bash
cp .env.example .env
# renseigner SECRET_KEY (générer : python -c "import secrets; print(secrets.token_hex(32))")

docker compose up --build
```

| Service | URL |
|---|---|
| API | http://localhost:5000/api |
| Interface | http://localhost:3000 |
| MongoDB | localhost:27017 |
| Redis | localhost:6379 |

Vérification : `curl http://localhost:5000/api/ready` doit retourner
`"models_loaded": true`.

## Installation manuelle

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt

cp .env.example .env            # puis renseigner SECRET_KEY
python run.py
```

Nécessite Python 3.12, MongoDB en écoute sur le port 27017, et Redis
(facultatif — la limitation de débit bascule en mémoire sans lui).

### Reproduire l'entraînement

Le jeu de données n'est pas versionné. Le télécharger depuis
[Kaggle](https://www.kaggle.com/datasets/tobiasbueck/multilingual-customer-support-tickets)
et placer `dataset-tickets-multi-lang-4-20k.csv` dans `data/raw/`, puis exécuter
les carnets dans l'ordre numérique.

---

## Structure du dépôt

| Répertoire | Contenu |
|---|---|
| `src/api/` | Application Flask : routes, sécurité, validation |
| `src/models/` | Schémas des documents MongoDB |
| `src/services/` | Journalisation d'activité, diffusion d'événements |
| `src/preprocessing.py` | Nettoyage du texte — partagé entraînement / inférence |
| `src/inference.py` | Moteur d'inférence temps réel |
| `src/routing.py` | Règles métier de routage |
| `models/` | Artefacts sérialisés (`.joblib`) — **versionnés** |
| `notebooks/` | Analyse exploratoire, entraînement, évaluation |
| `tests/` | Suite pytest |

Les trois artefacts de `models/` sont **solidaires** : ils ont été produits sur
la même partition et le même vocabulaire. Réentraîner le vectoriseur invalide
les deux classifieurs.

---

## API

| Méthode | Chemin | Accès | Fonction |
|---|---|---|---|
| GET | `/api/health` | Public | Sonde de vie |
| GET | `/api/ready` | Public | Sonde de disponibilité (modèles chargés) |
| POST | `/api/predict` | Public | Classification sans persistance |
| POST | `/api/auth/register` | Public | Création de compte |
| POST | `/api/auth/login` | Public | Authentification (JWT) |
| GET | `/api/auth/me` | Authentifié | Profil courant |
| POST | `/api/tickets` | Authentifié | Soumission d'un ticket |
| GET | `/api/tickets` | Authentifié | Liste filtrée, triée par urgence |
| GET | `/api/tickets/<id>` | Authentifié | Consultation unitaire |
| PATCH | `/api/tickets/<id>` | Agent, Admin | Mise à jour |
| DELETE | `/api/tickets/<id>` | Admin | Suppression |
| GET | `/api/events` | Agent, Admin | Flux temps réel (SSE) |
| GET | `/api/logs` | Admin | Journal d'activité |
| GET | `/api/stats` | Agent, Admin | Agrégats tableau de bord |
| GET | `/api/stats/model` | Admin | Suivi du modèle en production |

### Exemple

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"subject":"Server outage","body":"Our production servers have been completely down for two hours."}'
```

```json
{
  "queue": "Technical Support",
  "queue_confidence": 0.237,
  "priority": "high",
  "priority_confidence": 0.6796,
  "assigned_queue": "Triage",
  "needs_triage": true,
  "escalated": false,
  "inference_time_ms": 7.55
}
```

---

## Tests

```bash
pytest -v
pytest --cov=src --cov-report=term-missing
```

**44 tests, 81 % de couverture.** Les modules critiques
(`routing.py`, `preprocessing.py`, `security.py`, `inference.py`) sont
couverts à 100 %.

## Sécurité

- Mots de passe hachés par bcrypt (sel individuel)
- Jetons JWT signés HS256, expiration 12 h
- Contrôle d'accès par rôle : `client`, `agent`, `admin`
- Isolation des données clients au niveau de la requête MongoDB
- Validation et bornage de toutes les entrées
- Limitation de débit sur l'authentification (10 tentatives/min)
- Secrets externalisés en variables d'environnement
- CORS restreint aux origines déclarées

### Limites connues

- L'inscription autorise la création d'un compte administrateur en
  libre-service ; à restreindre avant tout déploiement réel.
- Le jeton JWT est stocké côté client dans `localStorage`, vulnérable au XSS.
  Alternative : cookie `httpOnly`.
- Le courtier d'événements SSE est en mémoire : il ne survit pas à une
  montée en charge horizontale (nécessiterait Redis pub/sub).

---

## Pile technologique

Python 3.12 · Flask · Gunicorn · MongoDB · Redis · scikit-learn · XGBoost ·
pandas · PyJWT · bcrypt · pytest