# Life Intelligence System

> A locally-run, privacy-first personal intelligence platform powered by GraphRAG.
> **Your data never leaves your machine.**

## Vision

The Life Intelligence System is an **umbrella architecture** — a single knowledge graph that unifies every major life domain (health, finances, legal, career, relationships) into one queryable, interconnected system. Each domain is a self-contained vertical that plugs into a shared Neo4j graph, shared vector store, shared API, and a single Person node at the center.

The magic is **cross-domain intelligence**: asking questions that no single-domain app could answer. Your diabetes diagnosis, your health insurance plan, your employment contract's FSA benefit, and your genetic risk profile all live in the same graph — and the system automatically discovers the connections between them.

**Right now:** The healthcare domain is fully built — medical records, fitness data, mental health, and genetic reports all ingested and cross-linked.

**Next:** Finances, legal contracts, career, and relationships — same pattern, same backbone, no changes to the core.

## Current Domains

| Domain | Status | Verticals | Node Types |
|--------|--------|-----------|------------|
| **Healthcare** | ✅ Active | medical, fitness, mental_health, genetics | 22 types |
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
    │   Claude claude-sonnet-4-6 for answers               │
    └────────────────────────────────────────────┘
```

## Setup & Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- An Anthropic API key ([get one here](https://console.anthropic.com))
- Tesseract OCR (for image/scan ingestion): `brew install tesseract`

### Quick Start

```bash
# 1. Clone / copy this folder
cd life-intelligence/

# 2. Configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and NEO4J_PASSWORD

# 3. Start services
docker-compose up -d
# Wait ~30 seconds for Neo4j to initialize

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Seed 30 years of synthetic healthcare data
python scripts/seed_data/seed_healthcare.py

# 6. Start the API
uvicorn src.api.main:app --host 127.0.0.1 --port 8000

# 7. Verify
curl http://127.0.0.1:8000/domains
curl http://127.0.0.1:8000/me
```

### Verify Services
- **Neo4j Browser**: http://localhost:7474 (user: neo4j, password: from .env)
- **API docs**: http://127.0.0.1:8000/docs
- **ChromaDB**: http://localhost:8001/api/v1/heartbeat

## Usage

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

### Query Your Data

```bash
# Ask any question
python scripts/query.py \
  --question "What medications am I on and do any interact?"

# Cross-domain query (once multiple domains are active)
python scripts/query.py \
  --question "Does my insurance cover my diabetes medication?" \
  --domains "healthcare,finances"

# Filter by date range
python scripts/query.py \
  --question "What happened to my health in 2020?" \
  --date-from 2020-01-01 \
  --date-to 2020-12-31
```

### API Examples

```bash
# Get current medications
curl http://127.0.0.1:8000/healthcare/medications/current

# Get HbA1c trend
curl "http://127.0.0.1:8000/healthcare/labs/trends?test=HbA1c"

# Full safety check (drug interactions, supplement conflicts)
curl http://127.0.0.1:8000/safety/full

# Cross-vertical insights (supplement-drug interactions, etc.)
curl http://127.0.0.1:8000/healthcare/insights/cross-vertical

# Genetic risks
curl http://127.0.0.1:8000/healthcare/genetics/risks

# Ask anything via API
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my active conditions and current medications?", "domains": ["healthcare"]}'
```

## Adding a New Domain (7 Steps)

The entire process of adding a new domain — no changes to core, no migrations:

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

## Adding a New Vertical to an Existing Domain (4 Steps)

```
Step 1: Create src/domains/{domain}/verticals/{vertical}/
Step 2: Implement extractor.py (Claude-based entity extraction)
Step 3: Implement graph_builder.py (Neo4j node/relationship creation)
Step 4: Implement loaders.py (vertical class extending BaseVertical)
```

## Running Tests

```bash
# After seeding data:
pytest tests/test_healthcare_queries.py -v

# Run all tests (cross-domain tests will be skipped)
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
| **No cloud sync** | Everything runs locally; Claude API receives only your question + context |

## Example Cross-Domain Queries (Planned)

Once finances and legal domains are implemented:

```
"Given my diabetes diagnosis and my health insurance claims,
 am I maximizing my FSA/HSA benefits?"

"Does my life insurance policy account for my BRCA2 screening needs?"

"What medical expenses can I claim given my employment contract benefits?"

"Is my Sertraline covered by my current insurance plan,
 and does my CYP2C19 status affect the dosage I should be on?"

"What are all my upcoming contract obligations that could
 affect my health coverage?"
```

## Data Sources Accepted

| Domain | Vertical | Accepted Formats |
|--------|----------|-----------------|
| Healthcare | Medical | PDF, DOCX, image (OCR), XML (HL7/FHIR) |
| Healthcare | Fitness | CSV (Apple Health, Garmin, Fitbit), JSON, PDF |
| Healthcare | Mental Health | PDF, DOCX, TXT (journal exports) |
| Healthcare | Genetics | PDF (23andMe, AncestryDNA reports), JSON |
| Finances | Banking | CSV, PDF (bank statements) |
| Finances | Insurance | PDF (policy documents) |
| Legal | Employment | PDF, DOCX (contracts, offer letters) |
| Career | All | PDF (resume), JSON (LinkedIn export) |

## Project Structure

```
life-intelligence/
├── docker-compose.yml          # Neo4j + ChromaDB services
├── requirements.txt
├── .env.example
├── data/uploads/               # Drop your documents here
│   ├── healthcare/{medical,fitness,mental_health,genetics}/
│   ├── finances/
│   ├── legal-contracts/
│   ├── career/
│   └── relationships/
├── src/
│   ├── core/                   # Shared backbone — never domain-specific
│   ├── domains/                # One folder per life domain
│   │   ├── base_domain.py
│   │   ├── healthcare/         # ✅ Fully implemented
│   │   ├── finances/           # 🔜 Planned — see PLANNED.md
│   │   ├── legal-contracts/    # 🔜 Planned
│   │   ├── career/             # 🔜 Planned
│   │   └── relationships/      # 🔜 Planned
│   ├── retrieval/              # Hybrid graph + vector retrieval
│   ├── generation/             # Claude-powered answer generation
│   └── api/                    # FastAPI — all endpoints
├── scripts/
│   ├── ingest.py               # CLI: drop any file into any domain
│   ├── query.py                # CLI: ask anything
│   ├── backup.py               # AES-256 encrypted backup
│   └── seed_data/
│       └── seed_healthcare.py  # 30-year synthetic health history
└── tests/
    ├── test_healthcare_queries.py    # 15 healthcare tests
    └── test_cross_domain_queries.py  # 5 cross-domain stubs
```
