# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repo is a **diploma project** ("Карпатська садиба" — a real 3-cottage guesthouse in the
Ukrainian Carpathians). The target is an **AI / LLM Engineer** role, so decisions are made by
research and measured ablation, not by picking a default. Project deadline: **2027-05-21**.

**As of this writing there is no code yet** — only planning docs under `docs/`. The first
implementation sprint (`docs/sprint-praktyka-08-19-09.md`) builds an end-to-end RAG + booking
vertical slice. Treat the docs as the spec; when you scaffold, follow the structure and stack
they define rather than inventing your own.

Frontend is a **separate repo** (Astro): https://github.com/SpaceNamee/KarpatskaSadyba
This repo is **backend + AI only**.

## The `docs/` folder is the source of truth (and is gitignored)

`docs/` is in `.gitignore` on purpose but is the single source of truth. Read it before doing
anything non-trivial. It is written in Ukrainian.

- `docs/about.md` — verified facts about the property: 3 cottages (260/260/120 m², max
  16/18/15 guests, base 10/14/14), real prices, rules, nearby POIs, review analysis. This is
  the seed data for the catalog. Do not contradict it or invent values.
- `docs/technical-discovery-v1.md` — architecture, DB schema, tech stack, project structure,
  Sprint 0. **Sections 3 (Roadmap) and 9 (Learning roadmap) are superseded** by
  `roadmap-v2-ai-engineer.md`; sections 1, 2, 4–8, 10, 11 remain authoritative.
- `docs/roadmap-v2-ai-engineer.md` — current roadmap, hours budget, the five research
  studies, and the dataset/annotation plan.
- `docs/sprint-praktyka-08-19-09.md` — the active sprint's day-by-day plan and demo script.

## Planned tech stack (per discovery doc §5)

Python 3.12+ · FastAPI · SQLAlchemy 2.0 (async) · Alembic · Pydantic v2 + pydantic-settings ·
**uv** (lockfile committed) · ruff + mypy (both enforced in CI) · pytest + pytest-asyncio +
httpx · PostgreSQL 16+ with **pgvector** and **btree_gist** · APScheduler → ARQ + Redis for
background jobs · structlog (JSON) · Docker Compose on a VPS.

Deliberately **not** used: LangChain / LlamaIndex (RAG is ~80 lines of transparent code);
a separate vector DB (pgvector in the same Postgres, ~500 chunks); microservices; Celery.

## Architecture — non-negotiable rules

Modular monolith. Dependency arrows point **down only**: `api → services → repositories → db`,
and separately `ai → services`.

1. **The AI layer never implements business logic and never touches the DB directly.** Agent
   tools are thin wrappers over the *same* services the REST API calls. This is the core
   design decision: it makes it physically impossible for the agent to invent a price or
   promise an occupied cottage.
2. **`services/` must not contain `import fastapi`.** Services must be callable from the
   agent, background jobs, and CLI without pulling in the web framework. This is grep-checkable.
3. **Double-booking is prevented at the database level**, not in Python. `availability_blocks`
   has `EXCLUDE USING gist (cottage_id WITH =, stay WITH &&)` with `stay` as a `daterange`
   using `'[)'` bounds (checkout day and check-in day do not conflict). Python checks are for
   nice error messages only; the guarantee lives in the constraint. A test asserting an
   overlapping insert raises `IntegrityError` is mandatory and is never cut.
4. **Money is always `Decimal` / Postgres `numeric`, never `float`.**
5. **Recommendation scoring is deterministic, tested code.** The LLM only does extraction
   (natural language → `GuestIntent` struct) at the input and explanation (struct → prose) at
   the output. Match scores/percentages are never produced by the LLM. See discovery §8.
6. **The eval harness (`app/ai/eval/`) exists from day one.** Every prompt / chunking /
   embedding / retrieval change is an experiment with a recorded result; CI runs the
   regression set and posts a metrics table as a PR comment. Experiment log lives in
   `docs/experiments/`.
7. Every LLM call is logged (`llm_calls` table): tokens, latency, cost.
8. LLM providers sit behind a project-owned `LLMClient` (~50 lines): model switch via env
   var, fake model in tests. Never import a vendor SDK inside business logic.

## Domain constraints

- Bookings are **request + host confirmation**, not instant confirmation.
- Booking.com iCal sync is **not real-time**. Overbooking in the sync window is a known,
  explicitly accepted limitation — design around it, don't pretend it's solved.
- The product domain is **Ukrainian-language**. Retrieval quality for Ukrainian must be
  measured (Research #1), not assumed.
- PII (names, phones, emails, chat text): don't log phones in plaintext, don't put PII in
  prompts without need. ЗУ «Про захист персональних даних» + GDPR (Polish guests).

## Dataset / annotation rules (roadmap §5)

- **Do not invent evaluation queries yourself.** Use real guest queries (Booking.com
  messages, Instagram Direct, phone questions, production logs). Only paraphrases of real
  queries are acceptable as synthetic, and they must carry a `synthetic` flag field.
- Datasets are versioned in git as **JSONL**, one commit per change, tagged `v1.0`, `v1.1`…
- Write `docs/annotation-guidelines.md` before annotating. Pilot on 30 items, rewrite the
  guidelines, re-annotate the pilot. Second annotator on 15% overlap; report Cohen's kappa /
  Krippendorff's alpha.

## Commands

No build/test tooling exists yet. Once scaffolded per the sprint plan, the intended commands
are (verify against `pyproject.toml` / `docker-compose.yml` when they exist):

```bash
uv sync                                   # install deps from lockfile
docker compose up                         # api + db + redis + worker; must work on a clean machine
uv run alembic upgrade head               # apply migrations
uv run alembic revision --autogenerate -m "..."
uv run pytest                             # full suite
uv run pytest path/to/test_file.py::test_name   # single test
uv run pytest tests/unit                  # unit only (fake repos, fast)
uv run pytest tests/integration           # against real Postgres in Docker — NOT SQLite
uv run ruff check . && uv run ruff format .
uv run mypy app
```

Integration tests run against real Postgres in Docker, never SQLite — SQLite has neither
`EXCLUDE` constraints nor `pgvector`, so a passing SQLite test would be lying.

## Project layout

Flat `app/` package at the repo root (not `src/app/` — the discovery doc §7 predates this
decision). Non-packaged uv project (`[tool.uv] package = false`, no `[build-system]`); `app`
is importable because `uv run` puts the repo root on `sys.path`. Run the API with
`uv run uvicorn app.main:app --reload`.

`app/` holds: `core/` (config, security, logging, exceptions), `db/models/`, `schemas/`
(Pydantic, external-facing), `repositories/` (the only place with SQL), `services/` (business
logic, no HTTP/LLM), `api/v1/endpoints/` (thin), `ai/` (`llm.py`, `embeddings.py`, `rag/`,
`agent/`, `eval/`), `jobs/`. Tests live in top-level `tests/{unit,integration}`.

## Git workflow

`main` (protected, PR only) ← `develop` ← short-lived `feat/…`, `chore/…`, `test/…`, `ci/…`
branches. Conventional Commits (`feat(cottages): …`, `fix(db): …`). CI on every PR:
ruff → mypy → pytest.
