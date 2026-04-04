# EVM_Operational_Playbook.md
## EveryVerseMatters.com — Operational Playbook

**Owner:** Aaron Blonquist
**Created:** March 28, 2026
**Last Updated:** April 4, 2026
**Version:** 1.1

---

### System Reference

| Document | Question It Answers | Path |
|----------|---------------------|------|
| **Source of Truth** | What are we building and why? | `EVM_Source_of_Truth.md` |
| **Data Reference** | What data/resources exist and how do we use them? | `EVM_Data_Reference.md` |
| **Quality Contract** | What must be true for output to be correct? | `EVM_Quality_Contract.md` |
| **Operational Playbook** (this document) | How do we actually do the work? | `EVM_Operational_Playbook.md` |

---

## 1. PIPELINE SEQUENCE

```
WEEKLY AUTOMATED PIPELINE (GitHub Actions — runs every Saturday 4:00 AM MT)

1. generate_commentary(next_week)     → Deep Dive content (all verse-by-verse)
2. discover_creators(next_week)       → third-party content
3. verify_urls(next_week)             → checks all links (graceful skip if missing)
4. verify_quotes(next_week)           → validates against Source Registry
5. generate_hook(next_week)           → homepage hook paragraph
6. generate_snippets(next_week)       → companion snippets for homepage
6.5 generate_audio(next_week)         → OpenAI TTS audio
6.6 verify_references(next_week)      → cross-reference existence check
6.7 run_qa(next_week)                 → Haiku hallucination audit
7. git commit + push                  → auto-commits generated content to repo
8. npm run build                      → Astro static site build
9. rsync deploy                       → push dist/ to VPS
```

Pipeline runs on Saturday morning so content is live before Sunday study.

### Special Week Handling [Implemented]
When `chapters` is empty but `passages` is populated (Easter, Christmas, Introduction), Stage 1 calls `run_special_week()` which loads `commentary_special.txt` and generates thematic commentary for curated passages instead of chapter iteration. All subsequent stages run identically — the `commentary.json` schema is the same regardless of week type. First validated: Easter Week 14 (March 28, 2026).

### GitHub Actions Configuration
- **Workflow file:** `.github/workflows/weekly-pipeline.yml`
- **Cron schedule:** `0 11 * * 6` (11:00 UTC = 4:00 AM MT)
- **Manual dispatch:** `workflow_dispatch` with optional `week` input for explicit week number
- **Required secrets:** `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `VPS_SSH_KEY`, `VPS_HOST`
- **Auto-commit:** `git pull --rebase` to handle concurrent changes, then commit + push generated content
- **Summary:** Posts verse count, cost, and error count to the workflow run page

> **History:** Pipeline automation was originally VPS cron (`/var/www/evm/run_weekly_pipeline.sh`). Migrated to GitHub Actions in March 2026 for reliability, visibility, and easier debugging.

### `run_pipeline.py` Flags
- `--skip-build` — skips internal build & deploy (used in CI where GitHub Actions handles deploy separately)
- `--skip-commentary` — skips commentary generation if content already exists
- `--dry-run` — show what would run without executing

---

## 2. STAGE DETAILS

### Stage 1: Commentary Generation

**Script:** `pipeline/generate_commentary.py`
**API:** Claude API (streaming) — model `claude-haiku-4-5` for standard weeks; Opus reserved for high-complexity chapters (Isaiah, Job, Psalms) where literary depth justifies cost
**Trigger:** GitHub Actions weekly workflow (Saturdays 4:00 AM MT) or manual dispatch
**Input:** Week number → looked up in `data/cfm_schedule.json` → returns scripture block
**Output:** `content/weeks/{year}/week-{nn}/commentary.json`

**Standard Week Process:**
1. Read `data/cfm_schedule.json` to determine the NEXT week's scripture block
2. For each chapter in the block, split into batches of 6 verses
3. If TCR data exists for the chapter (Genesis), load `content/tcr/{book}/chapter-{nn}.json` and inject TCR context (Hebrew, KJV, TCR rendering, translator notes, key terms) into the prompt
4. For each batch, call Claude API (streaming) with the Commentary Prompt Template (see Data Reference Section 7.1)
5. Response parsed via `json_parser.py` (strips markdown fences, fixes misplaced fields, handles trailing commas)
6. All chapters assembled into `commentary.json` for the week
7. Metadata logged to `logs/pipeline_runs.json`

**Special Week Process [Implemented]:**
1. `run()` detects `chapters` is empty but `passages` is populated → calls `run_special_week()`
2. Loads curated key passages from `cfm_schedule.json` `"passages"` field (e.g., `[{"book": "Isaiah", "chapter": 25, "verse_start": 8, "verse_end": 9}, ...]`)
3. Uses thematic system prompt (`pipeline/prompts/commentary_special.txt`) — instructs Claude to write commentary around the week's theme rather than sequential chapter coverage
4. Generates commentary for each passage batch, producing the same per-verse JSON schema
5. Output written to `commentary.json` in the standard location — all downstream stages work unchanged
6. `metadata.json` includes `"special_week": true` and `"theme"` fields

First successful run: Easter Week 14 (March 28, 2026) — 12 passages, 20 verses, all 12 pipeline stages passed. Creator discovery enriched with passage references for better search relevance. Downstream hardening fixes applied to `verify_quotes.py`, `verify_references.py`, and `run_qa.py` to ensure consistent return shapes when `commentary.json` is absent.

**API Call Structure:**
```python
with client.messages.stream(
    model="claude-haiku-4-5-20251001",
    max_tokens=32000,
    thinking={"type": "disabled"},
    system=COMMENTARY_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": user_message}],
) as stream:
    response = stream.get_final_message()
```

**Batching Strategy:**
- `VERSES_PER_BATCH = 6` — each API call generates commentary for 6 verses
- Large scripture blocks (10+ chapters) produce ~60 API calls per week
- Each call generates ~9,000-18,000 output tokens (comfortably within 32,000 max_tokens)
- Batch size 6 balances runtime (~90 min for a large week) against quality (no meaningful degradation vs batch size 3)
- The pipeline tracks token usage per call for cost monitoring

**Retry & Error Handling:**
- `api_client.py` retries on transient errors: `ConnectionResetError`, `httpx.RemoteProtocolError`, `RateLimitError`, `InternalServerError`, `APIConnectionError`
- Exponential backoff up to 120s, 4 attempts max
- `json_parser.py` handles markdown code fences (`` ```json ... ``` ``), misplaced commentary fields, extra braces, and trailing commas
- Failed batches save raw response to `logs/errors/` for debugging; pipeline continues with remaining batches

### Stage 2: Third-Party Content Discovery

**Script:** `pipeline/discover_creators.py`
**API:** Claude API — model `claude-sonnet-4-5-20250929` with `web_search` tool enabled
**Trigger:** Stage 2 of GitHub Actions weekly pipeline
**Input:** Week's scripture block + creator list from `data/sources.json`
**Output:** `content/weeks/{year}/week-{nn}/creators.json`

**Process:**
1. Load the list of tracked sources from `data/sources.json` (see Data Reference Section 2)
2. For each Tier 1 source, call Claude API with web search enabled:
   - Search query built from the source's `search_query_template` + this week's scripture block
   - Claude finds the creator's content for this specific week
   - Extracts: title, URL, publish date, content type, duration
   - Generates a 2-3 sentence summary of the creator's unique contribution
   - Attempts to identify specific verse references discussed
3. For Tier 2 sources, run a broader search pass
4. All results assembled into `creators.json`

**Two-cycle discovery:** `discover_creators.py` runs two passes per week — (1) 2026 current cycle, (2) 2022 OT archive cycle. Different guest scholars, different angles, 100% still relevant.

**Special Week enrichment:** For Special Weeks, the search `scripture` term includes specific passage references (e.g., `"Easter (Isaiah 25:8-9, Isaiah 53:3-5, Psalms 22:16-18...)"`) for better search relevance.

**API Call Structure:**
```python
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4000,
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    messages=[
        {
            "role": "user",
            "content": f"Find the latest Come Follow Me content from {source_name} "
                       f"for this week's reading: {scripture_block}. ..."
        }
    ]
)
```

### Stage 3: URL Verification & Quality Check

**Script:** `pipeline/verify_and_check.py`
**API:** Claude API — model `claude-sonnet-4-5-20250929` with `web_search` tool
**Status:** Currently graceful skip — to be built
**Input:** `commentary.json` and `creators.json` from Stages 1-2
**Output:** Updated files with verification flags + `quality_report.json`

**Process:**
1. URL Verification: For every URL in `creators.json`, confirm URL returns 200 and page content matches expected episode/article
2. Commentary Quality Check: Spot-check sample of verses for faithfulness, completeness, length
3. Output `quality_report.json` with pass/fail status

### Stage 5: Homepage Hook Paragraph

**Script:** `pipeline/generate_hooks.py`
**API:** Claude API — model `claude-sonnet-4-5-20250929`
**Input:** Deep Dive commentary + official CFM manual content
**Output:** `content/weeks/{year}/week-{nn}/hook.json`

### Stage 6: Companion Snippet Extraction

**Script:** `pipeline/generate_snippets.py`
**API:** Claude API — model `claude-haiku-4-5-20251001`
**Input:** Deep Dive commentary for the week
**Output:** `content/weeks/{year}/week-{nn}/snippets.json`

### Stage 6.5: Audio Generation

**Script:** `pipeline/generate_audio.py`
**API:** OpenAI tts-1-hd, voice: echo (warm male pastoral tone)
**Output:** `site/public/audio/week-{nn}-hook.mp3`

### Stage 7: Site Rebuild & Deploy

**Script:** `pipeline/build_and_deploy.sh`
**Process:**
1. Check `quality_report.json` — if critical failures, abort and alert Aaron
2. Run Astro static build: reads from `/content/` directory
3. Build generates HTML pages for: new Deep Dive page, homepage section, individual verse pages, All Weeks index
4. Deploy to Nginx webroot on VPS
5. Purge Cloudflare cache for updated pages
6. Log deployment status

### Week Summary Pipeline (for backfill)
`pipeline/generate_week_summary.py` generates a week-level summary (hook, overview, themes, key verses, restoration lens, application, highlights) for weeks without full verse-by-verse commentary. Used for backfill and as a lighter product tier. Cost: ~$0.06/week.

---

## 3. HOSTING & INFRASTRUCTURE

### Server & Repos
- **GitHub Repos:**
  - EVM: https://github.com/bashonda2/every-verse-matters
  - TCR: https://github.com/bashonda2/the-covenant-rendering
- **VPS:** `209.74.80.143` (SSH: `ssh root@209.74.80.143`) — also hosts Emree (PM2, port 3000) and MissionChecklist (Docker, port 5050)

### MCP Server
- **TypeScript** (`@modelcontextprotocol/sdk`) at `/var/www/evm/mcp-server/`
- **stdio transport** (Cursor/Claude Desktop): launched on-demand by IDE. Entry: `dist/server.js`.
- **HTTP transport** (Phase 3 web chat): `dist/http-server.js`, managed by PM2 as `evm-mcp-http`, listening on `127.0.0.1:3002`. Exposes 4 user-facing tools only (`ask`, `lesson_prep`, `compare_creators`, `deep_dive`). Auth: `MCP_HTTP_API_KEY` (Bearer token). Rate limit: 60 req/min per IP. Live at `https://everyversematters.com/api/mcp`.
- Ecosystem config: `/var/www/evm/mcp-server/ecosystem.config.cjs`

### Python Pipeline
- Dependencies in `requirements.txt` — `anthropic`, `openai`, `python-dotenv`
- Runs in GitHub Actions (Python 3.12) or locally

### CI/CD
- GitHub Actions workflow `.github/workflows/weekly-pipeline.yml`
- Saturdays 11:00 UTC (4:00 AM MT) or manual dispatch with explicit week number
- Auto-commits content and deploys via rsync
- *(Replaced VPS cron in March 2026.)*

### Content Store
- JSON files in `/content/` directory (MVP), PostgreSQL planned for Phase 2+

### Web Server
- **Reverse Proxy:** Nginx — static site served from `/var/www/evm/site/dist/`, API proxy `/api/` → `127.0.0.1:3002` (EVM MCP HTTP server)
- **Nginx Config:** `/etc/nginx/sites-available/everyversematters.com`

> **Port Map on VPS:**
> - `3000` — emree-server (API)
> - `3001` — emree-admin (Next.js admin panel)
> - `3002` — evm-mcp-http (EVM MCP HTTP server) ← Nginx `/api/` proxy target

### Domain, SSL, DNS, Email
- **Domain:** everyversematters.com (primary), everyversematters.org (redirect)
- **SSL:** Let's Encrypt via certbot (auto-renewing, cert at `/etc/letsencrypt/live/everyversematters.com/`)
- **DNS:** Namecheap — A records for `@` and `www` → `209.74.80.143`
- **Email:** `contact@everyversematters.com` → Gmail via ImprovMX (MX: `mx1/mx2.improvmx.com`). TCR uses `contact@thecovenantrendering.com` → Hotmail via Namecheap email forwarding.
- **VPS Path:** `/var/www/evm/` (site static files + MCP server + content data)

> **DEPLOY PATH — DO NOT GET THIS WRONG:**
> Nginx serves from **`/var/www/evm/site/dist/`** (confirmed via `nginx -T | grep root`).
> The correct deploy command is always:
> ```
> rsync -az --delete site/dist/ root@209.74.80.143:/var/www/evm/site/dist/
> ```
> **NOT** `/var/www/evm/dist/` — that directory exists but Nginx does not serve from it.

---

## 4. TOOLING ROLES

| Tool | Role | When to Use |
|------|------|-------------|
| **Claude API (Opus)** | Commentary generation engine | Automated weekly pipeline — generates all verse-by-verse content |
| **Claude API (Sonnet) + Web Search** | Third-party content discovery, URL verification, QA | Automated weekly pipeline — finds and validates creator content |
| **Claude Chat (Opus — claude.ai)** | PM, strategy, prompt refinement, research, browser tasks | Ad-hoc: refining prompts, researching new creators, checking live site, updating Source of Truth |
| **Cursor + Sonnet** | Site development, pipeline code, infrastructure | Building: all code written and tested here |
| **Cowork** | File management, non-code project tasks | Optional: organizing files, generating docs, slide decks |
| **Aaron** | Review, editorial oversight, deployment approval | Weekly: reviews flagged commentary, approves deploy, strategic decisions |

---

## 5. COST PROJECTIONS

### Weekly Operating Costs (Automated Pipeline)

| Component | Model | Estimated Weekly Cost |
|-----------|-------|---------------------|
| Deep Dive Commentary | Haiku 4.5 | $2-4 |
| Hook Paragraph Generation | Sonnet 4.5 | $0.10-0.25 |
| Hook Audio (TTS) | OpenAI tts-1-hd | ~$0.02/week |
| Companion Snippet Extraction | Haiku 4.5 | $0.05-0.10 |
| Quote Verification | Sonnet + Web Search | $0.25-0.50 |
| Creator Discovery | Sonnet + Web Search | $1-3 |
| URL Verification + QA | Sonnet + Web Search | $0.50-1 |
| VPS Hosting | Existing server | $0 |
| Domain | Annual | ~$0.25/week |
| Cloudflare CDN | Free tier | $0 |
| User-Facing AI (responses + Haiku audits) | Sonnet + Haiku | $5-50/month (scales with traffic) |
| **Total Weekly** | | **~$4-9/week** |
| **Total Annual** | | **~$210-470/year** |

*Audio (OpenAI): requires `OPENAI_API_KEY` in `.env`. Not part of the Anthropic-only cost estimates above.*

**Actual Week 9 Data (first real pipeline run, Feb 22):**
- Model: `claude-haiku-4-5-20251001` ($1/$5 per MTok)
- 154 verses generated, ~57 API calls
- ~390,000 output tokens
- Estimated cost: ~$2.10
- Runtime: ~71 minutes

**Note:** User-facing AI costs scale with traffic. At low traffic (100 queries/day), costs are minimal (~$5/month). At scale (10,000 queries/day), costs could reach $50-150/month but would justify a premium tier or usage-based pricing.

### Cost Optimization Options
- Haiku 4.5 delivers strong commentary quality at 1/5 the cost of Opus — validated in Week 9 run
- Use Opus selectively for complex chapters (Isaiah, Job) where depth matters most
- Use Anthropic Batch API for non-time-sensitive backfill — 50% discount
- Cache and reuse cross-reference data across verses in the same chapter
- As Anthropic prices decrease over time, costs will naturally fall

---

## 6. COMPLETED WORK LOG

### Hack Week — Feb 22-27, 2026

| Date | Milestone |
|------|-----------|
| Feb 22 (Day 0) | Domain secured. SOT created. Pipeline built with streaming, batching, error handling. Week 9 commentary generated (154 verses, Genesis 18-23). MCP server built (17 tools). DNS + SSL + Nginx configured. Landing page deployed. |
| Feb 22 (Evening) | `generate_week_summary.py` built. Week summaries for Weeks 1-8 ($0.49). Audio for 8 weeks. `discover_creators.py` + `verify_quotes.py` built. Full 8-stage pipeline (`run_pipeline.py`). VPS dry-run of Week 10. |
| Feb 22-23 | Source Registry created (26 sources). Hook + snippet pipelines built. Homepage redesigned (three-tier Weekly Feed). Creator discovery expanded to 18 entries. `generate_audio.py` (OpenAI TTS, echo voice). |
| Feb 23 | Full aesthetic redesign — editorial light-first theme (Cormorant Garamond + Source Sans 3 + Cinzel). Homepage polish: frosted glass header, hook cards, ornamental dividers, dark gradient Deep Dive CTA. |
| Feb 23-24 | TCR integration: Genesis 50 chapters in `content/tcr/`. MCP tools for TCR queries. Deep Dive KJV/JST/TCR tabs. TCR site deployed at thecovenantrendering.com. |
| Feb 23 | Anti-hallucination hardening: prompt rules (all 4 citation fields required), `verify_references.py` (cross-reference checker), `run_qa.py` (Haiku audit, >10% blocks deploy). 10-stage pipeline. |
| Feb 23 | Header polish, deploy path fix (`/var/www/evm/site/dist/`), global.css import fix, nav updates. |
| Feb 23-24 | MCP HTTP transport deployed (port 3002, PM2, auth + rate limiting). |
| Feb 23 | Shared with family/ward for feedback. |

### Weekly Production — March–April 2026

| Date | Milestone |
|------|-----------|
| Mar 7 | First fully automated GitHub Actions pipeline run (Week 10). Pipeline migrated from VPS cron. |
| Mar 28 | Special Week pipeline implemented: `run_special_week()` in `generate_commentary.py`, `commentary_special.txt` prompt, enriched creator discovery for Special Weeks, downstream hardening fixes (`verify_quotes.py`, `verify_references.py`, `run_qa.py`). Easter Week 14 deployed via GitHub Actions — 12 passages, 20 verses, all stages passed. |
| Mar 28 | SOT restructured into 4-document architecture (Source of Truth, Data Reference, Quality Contract, Operational Playbook). |
| Apr 4 | Anthropic API key rotated — updated `ANTHROPIC_API_KEY` secret in GitHub Actions. Week 15 (Exodus 7-13) deployed: 155 verses, 7 chapters, 8 stages passed, QA 0/155 flagged (0.0%), runtime 82 min. |

---

*This document describes how to operate EveryVerseMatters.com — pipeline, deploy, infrastructure. For product vision, see `EVM_Source_of_Truth.md`. For data schemas and resources, see `EVM_Data_Reference.md`. For quality rules, see `EVM_Quality_Contract.md`.*

---
**Version 1.1 — April 4, 2026**
