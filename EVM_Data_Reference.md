# EVM_Data_Reference.md
## EveryVerseMatters.com — Data Reference

**Owner:** Aaron Blonquist
**Created:** March 28, 2026
**Last Updated:** August 26, 2026
**Version:** 1.1

---

### System Reference

| Document | Question It Answers | Path |
|----------|---------------------|------|
| **Source of Truth** | What are we building and why? | `EVM_Source_of_Truth.md` |
| **Data Reference** (this document) | What data/resources exist and how do we use them? | `EVM_Data_Reference.md` |
| **Quality Contract** | What must be true for output to be correct? | `EVM_Quality_Contract.md` |
| **Operational Playbook** | How do we actually do the work? | `EVM_Operational_Playbook.md` |

---

## 1. DATA MODEL

```
BOOKS
  - id, name, testament, abbreviation, chapter_count
  - e.g., { id: 1, name: "Genesis", testament: "OT", abbr: "Gen", chapters: 50 }

CHAPTERS
  - id, book_id, chapter_number, verse_count

VERSES
  - id, chapter_id, verse_number, text_kjv, text_jst (if applicable)

CFM_WEEKS
  - id, year, week_number, date_start, date_end, title, theme
  - scripture_refs (array of book/chapter/verse ranges)
  - official_url (link to churchofjesuschrist.org lesson)

EVM_COMMENTARY
  - id, verse_id, cfm_week_id
  - narrative (main commentary text)
  - word_study (Hebrew/Greek insights)
  - cross_references (JSON array of verse_ids with notes)
  - historical_context
  - restoration_lens
  - prophetic_quotes (JSON array with speaker, talk, date, quote)
  - christological_typology
  - application
  - generated_by (model version)
  - generated_at (timestamp)
  - reviewed (boolean — has Aaron reviewed this?)
  - review_notes (any corrections or flags)

THIRD_PARTY_SOURCES
  - id, name, type (podcast/blog/youtube/website)
  - url, rss_feed_url, youtube_channel_id
  - hosts, description
  - active (boolean)
  - search_query_template (how the pipeline finds their weekly content)

THIRD_PARTY_CONTENT
  - id, source_id, cfm_week_id
  - title, url, published_at
  - content_type (episode/article/video)
  - summary (AI-generated)
  - verse_tags (JSON array of verse_ids this content references)
  - duration_minutes (for audio/video)
  - url_verified (boolean — confirmed live at last pipeline run)
  - url_verified_at (timestamp)

PIPELINE_RUNS
  - id, week_id, run_type (commentary/creators/full)
  - started_at, completed_at
  - status (success/partial/failed)
  - tokens_used, estimated_cost
  - errors (JSON array of any issues)
  - output_path (where files were written)
```

---

## 2. THIRD-PARTY CONTENT SOURCES — THE CATALOG

### Tier 1: Major Weekly Producers (consistently publish every CFM week)

| Source | Type | Hosts/Authors | Specialty | URL | Search Strategy |
|--------|------|---------------|-----------|-----|-----------------|
| **Scripture Central** | Podcast/Video/Articles | John Hilton III, Taylor Halverson, Tyler Griffin, Lynn Hilton Wilson | Academic rigor, scholarly depth, multiple series | scripturecentral.org | Web search: "Scripture Central Come Follow Me [scripture block]" |
| **Don't Miss This** | Podcast/Video | Emily Freeman, David Butler | Accessibility, enthusiasm, emotional connection | dontmissthis.com | Web search: "Don't Miss This [scripture block]" |
| **Follow Him (followHIM)** | Podcast | Hank Smith, John Bytheway + weekly guest scholars | Long-form scholarly conversation, guest expertise | followhim.co | Web search: "Follow Him podcast [scripture block]" |
| **Talking Scripture** | Podcast | Mike Day, Bryce Dunford | Conversational deep dives | talkingscripture.com | Web search: "Talking Scripture [scripture block]" |
| **Line Upon Line** | Video/Podcast | Living Scriptures | Wide-audience, family-friendly overviews | livingscriptures.com | Web search: "Line Upon Line Living Scriptures [scripture block]" |
| **Meridian Magazine CFM** | Podcast/Articles | Scot & Maurine Proctor | Written depth, Holy Land context, photography | latterdaysaintmag.com | Web search: "Meridian Magazine Come Follow Me [scripture block]" |
| **One Minute Scripture Study** | Podcast | Cali Black | Quick daily bites (1-5 min, 5x/week), accessible | oneminutescripturestudy.com | RSS feed / podcast app — not web-indexable |
| **Teaching with Power** | Podcast/Blog | Benjamin Wilcox | Seminary/Sunday School teacher focus, downloadable lesson materials | teachingwithpower.com | Web search: "Teaching with Power [scripture block]" |
| **The Scriptures Are Real** | Podcast/Video | Kerry Muhlestein & Lamar Newmeyer | BYU Egyptology/ancient scripture, expert interviews, top 0.5% global podcasts | podcasts.apple.com/us/podcast/the-scriptures-are-real/id1600496638 | Web search: "Scriptures Are Real Muhlestein [scripture block]" |
| **Unshaken Saints** | Podcast/Video | Jared Halverson | Verse-by-verse deep dives (2-4 hrs), faith-crisis support, closest format to EVM | unshaken.org | Web search: "Unshaken Saints [scripture block]" |
| **Church News** | Articles | Church News staff | Weekly verified prophetic quote compilations — key Source Registry feeder. **Primary source for Special Weeks** (Easter, Christmas): publishes seasonal articles, General Conference coverage, First Presidency messages, and prophetic quote compilations. URL: https://www.thechurchnews.com/ | thechurchnews.com | Web search: "Church News Come Follow Me [scripture block] leaders said" (standard weeks) / "Church News Easter 2026" or "Church News Christmas 2026" (Special Weeks) |
| **Come Follow Me Daily** | Website | Various | Weekly aggregation of all CFM content | comefollowhimdaily.com | Direct fetch: check weekly page |
| **LDS Daily** | Website/Blog | LDS Daily | Weekly study guides, historical context, aggregated podcast links | ldsdaily.com | Web search: "LDS Daily Come Follow Me [scripture block]" |

### Tier 2: Supplementary/Specialized Sources

| Source | Type | Specialty |
|--------|------|-----------|
| **BYU Religious Studies Center (RSC)** | Articles | Peer-reviewed academic articles by BYU religion faculty; evergreen by scripture block |
| **BYUtv Come Follow Up** | Video | Television-quality studio discussions; re-airing 2022 OT episodes in 2026 |
| **Maxwell Institute** | Podcast/Articles | Academic, interfaith-friendly scholarship; irregular publication schedule |
| **Book of Mormon Central** | Articles/Video | BoM cross-references (especially relevant for OT year) |
| **The Red Crystal** | Blog/Printables | Youth lesson helps and teacher resources |
| **Gospel Grab Bag** | Blog/Printables | Primary and family activity resources (ages 1-16) |
| **Hope in Christ** | Podcast | Ben Peterson — devotional approach |
| **Talk of Him** | Podcast | Ganel-Lynn Condie & John Fossum |
| **Church Newsroom** | Official | Official Church supplementary resources |
| **Insights from the Apostles** | Video | Monthly videos from Quorum of the Twelve |

*Note: Scripture Gems (Jon & Jay Fullmer) appears inactive since March 2024 — downgraded from Tier 1.*

### Tier 3: Archive Sources (for backfill from previous OT cycle)
- 2022 was the last Old Testament year in CFM
- All Tier 1 and Tier 2 sources will have archived 2022 OT content
- This content can be mapped to the same verse references for enrichment
- Previous cycles: 2019 (NT), 2020 (BoM), 2021 (D&C), 2022 (OT), 2023 (NT), 2024 (BoM), 2025 (D&C)

---

## 3. TECHNICAL ARCHITECTURE — MCP-FIRST

### 3.1 Core Concept: Build Once, Use Everywhere

Instead of a rigid cron pipeline, EVM is built around an MCP (Model Context Protocol) server hosted on Aaron's VPS. This server exposes tools that can be called:
- **Interactively** — from Cursor or Claude Desktop, for content review and steering
- **Programmatically** — from GitHub Actions for weekly automation (migrated from VPS cron March 2026)
- **From the website** — powering the user-facing AI chat

Build once, use everywhere.

### 3.2 MCP Server — Tool Catalog

#### CONTENT TOOLS
- `generate_commentary(week, chapter, verse_range)` — Calls Claude API (Opus) to produce verse-by-verse commentary. Stores results in content DB.
- `discover_creators(week)` — Uses Claude API (Sonnet) + web search to find all third-party CFM content published for a given week. Returns titles, URLs, creators, and AI-generated summaries.
- `verify_urls(week)` — Checks all stored third-party URLs for a week are still live. Flags dead links.
- `search_content(query)` — Full-text search across all generated commentary and creator content.

#### PUBLISHING TOOLS
- `get_week(week_number)` — Retrieves the full assembled content package for a week (commentary + creators + official CFM).
- `publish(week)` — Triggers a build and deploy of the site with updated content.
- `backfill(week_range)` — Batch generates commentary and creator discovery for a range of historical weeks. Uses Anthropic Batch API for cost savings.

#### QA TOOLS
- `verify_quotes(week)` — Uses web search to verify every General Conference or prophetic quote in the week's commentary. Flags unverifiable quotes.
- `flag_review(week, verse, reason)` — Marks a specific verse's commentary for Aaron's manual review.
- `run_qa(week)` — Runs full QA suite: URL verification, quote verification, doctrinal tone check.

#### USER AI TOOLS (powers the user-facing chat on the website)
- `ask(question, context)` — Answers user questions grounded in EVM's content database. Context includes what week/verse the user is currently viewing.
- `lesson_prep(topic, duration, audience)` — Generates a lesson outline for Gospel Doctrine teachers, seminary teachers, or family home evening.
- `compare_creators(week, topic)` — Compares what different CFM creators said about a specific topic or verse.
- `deep_dive(verse, dimensions[])` — Goes deeper on a specific verse across chosen dimensions (Hebrew, history, typology, cross-references, etc.)

#### ANALYTICS TOOLS
- `log_query(user_query, response, audit_result, metadata)` — Logs every user-facing AI interaction.
- `get_popular_queries(timeframe)` — Returns most frequent user queries for a time period.
- `get_verse_engagement(verse_id)` — Shows which verses generate the most user questions.
- `get_unmet_needs()` — Surfaces queries where the AI had low-confidence answers or hit guardrail boundaries.

### 3.3 Clients — Who Calls the MCP Server

| Client | Use Case |
|--------|----------|
| everyversematters.com chat widget | User-facing AI — members ask questions, get grounded answers |
| Aaron in Cursor | Interactive builds, content review, steering commentary generation |
| Aaron in Claude.ai | PM work, strategy, research, Source of Truth updates |
| GitHub Actions (weekly) | Automated pipeline — runs `run_pipeline.py`, commits content, builds & deploys via rsync |
| Future admin dashboard | Web UI for monitoring pipeline, reviewing flagged content, viewing analytics |

### 3.4 Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **MCP Server** | Official MCP SDK (TypeScript or Python) | Exposes all tools via standard protocol |
| **Frontend** | Astro (static) | Static generation for SEO + fast page loads; consumes MCP tools |
| **Chat Widget** | React component | User-facing AI interface, calls MCP server via API |
| **Styling** | Tailwind CSS | Rapid development, mobile-first, modern aesthetic |
| **Content Store** | PostgreSQL or SQLite | Structured storage for commentary, creator content, and query logs |
| **Content Files** | JSON files in `/content/` directory | Simple, git-versioned, fallback for MVP |
| **Pipeline Client** | Python 3.12+ | GitHub Actions workflow that runs pipeline stages in sequence |
| **AI API** | Anthropic Claude API (Opus for commentary, Sonnet for summaries, Haiku for audits) | Native web search tool, best quality |
| **Search** | PostgreSQL FTS or Meilisearch | Full-text search across commentary |
| **CDN** | Cloudflare (free tier) | Caching, performance, DDoS protection |
| **CI/CD** | GitHub Actions (cron schedule + manual dispatch) | Weekly pipeline scheduling, auto-commit, deploy |
| **Monitoring** | Query logs + analytics tools + email alerts | Pipeline and AI interaction health tracking |

### 3.5 API Endpoints

```
GET /api/weeks                              → List all CFM weeks for current year
GET /api/weeks/:weekId                      → Full week view with all content
GET /api/weeks/:weekId/verses               → All verses with commentary for a week
GET /api/verses/:bookAbbr/:chapter/:verse   → Single verse with full commentary
GET /api/sources                            → List all third-party sources
GET /api/sources/:sourceId/content          → Content from a specific creator
GET /api/search?q=                          → Full-text search across all commentary
GET /api/pipeline/status                    → Latest pipeline run status (admin)
GET /api/pipeline/history                   → Pipeline run history (admin)
POST /api/chat                              → User-facing AI chat endpoint (calls MCP ask tool)
GET /api/analytics/popular                  → Popular queries (admin)
GET /api/analytics/engagement               → Verse engagement stats (admin)
GET /api/weeks/:weekId/hook                 → Hook paragraph for a week
GET /api/weeks/:weekId/snippets             → Companion snippets for a week
GET /api/registry                           → Full source registry (for About > Sources page)
GET /api/registry/:category                 → Sources filtered by category
```

### 3.6 SEO Strategy
Every verse gets its own URL: `everyversematters.com/genesis/18/1`
Every Deep Dive page gets its own URL: `everyversematters.com/deep-dive/2026/week-9`
This creates thousands of indexable, scripture-rich pages that rank for specific verse searches. The Deep Dive URL structure keeps the full commentary as a distinct, linkable destination separate from the homepage.

---

## 4. PIPELINE CONFIGURATION FILES

### `data/cfm_schedule.json` — Full weekly schedule
```json
[
  {
    "week": 9,
    "year": 2026,
    "date_start": "2026-02-23",
    "date_end": "2026-03-01",
    "title": "Sarah and Isaac",
    "scripture_block": "Genesis 18–23",
    "chapters": [
      {"book": "Genesis", "chapter": 18},
      {"book": "Genesis", "chapter": 19},
      {"book": "Genesis", "chapter": 20},
      {"book": "Genesis", "chapter": 21},
      {"book": "Genesis", "chapter": 22},
      {"book": "Genesis", "chapter": 23}
    ],
    "official_url": "https://www.churchofjesuschrist.org/study/manual/come-follow-me-for-home-and-church-old-testament-2026/09"
  }
]
```

Special Weeks use `"chapters": []` with a `"passages"` array and `"theme"` field:
```json
{
  "week": 14,
  "chapters": [],
  "passages": [
    {"book": "Isaiah", "chapter": 25, "verse_start": 8, "verse_end": 9},
    {"book": "Isaiah", "chapter": 53, "verse_start": 3, "verse_end": 5}
  ],
  "theme": "He Will Swallow Up Death in Victory"
}
```

### `data/sources.json` — Creator catalog with search templates
```json
[
  {
    "id": "scripture-central",
    "name": "Scripture Central",
    "tier": 1,
    "type": "podcast/video/articles",
    "url": "https://scripturecentral.org",
    "search_query_template": "Scripture Central Come Follow Me {scripture_block}",
    "active": true
  }
]
```

### `data/config.json` — Pipeline settings
```json
{
  "commentary_model": "claude-opus-4-6",
  "discovery_model": "claude-sonnet-4-5-20250929",
  "max_tokens_per_chapter": 16000,
  "pipeline_timezone": "America/Denver",
  "pipeline_schedule": {
    "commentary": "0 4 * * 6",
    "discovery": "0 6 * * 6",
    "verify": "0 7 * * 6",
    "build": "30 7 * * 6",
    "notify": "0 8 * * 6"
  },
  "notification_email": "aaron@covenantbuilders.ai",
  "cost_alert_threshold_weekly": 50.00,
  "anthropic_api_key_env": "ANTHROPIC_API_KEY"
}
```

---

## 5. DIRECTORY STRUCTURE

```
everyversematters/
├── mcp-server/                        # MCP server (tools exposed to all clients)
│   ├── src/
│   │   ├── tools/
│   │   │   ├── content.ts             # generate_commentary, discover_creators, etc.
│   │   │   ├── publishing.ts          # get_week, publish, backfill
│   │   │   ├── qa.ts                  # verify_quotes, flag_review, run_qa
│   │   │   ├── user_ai.ts            # ask, lesson_prep, compare_creators, deep_dive
│   │   │   └── analytics.ts          # log_query, get_popular_queries, etc.
│   │   ├── server.ts                  # MCP server entry point
│   │   └── db.ts                      # Database connection
│   ├── package.json
│   └── tsconfig.json
│
├── .github/workflows/
│   └── weekly-pipeline.yml            # GitHub Actions: weekly cron + manual dispatch
│
├── pipeline/                          # Content generation pipeline (called by GitHub Actions)
│   ├── generate_commentary.py         # Stage 1: Deep Dive commentary generation
│   ├── discover_creators.py           # Stage 2: Third-party content discovery
│   ├── verify_and_check.py            # Stage 3: URL verification + QA
│   ├── verify_quotes.py               # Stage 4: Quote verification against Source Registry
│   ├── generate_hooks.py              # Stage 5: Homepage hook paragraph generation
│   ├── generate_snippets.py           # Stage 6: Companion snippet extraction
│   ├── build_and_deploy.sh            # Stage 7: Static site build + deploy
│   ├── notify.py                      # Email admin summary
│   ├── run_pipeline.py                # Master orchestrator (runs all stages)
│   ├── prompts/
│   │   ├── commentary_system.txt      # Standard week system prompt
│   │   ├── commentary_special.txt     # Special week thematic prompt
│   │   ├── discovery_system.txt       # Creator discovery prompt
│   │   ├── hook_generation.txt        # Hook paragraph prompt
│   │   └── snippet_extraction.txt     # Snippet extraction prompt
│   └── utils/
│       ├── api_client.py              # Claude API wrapper with retry/logging
│       ├── json_parser.py             # Parse and validate Claude JSON output
│       ├── registry_loader.py         # Load and query sources_registry.json
│       └── cost_tracker.py            # Token usage and cost monitoring
│
├── data/                              # Static reference data
│   ├── cfm_schedule.json              # Full 52-week schedule
│   ├── sources.json                   # Third-party creator catalog
│   ├── sources_registry.json          # Master source registry (whitelist)
│   ├── config.json                    # Pipeline configuration
│   └── kjv_verses/                    # KJV text by book (for verse text)
│       ├── genesis.json
│       ├── exodus.json
│       └── ...
│
├── content/                           # Generated content (pipeline output)
│   ├── weeks/
│   │   └── 2026/
│   │       ├── week-09/
│   │       │   ├── commentary.json    # Verse-by-verse Deep Dive commentary
│   │       │   ├── creators.json      # Third-party content catalog
│   │       │   ├── hook.json          # Homepage hook paragraph
│   │       │   ├── snippets.json      # Companion snippets (5-7 per week)
│   │       │   ├── quality_report.json # QA results
│   │       │   └── metadata.json      # Run stats (tokens, cost, timing)
│   │       ├── week-10/
│   │       └── ...
│   ├── tcr/                           # The Covenant Rendering (Hebrew OT, all 39 books)
│   │   ├── genesis/chapter-01.json   # Per-chapter WLC Hebrew + KJV + TCR rendering
│   │   ├── ...                        # translator notes, key terms, expanded meanings
│   │   └── malachi/
│   └── dss/                           # Dead Sea Scrolls variant data
│       └── isaiah/                    # 1QIsaᵃ (Great Isaiah Scroll), all 66 chapters
│           ├── chapter-01.json
│           ├── ...
│           └── chapter-66.json
│
├── site/                              # Astro frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.astro            # Homepage — Weekly Feed (scrolling, two-column)
│   │   │   ├── about.astro            # About page with dynamic Sources section
│   │   │   ├── deep-dive/
│   │   │   │   └── [week].astro       # Deep Dive pages (verse-by-verse)
│   │   │   ├── weeks/
│   │   │   │   └── [week].astro       # All Weeks index
│   │   │   └── [book]/
│   │   │       └── [chapter]/
│   │   │           └── [verse].astro  # Individual verse pages (SEO)
│   │   ├── components/
│   │   │   ├── WeekSection.astro      # Homepage week section (hook + two columns)
│   │   │   ├── CompanionSnippet.astro # Individual companion snippet card
│   │   │   ├── VerseCommentary.astro  # Single verse display (Deep Dive)
│   │   │   ├── WordStudy.astro        # Expandable word study
│   │   │   ├── CrossReferences.astro  # Expandable cross-refs
│   │   │   ├── CreatorCard.astro      # Third-party content card
│   │   │   ├── SourcesGrid.astro      # About > Sources section (from registry)
│   │   │   ├── WeekNav.astro          # Week navigation
│   │   │   └── Layout.astro           # Base layout
│   │   └── styles/
│   │       └── global.css
│   ├── public/
│   │   ├── favicon.ico
│   │   └── images/
│   └── astro.config.mjs
│
├── logs/                              # Pipeline logs
│   ├── pipeline_runs.json             # Run history
│   └── errors/                        # Error logs by date
│
├── nginx/                             # Nginx config
│   └── everyversematters.conf
│
├── .env                               # ANTHROPIC_API_KEY, etc.
├── requirements.txt                   # Python dependencies
├── package.json                       # Node dependencies (site)
└── README.md                          # Project overview
```

---

## 6. SCRIPTURE TEXT SOURCES — TCR & DSS

Two per-verse text sources supplement the KJV (and optional JST) at both the pipeline layer and the Deep Dive UI layer. Both live under `content/` in per-book, per-chapter JSON files, and both are loaded by identical patterns in `pipeline/generate_commentary.py` and `site/src/pages/2026/week/[week].astro`.

### 6.1 The Covenant Rendering (TCR)

**Coverage:** Full Old Testament — 39 books, all chapters.
**Source:** `bashonda2/the-covenant-rendering` (Aaron Blonquist, CC-BY-4.0).
**Base text:** Westminster Leningrad Codex (WLC).
**Purpose:** A scholarly modern-English rendering paired with translator notes and Hebrew key-term glosses. Injected into every commentary generation prompt for OT books; rendered in the Deep Dive UI with a sage-green accent.
**Path:** `content/tcr/{book-slug}/chapter-{NN}.json`

Per-verse schema (fields commentary generation and UI consume):
```json
{
  "verse": 1,
  "text_hebrew": "בְּרֵאשִׁית בָּרָא אֱלֹהִים...",
  "text_kjv": "In the beginning God created the heaven and the earth.",
  "rendering": "In the beginning, God created the heavens and the earth.",
  "expanded_rendering": "Optional expanded gloss...",
  "translator_notes": ["Note on the perfect tense...", "..."],
  "key_terms": [
    {
      "hebrew": "רֵאשִׁית",
      "transliteration": "re'shit",
      "rendered_as": "beginning",
      "semantic_range": "start, firstborn, chief part",
      "note": "Root ראש (rosh, 'head') — same word behind 'firstfruits'."
    }
  ],
  "reading_level": "8th grade"
}
```

### 6.2 Dead Sea Scrolls — Great Isaiah Scroll (1QIsaᵃ)

**Coverage:** Isaiah only — all 66 chapters. Extensible to other DSS books (Psalms fragments, Samuel scrolls) by adding to the slug map on both sides.
**Source:** `bashonda2/the-covenant-rendering` (DSS data alongside TCR), CC-BY-4.0.
**Manuscript:** 1QIsaᵃ (Qumran Cave 1), c. 125 BCE, Shrine of the Book, Israel Museum.
**Purpose:** Surface pre-Christian Hebrew variants (orthographic → moderate → theological) so the commentary can note where the DSS text materially agrees with, differs from, or amplifies the Masoretic Text. First live in Weeks 38-42 (Isaiah), including Isaiah 53 (Week 41) where 1QIsaᵃ's "he shall see light" reading is the most consequential OT variant in scholarship.
**Path:** `content/dss/isaiah/chapter-{NN}.json`

Chapter-level meta:
```json
{
  "meta": {
    "book": "Isaiah",
    "chapter": 53,
    "tradition": "dss-1qisaiah-a",
    "tradition_label": "Dead Sea Scrolls (1QIsaᵃ)",
    "source_text": "1QIsaᵃ (Qumran Cave 1)",
    "base_text": "Westminster Leningrad Codex (WLC)",
    "date": "c. 125 BCE",
    "manuscript_location": "Shrine of the Book, Israel Museum, Jerusalem",
    "license": "CC-BY-4.0"
  },
  "preamble": {
    "summary": "One-paragraph orientation to this chapter in 1QIsaᵃ.",
    "notable_variants": "Verse-by-verse cheat sheet of variants.",
    "scroll_condition": "Physical state of the column.",
    "column_reference": "Column XLIV of 1QIsaᵃ"
  },
  "verses": [ /* see below */ ]
}
```

Per-verse schema:
```json
{
  "verse": 11,
  "has_variant": true,
  "significance": "theological",
  "mt_reading": "יִרְאֶה",
  "dss_reading": "יראה אור",
  "variant_rendering": "he shall see light",
  "mt_rendering": "he shall see",
  "manuscript_reference": "1QIsaᵃ col. XLIV, line 11",
  "variant_notes": [
    "MT reads simply yireh; 1QIsaᵃ adds אור (light)...",
    "Second note (up to 3 shown in prompt)..."
  ]
}
```

**Significance tiers:** `minor` (orthographic / plene spelling), `moderate` (word-form or verb-form differences), `theological` (variant meaningfully affects meaning).

**UI rendering rule:** The Deep Dive shows a DSS block only when meaningful — i.e. when the DSS rendering differs from MT, when variant notes are present, or when the significance is `theological`. Verses that are purely orthographic variants (renderings identical between MT and DSS, no notes) are skipped to avoid noise.

---

## 7. SOURCE REGISTRY — DATA MODEL

### Purpose
The Source Registry (`data/sources_registry.json`) is EVM's editorial backbone — a living, curated catalog of every source the platform is authorized to draw from. See Quality Contract for vetting rules and enforcement.

### Source Categories

| Category | Description | Examples |
|----------|-------------|----------|
| **Official Church Sources** | Church-published materials | CFM manual, General Conference talks, seminary/institute manuals, Gospel Topics essays, Ensign/Liahona articles |
| **Scripture & Text** | Primary scripture texts and translations | KJV, JST revisions, Dead Sea Scrolls references, Hebrew/Greek lexicons |
| **Scholarly/Academic** | Peer-reviewed or institutionally published biblical scholarship | BYU RSC, Maxwell Institute, Scripture Central research articles, published ANE scholarship |
| **CFM Creators** | Weekly Come Follow Me content producers | Podcasts, YouTube channels, blogs — the existing Tier 1 and Tier 2 catalog |
| **Prophetic Commentary** | Specific, individually cited talks and publications by Church leaders | Individual General Conference talks (speaker, title, date), published books, Ensign articles |
| **Historical/Archaeological** | ANE scholarship, geographic context, archaeological findings | Specific academic publications, archaeological survey reports, geographic references |

### Registry Entry Schema

```json
{
  "id": "gc-holland-grandeur-2003",
  "name": "The Grandeur of God",
  "category": "prophetic_commentary",
  "type": "general_conference_talk",
  "author": "Elder Jeffrey R. Holland",
  "date": "2003-04",
  "url": "https://www.churchofjesuschrist.org/study/general-conference/2003/04/the-grandeur-of-god",
  "verified": true,
  "verified_at": "2026-02-23",
  "mcp_authorized": true,
  "notes": "Apostolic address on God's nature and majesty",
  "added_at": "2026-02-23",
  "added_by": "aaron"
}
```

### Registry File Location
`data/sources_registry.json` — loaded by the MCP server at startup. The Sources page on the website is generated from this same file (single source of truth).

### How the Registry Integrates with the Pipeline

```
COMMENTARY GENERATION
  → Claude generates verse commentary including prophetic quotes
  → verify_quotes tool checks each quote against sources_registry.json
  → If quote matches a verified source → include with citation
  → If quote cannot be verified → flag and strip before publish
  → Only verified, registry-sourced quotes appear on the site

USER-FACING AI
  → User asks a question
  → AI generates response grounded in Deep Dive content
  → Any quotes or citations checked against registry
  → Guardrail audit (Haiku) includes source verification check

SOURCES PAGE (About > Sources)
  → Generated from data/sources_registry.json
  → Grouped by category
  → Each entry shows: name, author/host, type, URL, description
  → Dynamic — updated whenever new sources are vetted and added
  → Readers can browse and discover new study resources
```

---

## 8. PROMPT TEMPLATES

### 7.1 Commentary Prompt Template (Standard Weeks)

This is the system prompt used for all standard week commentary generation API calls. It is the single most important prompt in the system.

```
SYSTEM PROMPT — EVM Commentary Generator

You are a scripture commentary engine for EveryVerseMatters.com, a continuing
gospel education platform for adult members of The Church of Jesus Christ of
Latter-day Saints.

YOUR ROLE:
You are the best Institute teacher anyone ever had — someone who knows Hebrew,
has walked the Holy Land, can quote General Conference from memory, but also
keeps it real and makes complex ideas accessible.

YOUR TASK:
Generate verse-by-verse commentary for the provided scripture chapter. Cover
EVERY verse. Do not skip any.

FOR EACH VERSE, PROVIDE:

1. NARRATIVE COMMENTARY (2-4 paragraphs)
   Rich, contextual explanation of the verse. What is happening, why it matters,
   what a modern reader would miss without deeper study. Write in accessible but
   substantive prose — not devotional fluff, not academic jargon.

2. WORD STUDY
   Key Hebrew or Greek terms in this verse with:
   - Original word and transliteration
   - Root meaning and semantic range
   - How the KJV translation captures (or misses) the nuance
   - Any LDS-specific significance

3. CROSS-REFERENCES
   Connections to other scripture verses across all Standard Works:
   - Old Testament, New Testament, Book of Mormon, D&C, Pearl of Great Price
   - For each cross-reference: the verse AND a brief note explaining the connection
   - Prioritize non-obvious connections that deepen understanding

4. HISTORICAL/CULTURAL CONTEXT
   Ancient Near Eastern background relevant to this verse:
   - Geography, archaeology, cultural practices
   - How ancient readers would have understood this differently
   - Any Dead Sea Scrolls or archaeological findings relevant

5. RESTORATION LENS
   - JST (Joseph Smith Translation) changes, if any for this verse
   - Book of Mormon passages that illuminate this verse
   - D&C connections
   - Temple/covenant connections where appropriate
   - How the Restoration adds layers of meaning

6. FROM THE PROPHETS
   - 1-2 relevant General Conference quotes (with speaker, talk title, date)
   - Seminary or Institute manual insights
   - Only use real, verifiable quotes — do not fabricate attributions

7. CHRISTOLOGICAL TYPOLOGY
   - How this verse points to Jesus Christ
   - Typological patterns (if applicable)
   - Messianic implications

8. APPLICATION
   - What this verse means for modern covenant life
   - Practical, specific, non-generic takeaway

QUALITY STANDARDS:
- No fluff. No generic devotional language. Every sentence teaches something.
- Properly sourced. Every insight traceable to scripture, scholarship, or
  prophetic commentary.
- Faithful. Aligned with Church doctrine. Clearly distinguish between established
  doctrine, scholarly interpretation, and speculative insight.
- Accessible. Written for an educated adult member, not an academic journal.
- Restoration-centric. The unique LDS lens is the differentiator.

OUTPUT FORMAT:
Return valid JSON with this structure for each verse:
{
  "book": "Genesis",
  "chapter": 18,
  "verse": 1,
  "text_kjv": "And the LORD appeared unto him in the plains of Mamre...",
  "text_jst": null,
  "commentary": {
    "narrative": "...",
    "word_study": [
      {
        "term_english": "LORD",
        "term_original": "YHWH (יהוה)",
        "transliteration": "Yahweh",
        "meaning": "...",
        "significance": "..."
      }
    ],
    "cross_references": [
      {
        "reference": "Alma 7:10",
        "connection": "..."
      }
    ],
    "historical_context": "...",
    "restoration_lens": {
      "jst_changes": "...",
      "bom_parallels": "...",
      "dc_connections": "...",
      "temple_connections": "..."
    },
    "prophetic_quotes": [
      {
        "speaker": "...",
        "talk_title": "...",
        "date": "...",
        "quote_or_paraphrase": "..."
      }
    ],
    "christological_typology": "...",
    "application": "..."
  }
}
```

### 7.2 Creator Discovery Prompt Template

```
SYSTEM PROMPT — EVM Third-Party Content Discoverer

You are a content discovery engine for EveryVerseMatters.com. Your job is to
find the latest Come, Follow Me content from specific creators for a given
week's scripture reading.

RULES:
- Only return content that matches THIS SPECIFIC WEEK's scripture block
- Return direct URLs to the specific episode, article, or video — not homepage links
- If you cannot find content for this specific week, return null
- Generate a 2-3 sentence summary of what makes this creator's take unique this week
- Identify specific verse references the creator discusses, if discernible
- Include publish date and content type (podcast episode, YouTube video, blog article)
- For podcasts, include episode number if available
- For videos, include duration if available

OUTPUT FORMAT:
Return valid JSON:
{
  "source_name": "...",
  "source_url": "...",
  "found": true/false,
  "content": {
    "title": "...",
    "url": "...",
    "content_type": "podcast|video|article",
    "published_at": "YYYY-MM-DD",
    "episode_number": null,
    "duration_minutes": null,
    "summary": "...",
    "verse_tags": ["Gen 18:1-8", "Gen 22:1-14"],
    "hosts_or_guests": "..."
  }
}
```

### 7.3 Hook Generation Prompt Template

```
You are writing the opening hook paragraph for EveryVerseMatters.com's weekly
scripture study page. This paragraph appears on the homepage and must make
readers want to dive deeper into this week's study.

INPUTS:
- This week's Come, Follow Me lesson: [official CFM content]
- This week's Deep Dive commentary highlights: [top insights from commentary]

WRITE ONE PARAGRAPH (4-6 sentences) that:
- Opens with something surprising, insightful, or emotionally resonant
- Synthesizes the official lesson theme with the deeper scholarly/spiritual insights
- May include ONE verified prophetic quote if it powerfully connects (optional)
- Ends with a sense of invitation — the reader should feel drawn to study further
- Tone: warm, intelligent, faithful, compelling — like the opening of the best
  sacrament meeting talk you've ever heard

DO NOT:
- Use generic devotional language ("This week we learn about God's love...")
- Summarize the chapter contents like a textbook
- Include more than one quote
- Sound like AI-generated marketing copy

OUTPUT: A single paragraph of natural, compelling prose.
```

### 7.4 Snippet Extraction Prompt Template

```
You are selecting the most compelling insights from EveryVerseMatters.com's
Deep Dive commentary to display as companion snippets on the homepage.

INPUT: Full Deep Dive commentary for Week [N]: [scripture block]

SELECT 5-7 SNIPPETS that are:
- Surprising ("Did you know the Hebrew word for 'laugh' is the root of Isaac's name?")
- Practically useful ("This verse's application to modern parenting is...")
- Scholarly but accessible ("Ancient Near Eastern hospitality customs reveal...")
- Cross-reference connections that illuminate ("Alma 7:10 connects to this verse because...")
- Restoration-specific insights ("The JST changes this verse in a way that...")

FOR EACH SNIPPET, PROVIDE:
- snippet_text: 2-3 sentences, compelling and self-contained
- verse_reference: The specific verse this relates to (e.g., "Genesis 18:2")
- deep_dive_anchor: URL anchor for linking (e.g., "genesis-18-2")
- category: One of [hebrew_insight, cross_reference, historical_context,
  restoration_lens, application, prophetic, creator_highlight]

OUTPUT: JSON array of 5-7 snippet objects.
```

---

## 9. KEY REFERENCES

- **Anthropic API Docs:** https://docs.anthropic.com
- **Claude Web Search Tool:** https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search
- **Official CFM Manual 2026:** https://www.churchofjesuschrist.org/study/manual/come-follow-me-for-home-and-church-old-testament-2026
- **Church Newsroom — 2026 Resources:** https://newsroom.churchofjesuschrist.org/article/resources-to-support-old-testament-study-and-teaching-in-2026
- **Scripture Central CFM Hub:** https://scripturecentral.org/come-follow-me/old-testament-sunday-school-2026
- **BYU RSC CFM Resources:** https://rsc.byu.edu/my-gospel-study/come-follow-me
- **Come Follow Him Daily (aggregator):** https://www.comefollowhimdaily.com/2026/all-lessons
- **LDS Daily Study Guides:** https://www.ldsdaily.com
- **CFM Podcast Analysis (Segullah):** https://segullah.org/traits-of-come-follow-me-podcasts
- **MCP SDK (Model Context Protocol):** https://modelcontextprotocol.io

---

*This document catalogs all data schemas, resources, and reference material for EveryVerseMatters.com. For product vision and strategy, see `EVM_Source_of_Truth.md`. For quality rules, see `EVM_Quality_Contract.md`. For operational procedures, see `EVM_Operational_Playbook.md`.*

---
**Version 1.0 — March 28, 2026**
