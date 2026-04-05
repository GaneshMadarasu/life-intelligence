# Life Intelligence System

> A locally-run, privacy-first personal intelligence platform powered by GraphRAG.
> **Your data never leaves your machine.**

## Vision

The Life Intelligence System is an **umbrella architecture** — a single knowledge graph that unifies every major life domain (health, finances, legal, career, relationships) into one queryable, interconnected system. Each domain is a self-contained vertical that plugs into a shared Neo4j graph, shared vector store, shared API, and a single Person node at the center.

The magic is **cross-domain intelligence**: asking questions that no single-domain app could answer. Your diabetes diagnosis, your health insurance plan, your employment contract's FSA benefit, and your genetic risk profile all live in the same graph — and the system automatically discovers the connections between them.

**Right now:** The healthcare domain is fully built — medical records, fitness data (including live Whoop biometrics), mental health, and genetic reports all ingested and cross-linked. A dark-themed web UI lets you ask natural-language questions with full conversation memory.

**Next:** Finances, legal contracts, career, and relationships — same pattern, same backbone, no changes to the core.

## Current Domains

| Domain | Status | Verticals | Node Types |
|--------|--------|-----------|------------|
| **Healthcare** | ✅ Active | medical, fitness, mental_health, genetics | 24 types |
| **Finances** | 🔜 Planned | banking, investments, insurance, taxes | — |
| **Legal Contracts** | 🔜 Planned | employment, property, insurance-policies | — |
| **Career** | 🔜 Planned | employment-history, skills, education | — |
| **Relationships** | 🔜 Planned | family, professional | — |

## Architecture

```
                    ┌─────────────────────────────────┐
                    │    Life Intelligence System      │
                    │      (life-intelligence/)        │
                    └──────────────┬──────────────────┘
                                   │
              ┌────────────────────┼─────────────────────┐
              │                    │                     │
    ┌─────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
    │   src/core/      │  │  Neo4j Graph DB │  │  ChromaDB       │
    │  (shared backbone│  │  (shared schema)│  │  (vector store) │
    │   never changes) │  │  port 7474/7687 │  │  port 8001      │
    └─────────┬────────┘  └────────┬────────┘  └────────┬────────┘
              │                    │                     │
    ┌─────────▼────────────────────▼─────────────────────▼─────────┐
    │                       src/domains/                            │
    ├────────────┬────────────────┬────────────────┬───────────────┤
    │ healthcare │   finances     │legal-contracts │    career     │
    │ ✅ Active  │  🔜 Planned   │  🔜 Planned   │  🔜 Planned  │
    │            │                │                │               │
    │ ├─ medical │ ├─ banking     │ ├─ employment  │ ├─ emp-hist   │
    │ ├─ fitness │ ├─ investments │ ├─ property    │ ├─ skills     │
    │ ├─ mental  │ ├─ insurance   │ └─ ins-policy  │ └─ education  │
    │ └─ genetics│ └─ taxes       │                │               │
    └─────┬──────┴────────────────┴────────────────┴───────────────┘
          │
    ┌─────▼──────────────────────────────────────┐
    │     src/integrations/whoop/                │
    │  OAuth2 client · sync engine · mapper      │
    │  Pulls live biometrics from Whoop API      │
    │  (recovery, HRV, sleep, strain, workouts)  │
    └─────┬──────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────┐
    │          Cross-Domain Linker               │
    │  Finds connections across ALL domains:     │
    │  InsurancePlan ↔ Condition                 │
    │  Contract ↔ Benefit                        │
    │  Expense(medical) ↔ Procedure              │
    │  Stressor ↔ PerformanceReview             │
    └─────┬──────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────┐
    │   FastAPI  (127.0.0.1:8000 only)           │
    │   Hybrid retrieval: graph + vector         │
    │   Multi-turn conversation context          │
    │   Claude claude-sonnet-4-6 for answers     │
    │   Web UI served at http://127.0.0.1:8000   │
    └────────────────────────────────────────────┘
```

## Setup & Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- An Anthropic API key ([get one here](https://console.anthropic.com))
- Tesseract OCR (for image/scan ingestion): `brew install tesseract`
- A Whoop developer account (optional, for live biometrics): [developer.whoop.com](https://developer.whoop.com)

### Quick Start

```bash
# 1. Clone / copy this folder
cd life-intelligence/

# 2. Configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY, NEO4J_PASSWORD, and optionally WHOOP_CLIENT_ID / WHOOP_CLIENT_SECRET

# 3. Start services
docker-compose up -d
# Wait ~30 seconds for Neo4j to initialize

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Seed synthetic healthcare data
python scripts/seed_data/seed_ganesh_healthcare.py

# 6. Start the API + Web UI
uvicorn src.api.main:app --host 127.0.0.1 --port 8000

# 7. Open the web UI
open http://127.0.0.1:8000
```

### Verify Services
- **Web UI**: http://127.0.0.1:8000
- **API docs**: http://127.0.0.1:8000/docs
- **Neo4j Browser**: http://localhost:7474 (user: neo4j, password: from .env)
- **ChromaDB**: http://localhost:8001/api/v1/heartbeat

## Whoop Integration (Live Biometrics)

Connect your Whoop device to pull real-time recovery, HRV, sleep, strain, and workout data directly into the knowledge graph.

### Setup

1. Create a Whoop developer app at [developer.whoop.com](https://developer.whoop.com)
   - Set redirect URI to: `http://localhost:8080/callback`
   - Enable scopes: `offline read:recovery read:sleep read:workout read:profile read:cycles`
2. Add credentials to `.env`:
   ```
   WHOOP_CLIENT_ID=your_client_id
   WHOOP_CLIENT_SECRET=your_client_secret
   ```

### Authenticate & Sync

```bash
# First-time OAuth2 login (opens browser)
python scripts/whoop_sync.py auth

# If automatic callback fails, copy the redirect URL from your browser:
python scripts/whoop_sync.py auth --code 'http://localhost:8080/callback?code=...'

# Sync last 30 days (default)
python scripts/whoop_sync.py sync

# Sync last 90 days
python scripts/whoop_sync.py sync --days 90

# Check connection status
python scripts/whoop_sync.py status
```

### What Gets Synced

| Data Type | Node Type | Key Fields |
|-----------|-----------|------------|
| Daily recovery | `WhoopRecovery` | recovery_score, hrv_rmssd, resting_hr, spo2_pct |
| Daily cycle | `WhoopCycle` | strain, calories, avg_heart_rate, max_heart_rate |
| Sleep sessions | `SleepRecord` (source=whoop) | duration_hours, deep/REM/light, sleep_performance_pct |
| Workouts | `Workout` (source=whoop) | type, strain_score, duration_mins, HR zones 1–5 |

### Whoop API Endpoints

```bash
# Connection status + profile
curl http://127.0.0.1:8000/integrations/whoop/status

# Trigger sync from the API
curl -X POST http://127.0.0.1:8000/integrations/whoop/sync \
  -H "Content-Type: application/json" \
  -d '{"days": 30}'

# Last 30 days of recovery + HRV
curl "http://127.0.0.1:8000/healthcare/fitness/recovery?days=30"

# Daily strain + workouts
curl "http://127.0.0.1:8000/healthcare/fitness/strain?days=30"

# Sleep performance breakdown
curl "http://127.0.0.1:8000/healthcare/fitness/sleep?days=30"
```

## Web UI

A dark-themed chat interface is served directly by the API — no separate server needed.

```
http://127.0.0.1:8000
```

**Features:**
- **Whoop Live panel** — sidebar shows today's recovery score (color-coded green/yellow/red), HRV, RHR, day strain, sleep performance, and sleep hours
- **Multi-turn conversation** — the chat window remembers the last 5 exchanges; follow-up questions reference prior answers naturally
- **Markdown-rendered answers** — AI responses render with headings, bullets, and code blocks
- **Safety warnings** — drug interactions and genetic risks surface inline, color-coded by severity
- **Quick questions** — one-click buttons for common health queries (Whoop recovery, HRV trends, sleep analysis, medication interactions, genetic risks)
- **Domain selector** — filter queries to specific domains (healthcare, all)
- **Clear chat** — resets both the visible messages and the conversation history

## Usage

### Ask Questions

**Via web UI** (recommended): open `http://127.0.0.1:8000` and type in the chat box.

**Via CLI:**
```bash
python scripts/query.py \
  --question "What is my latest HRV and recovery score, and what does it mean?"

# Cross-domain (once multiple domains are active)
python scripts/query.py \
  --question "Does my insurance cover my diabetes medication?" \
  --domains "healthcare,finances"
```

**Via API:**
```bash
# Single question
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my active conditions?", "domains": ["healthcare"]}'

# With conversation history (multi-turn)
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "And how does that compare to last week?",
    "domains": ["healthcare"],
    "conversation_history": [
      {"role": "user", "content": "What is my latest HRV?"},
      {"role": "assistant", "content": "Your latest HRV is 186ms..."}
    ]
  }'
```

### Ingest Your Documents

```bash
# Ingest a single medical PDF
python scripts/ingest.py \
  --file data/uploads/healthcare/medical/lab_results_2024.pdf \
  --domain healthcare \
  --vertical medical

# Ingest an entire folder (auto-detects vertical from subfolder name)
python scripts/ingest.py \
  --folder data/uploads/healthcare/ \
  --domain healthcare
```

### Other API Endpoints

```bash
# Person summary
curl http://127.0.0.1:8000/me

# Current medications
curl http://127.0.0.1:8000/healthcare/medications/current

# Active conditions
curl http://127.0.0.1:8000/healthcare/conditions/active

# HbA1c trend
curl "http://127.0.0.1:8000/healthcare/labs/trends?test=HbA1c"

# Full safety check (drug interactions, supplement conflicts)
curl http://127.0.0.1:8000/safety/full

# Genetic risks
curl http://127.0.0.1:8000/healthcare/genetics/risks
```

## Adding a New Domain (7 Steps)

```
Step 1: Create src/domains/{domain-name}/
Step 2: Create domain.py extending BaseDomain
Step 3: Create verticals/ subfolder with vertical modules
         Each vertical: extractor.py, graph_builder.py, queries.py, loaders.py
Step 4: Create data/uploads/{domain-name}/ folder
Step 5: Add endpoints to src/api/main.py
Step 6: Register in src/domains/__init__.py
Step 7: Add cross-domain rules to src/core/cross_domain_linker.py
```

That's it. No changes to `src/core/`, no schema migrations, no vector store changes.

## Running Tests

```bash
pytest tests/test_healthcare_queries.py -v
pytest tests/ -v
```

## Backup & Restore

```bash
# Generate encryption key (one-time setup)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add the key to BACKUP_ENCRYPTION_KEY in .env

# Create encrypted backup
python scripts/backup.py backup

# Restore from backup
python scripts/backup.py restore data/backups/life-intel-backup-20240101_120000.enc
```

## Privacy & Security

| Feature | Implementation |
|---------|---------------|
| **Local-only** | All data in Neo4j + ChromaDB running on localhost |
| **API binding** | FastAPI bound to `127.0.0.1` — not accessible from network |
| **Git exclusion** | `.env` and `data/` are in `.gitignore` — never committed |
| **Encrypted backup** | AES-256 (Fernet) encryption for all backups |
| **No telemetry** | ChromaDB runs with `ANONYMIZED_TELEMETRY=FALSE` |
| **No cloud sync** | Everything runs locally; Claude API receives only your question + context excerpts |
| **Whoop tokens** | OAuth2 tokens saved to `.whoop_tokens.json` (chmod 600), gitignored |

## Neo4j Node Types

| Domain | Node Types |
|--------|-----------|
| Core | `Person`, `Document`, `TimePoint`, `Provider`, `Organisation` |
| Medical | `Condition`, `Medication`, `Supplement`, `LabResult`, `Vital`, `Allergy`, `Procedure`, `Vaccine`, `Hospitalization` |
| Fitness | `Workout`, `Meal`, `BodyMetric`, `SleepRecord`, `WhoopRecovery`, `WhoopCycle` |
| Mental Health | `MoodEntry`, `TherapySession`, `Stressor`, `JournalEntry`, `MeditationSession`, `MentalCondition` |
| Genetics | `Gene`, `GeneticVariant`, `GeneticRisk`, `Pharmacogene`, `GeneticReport`, `AncestrySegment` |

## Example Cross-Domain Queries (Planned)

Once finances and legal domains are implemented:

```
"Given my diabetes diagnosis and my health insurance claims,
 am I maximizing my FSA/HSA benefits?"

"Does my life insurance policy account for my BRCA2 screening needs?"

"What medical expenses can I claim given my employment contract benefits?"

"Is my Sertraline covered by my current insurance plan,
 and does my CYP2C19 status affect the dosage I should be on?"
```

## Project Structure

```
life-intelligence/
├── docker-compose.yml          # Neo4j + ChromaDB services
├── requirements.txt
├── .env.example
├── system-design.html          # Visual architecture document
├── data/uploads/               # Drop your documents here (gitignored)
│   └── healthcare/{medical,fitness,mental_health,genetics}/
├── src/
│   ├── core/                   # Shared backbone — never domain-specific
│   │   ├── neo4j_client.py     # Graph DB connection + schema init
│   │   ├── person.py           # Single Person node manager
│   │   ├── vector_store.py     # ChromaDB interface
│   │   ├── timeline.py         # Universal event timeline
│   │   ├── safety_checker.py   # Drug interactions, supplement conflicts
│   │   └── cross_domain_linker.py
│   ├── domains/                # One folder per life domain
│   │   ├── base_domain.py
│   │   ├── healthcare/         # ✅ Fully implemented
│   │   ├── finances/           # 🔜 Planned
│   │   ├── legal-contracts/    # 🔜 Planned
│   │   ├── career/             # 🔜 Planned
│   │   └── relationships/      # 🔜 Planned
│   ├── integrations/
│   │   └── whoop/
│   │       ├── client.py       # OAuth2 client + auto token refresh
│   │       ├── mapper.py       # Whoop API → graph schema
│   │       └── sync.py         # Orchestrates fetch + ingest
│   ├── retrieval/              # Hybrid graph + vector retrieval
│   │   ├── graph_retriever.py  # Cypher search + Whoop biometric injection
│   │   ├── vector_retriever.py # ChromaDB semantic search
│   │   └── hybrid_retriever.py # Score fusion + context assembly
│   ├── generation/
│   │   └── answer_generator.py # Claude-powered QA with conversation history
│   ├── api/
│   │   └── main.py             # FastAPI — all endpoints + UI serving
│   └── ui/
│       └── index.html          # Dark-themed chat UI (Tailwind + marked.js)
├── scripts/
│   ├── ingest.py               # CLI: drop any file into any domain
│   ├── query.py                # CLI: ask anything
│   ├── whoop_sync.py           # CLI: Whoop auth / sync / status
│   ├── backup.py               # AES-256 encrypted backup
│   └── seed_data/
│       └── seed_ganesh_healthcare.py  # Synthetic health history for Ganesh
└── tests/
    ├── test_healthcare_queries.py
    └── test_cross_domain_queries.py
```
