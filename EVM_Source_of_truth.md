# EVM_Source_of_Truth.md
## EveryVerseMatters.com — Source of Truth

**Owner:** Aaron Blonquist
**PM:** Claude (Opus 4.6) — via claude.ai for strategy/research, via API for automated production
**Created:** February 22, 2026
**Last Updated:** April 4, 2026
**Version:** 2.1

---

### System Reference

| Document | Question It Answers | Path |
|----------|---------------------|------|
| **Source of Truth** (this document) | What are we building and why? | `EVM_Source_of_Truth.md` |
| **Data Reference** | What data/resources exist and how do we use them? | `EVM_Data_Reference.md` |
| **Quality Contract** | What must be true for output to be correct? | `EVM_Quality_Contract.md` |
| **Operational Playbook** | How do we actually do the work? | `EVM_Operational_Playbook.md` |

---

## Current State

- **Deployed:** everyversematters.com live with Weeks 3-15 content (including Easter Special Week).
- **Pipeline:** 10-stage automated pipeline via GitHub Actions. Runs every Saturday 4:00 AM MT. Zero human intervention.
- **Special Weeks:** Thematic commentary path implemented and deployed for Easter (Week 14). Christmas (Week 52) will follow same pattern.
- **Quality:** Anti-hallucination hardened — 3-layer system (prompt + reference verification + Haiku audit). All prophetic quotes verified or stripped.
- **Translations:** Multi-translation deep dive: KJV + JST + TCR tabs per verse. TCR covers the full Old Testament (39 books, all chapters).
- **Next milestone:** Week 16 automated run — Exodus 14-18 (Crossing the Red Sea).
- **Repos:** EVM: `github.com/bashonda2/every-verse-matters` | TCR: `github.com/bashonda2/the-covenant-rendering`

---

## 1. PRODUCT VISION

### What It Is
EveryVerseMatters.com (EVM) is a continuing gospel education platform for adult members of The Church of Jesus Christ of Latter-day Saints. It provides deep, verse-by-verse scripture commentary powered by AI, aggregated alongside the best third-party content from dozens of Come, Follow Me (CFM) creators, all running parallel to the official Church curriculum.

### The Problem
- The Church's CES program (Seminary, Institute) effectively ends at age 35
- Come, Follow Me has become the centerpiece of member scripture study since 2019
- Dozens of podcasts, blogs, and YouTube channels produce CFM content weekly — no single member can consume it all
- Each creator brings a specialty but nobody synthesizes ALL dimensions for every verse
- The Old Testament (2026 curriculum) is where members struggle most and need the deepest support

### The Solution
One destination where members go each week and find:
1. **AI-Generated Verse-by-Verse Commentary** — deep, faithful, properly sourced narrative for every single verse in the week's reading
2. **Aggregated Third-Party Content** — cataloged, indexed by verse, with links and attribution to every major CFM creator
3. **Official Curriculum** — the Church's own CFM manual content running as the backbone

### Three-Tier Content Architecture

EVM delivers content through three tiers, each serving a different reader need:

**Tier 1: The Homepage — "Weekly Feed"**
A single scrolling page with one section per week (52 weeks). Each week's section contains:
- **Hook Paragraph** — A Claude-generated opening paragraph (Sonnet or Opus quality) that synthesizes the official CFM lesson and the Deep Dive content into something compelling, insightful, and attention-getting. This is NOT a dry summary — it's the opening 30 seconds of the best Gospel Doctrine teacher's lesson. May include a verified prophetic quote that connects to the week's theme. Purpose: make the reader say "I need to study this week."
- **Two-Column Layout:**
  - **Left Column: Official Curriculum** — Key questions, study prompts, and themes from the Church's Come, Follow Me manual for that week. Links to churchofjesuschrist.org.
  - **Right Column: Curated Companion Content** — 5-7 bite-sized insights extracted by Claude from the Deep Dive page. Each snippet is 2-3 sentences, tied to a specific verse or theme, designed to surprise or enlighten. Each links to the exact verse on the Deep Dive page. These are the most interesting, surprising, or practically useful insights — the "wait, really?" moments that drive click-through.

**Tier 2: The Deep Dive Page**
The full verse-by-verse commentary for each week. Every word study, every cross-reference, every Restoration Lens section, every prophetic quote (verified), every application. This is the serious study destination — linked from companion snippets on the homepage. URL pattern: `everyversematters.com/deep-dive/2026/week-{nn}`

**Tier 3: User-Facing AI (Future — Phase 2+)**
A chat interface where members ask questions grounded in the Deep Dive content database. Powered by the same MCP server. Every response passes through the dual-pass safety audit. (See Quality Contract for guardrail details.)

**Content Flow:**
```
Deep Dive (Tier 2) is generated FIRST by the pipeline
    ↓
Homepage content (Tier 1) is generated FROM the Deep Dive
    - Hook paragraph synthesizes Deep Dive + official CFM
    - Companion snippets are extracted from Deep Dive highlights
    ↓
User-Facing AI (Tier 3) answers questions FROM the Deep Dive database
```

The Deep Dive is the engine. The Homepage is the storefront. The AI is the concierge.

### Why AI Is the Differentiator
For any single verse, Claude can simultaneously synthesize:
- Hebrew/Greek root words and translation nuances
- Ancient Near Eastern cultural and historical context
- Cross-references across all four Standard Works (OT, NT, BoM, D&C, PoGP)
- Decades of General Conference addresses referencing that verse
- JST (Joseph Smith Translation) revisions
- Dead Sea Scrolls and relevant archaeological scholarship
- Typological and Christological layers unique to the Restoration
- Seminary/Institute manual insights
- Geographic and archaeological context

No single human content creator can cover all these dimensions in a weekly production cycle. EVM can — for every verse, every week.

### Why Automation Is Required
The third-party content layer — links, episode titles, summaries, URL verification — changes every single week. Creators publish new episodes, URLs shift, new podcasts launch, old ones go dark. This cannot be maintained manually. The entire content pipeline is automated end-to-end through GitHub Actions and Python scripts that call the Claude API — zero human intervention for standard weekly production. See Operational Playbook for pipeline details.

### The Name
"Every Verse Matters" is a conviction, a mission, and a brand:
- **It's a belief statement** that resonates with how Latter-day Saints approach scripture
- **It's the product** — verse-by-verse depth, nothing skipped
- **It's curriculum-proof** — works whether CFM exists or not
- **It scales** — OT, NT, BoM, D&C, PoGP, General Conference... every verse matters

### Target Audience
- Active Latter-day Saint adults (35+) who have aged out of Institute
- Gospel Doctrine teachers preparing weekly lessons
- Seminary/Institute teachers looking for supplemental depth
- Return missionaries wanting to continue deep study
- Anyone doing Come, Follow Me who wants more than surface-level study

### User-Facing AI Experience
Members don't just read EVM — they interact with it. A chat interface on the site allows users to ask questions grounded in EVM's curated content database. Example queries:
- "Help me prepare a 20-minute Gospel Doctrine lesson on Abraham and Isaac"
- "My teenager is struggling with faith — which verses this week speak to doubt?"
- "What are the Hebrew wordplays in Genesis 22 that don't translate into English?"
- "Compare what Scripture Central and Follow Him said about the Abrahamic covenant"
- "I'm a visual learner — summarize Genesis 18 as a narrative timeline"

The AI is powered by the same MCP server that runs the content pipeline, ensuring consistency between the published commentary and the interactive experience. All responses are grounded in EVM's content database first, then scripture and official sources — never ungrounded speculation. Every response passes through the real-time dual-pass audit system (see Quality Contract).

User queries are logged anonymously and analyzed to:
- Identify what members need most from scripture study
- Surface questions the official manual doesn't address
- Discover new features and content formats the audience wants
- Continuously improve the AI's responses and the commentary itself

This transforms EVM from a content site into a living study platform that gets smarter with every interaction.

### Historical Inspiration
The platform carries the spiritual legacy of the School of the Prophets (D&C 88), established by Joseph Smith in Kirtland, Ohio in 1833 — the Church's first adult continuing education program where leaders studied theology, Hebrew, history, and the mysteries of the kingdom. EVM is a modern digital continuation of that tradition.

---

## 2. 2026 CURRICULUM — COME, FOLLOW ME: OLD TESTAMENT

### Full Weekly Schedule

| Week | Dates | Scripture Block | Theme/Title |
|------|-------|----------------|-------------|
| 1 | Dec 29 – Jan 4 | Introduction to the Old Testament | Introduction |
| 2 | Jan 5–11 | Moses 1; Abraham 3 | God's Work and Glory |
| 3 | Jan 12–18 | Genesis 1–2; Moses 2–3; Abraham 4–5 | The Creation |
| 4 | Jan 19–25 | Genesis 3–4; Moses 4–5 | The Fall |
| 5 | Jan 26 – Feb 1 | Genesis 5; Moses 6 | Teach These Things Freely unto Your Children |
| 6 | Feb 2–8 | Moses 7 | Enoch and Zion |
| 7 | Feb 9–15 | Genesis 6–11; Moses 8 | Noah and the Flood |
| 8 | Feb 16–22 | Genesis 12–17; Abraham 1–2 | The Abrahamic Covenant |
| 9 | Feb 23 – Mar 1 | Genesis 18–23 | Sarah and Isaac |
| 10 | Mar 2–8 | Genesis 24–33 | Jacob and Esau |
| 11 | Mar 9–15 | Genesis 37–41 | Joseph in Egypt (Part 1) |
| 12 | Mar 16–22 | Genesis 42–50 | Joseph in Egypt (Part 2) |
| 13 | Mar 23–29 | Exodus 1–6 | Moses and the Burning Bush |
| 14 | Mar 30 – Apr 5 | Easter | Easter |
| 15 | Apr 6–12 | Exodus 7–13 | The Plagues and Passover |
| 16 | Apr 13–19 | Exodus 14–18 | Crossing the Red Sea |
| 17 | Apr 20–26 | Exodus 19–20; 24; 31–34 | The Ten Commandments |
| 18 | Apr 27 – May 3 | Exodus 35–40; Leviticus 1; 4; 16; 19 | The Tabernacle and Sacrifice |
| 19 | May 4–10 | Numbers 11–14; 20–24; 27 | Wandering in the Wilderness |
| 20 | May 11–17 | Deuteronomy 6–8; 15; 18; 29–30; 34 | Moses's Final Words |
| 21 | May 18–24 | Joshua 1–8; 23–24 | Joshua and the Promised Land |
| 22 | May 25–31 | Judges 2–4; 6–8; 13–16 | Judges of Israel |
| 23 | Jun 1–7 | Ruth; 1 Samuel 1–7 | Ruth and Hannah |
| 24 | Jun 8–14 | 1 Samuel 8–10; 13; 15–16 | Israel's Kings Begin |
| 25 | Jun 15–21 | 1 Samuel 17–18; 24–26; 2 Samuel 5–7 | David |
| 26 | Jun 22–28 | 2 Samuel 11–12; 1 Kings 3; 6–9; 11 | Solomon and the Temple |
| 27 | Jun 29 – Jul 5 | 1 Kings 12–13; 17–22 | Elijah |
| 28 | Jul 6–12 | 2 Kings 2–7 | Elisha |
| 29 | Jul 13–19 | 2 Kings 16–25 | The Fall of Israel and Judah |
| 30 | Jul 20–26 | 2 Chronicles 14–20; 26; 30 | Righteous Kings |
| 31 | Jul 27 – Aug 2 | Ezra 1; 3–7; Nehemiah 2; 4–6; 8 | Return and Rebuild |
| 32 | Aug 3–9 | Esther | Esther |
| 33 | Aug 10–16 | Job 1–3; 12–14; 19; 21–24; 38–40; 42 | Job |
| 34 | Aug 17–23 | Psalms 1–2; 8; 19–33; 40; 46 | Psalms (Part 1) |
| 35 | Aug 24–30 | Psalms 49–51; 61–66; 69–72; 77–78; 85–86 | Psalms (Part 2) |
| 36 | Aug 31 – Sep 6 | Psalms 102–3; 110; 116–19; 127–28; 135–39; 146–50 | Psalms (Part 3) |
| 37 | Sep 7–13 | Proverbs 1–4; 15–16; 22; 31; Ecclesiastes 1–3; 11–12 | Wisdom Literature |
| 38 | Sep 14–20 | Isaiah 1–12 | Isaiah (Part 1) |
| 39 | Sep 21–27 | Isaiah 13–14; 22; 24–30; 35 | Isaiah (Part 2) |
| 40 | Sep 28 – Oct 4 | Isaiah 40–49 | Isaiah (Part 3) |
| 41 | Oct 5–11 | Isaiah 50–57 | Isaiah (Part 4) — The Suffering Servant |
| 42 | Oct 12–18 | Isaiah 58–66 | Isaiah (Part 5) |
| 43 | Oct 19–25 | Jeremiah 1–3; 7; 16–18; 20 | Jeremiah (Part 1) |
| 44 | Oct 26 – Nov 1 | Jeremiah 31–33; 36–38; Lamentations 1; 3 | Jeremiah (Part 2) |
| 45 | Nov 2–8 | Ezekiel 1–3; 33–34; 36–37; 47 | Ezekiel |
| 46 | Nov 9–15 | Daniel 1–7 | Daniel |
| 47 | Nov 16–22 | Hosea 1–6; 10–14; Joel | Hosea and Joel |
| 48 | Nov 23–29 | Amos; Obadiah; Jonah | Amos, Obadiah, Jonah |
| 49 | Nov 30 – Dec 6 | Micah; Nahum; Habakkuk; Zephaniah | Minor Prophets (Part 1) |
| 50 | Dec 7–13 | Haggai 1–2; Zechariah 1–4; 7–14 | Haggai and Zechariah |
| 51 | Dec 14–20 | Malachi | Malachi |
| 52 | Dec 21–27 | Christmas | Christmas |

### Special Weeks

Three weeks in the 2026 schedule have no sequential chapter assignments — they are **thematic/topical lessons** rather than chapter-block readings. These are classified as **Special Weeks** in the pipeline:

| Week | Title | Type | Key Scriptures |
|------|-------|------|----------------|
| 1 | Introduction to the Old Testament | Introduction | Overview — no specific verses |
| 14 | Easter | Holiday | OT prophecies of Christ: Isaiah 25:8, 53:3-9; Psalms 22:16-18, 69:21, 118:22; Zechariah 9:9, 11:12-13; Daniel 12:2. NT fulfillments paired with each. Restoration: Mosiah 3:7, Alma 7:10-13, D&C 19:15-19, Moses 5:9-12 |
| 52 | Christmas | Holiday | TBD — will follow same pattern as Easter |

**Easter (Week 14)** — "He Will Swallow Up Death in Victory"
The CFM Easter lesson is a standalone thematic lesson that pauses the regular OT reading schedule. It draws on scriptures from across the entire canon — Old Testament prophecies paired with New Testament fulfillments, centered on the Atonement and Resurrection. The lesson also coincides with General Conference weekend (Easter 2026). Primary OT passages: Isaiah 25, Isaiah 53, Psalms 22, 69, 118, Zechariah 9 and 11, Daniel 12. Official lesson: https://www.churchofjesuschrist.org/study/manual/come-follow-me-for-home-and-church-old-testament-2026/14

**Special Week pipeline handling:** When `chapters` is empty but `passages` is populated in `cfm_schedule.json`, the pipeline uses a thematic commentary path with curated passages instead of chapter iteration. All downstream stages work without modification — the output schema is identical. See Operational Playbook for implementation details.

**Content Sources for Special Weeks:** [Church News](https://www.thechurchnews.com/) is a primary source for Special Week content — they publish Easter/Christmas-specific articles, prophetic quote compilations, General Conference coverage, and seasonal devotional content. Creator discovery for Special Weeks should prioritize Church News alongside the standard Tier 1 creators.

---

## 3. CONTENT ARCHITECTURE

### 3.1 Three Content Layers

**Layer 1: Official Curriculum (The Backbone)**
- Source: churchofjesuschrist.org CFM manual
- Weekly lesson title, theme, key questions, and study prompts
- Links to official resources (Old Testament Stories, Gospel Art, Insights from the Apostles videos)
- This is the anchor — everything else wraps around it

**Layer 2: AI Verse-by-Verse Commentary (The Engine — Claude API)**
For every verse in the week's reading, Claude generates:
- **Narrative Commentary** — accessible, faithful prose explaining the verse in context
- **Hebrew/Greek Word Study** — key terms with original language insights
- **Cross-References** — connections across all Standard Works
- **Historical/Cultural Context** — ANE background, geography, archaeology
- **Restoration Lens** — JST revisions, Book of Mormon parallels, D&C connections
- **Prophetic Commentary** — relevant General Conference quotes (properly attributed)
- **Christological Typology** — how the verse points to Jesus Christ
- **Application** — what this means for modern covenant life

**Layer 3: Aggregated Third-Party Content (The Catalog — Claude API + Web Search)**
- Every major CFM creator's weekly output, discovered and cataloged automatically
- Tagged not just by week but by specific verse references where possible
- Direct links back to original content (driving traffic to creators, not replacing them)
- AI-generated summary of each creator's unique contribution that week
- URL verification on every link before publish

### 3.2 Content Hierarchy — Homepage View (Tier 1)

```
HOMEPAGE (single scrolling page, one section per week)
├── Week 9: Sarah and Isaac
│   ├── Hook Paragraph (compelling synthesis, verified quote)
│   ├── TWO COLUMNS:
│   │   ├── LEFT: Official CFM Curriculum
│   │   │   ├── Week title, date range, scripture block
│   │   │   ├── Key study questions from manual
│   │   │   ├── Study prompts
│   │   │   └── Link to churchofjesuschrist.org lesson
│   │   └── RIGHT: Curated Companion Content
│   │       ├── Snippet 1: "Did you know..." + link to Deep Dive verse
│   │       ├── Snippet 2: Hebrew insight + link
│   │       ├── Snippet 3: Cross-reference connection + link
│   │       ├── Snippet 4: Restoration Lens highlight + link
│   │       ├── Snippet 5: Historical context gem + link
│   │       ├── Snippet 6: Application insight + link
│   │       └── Snippet 7: Creator roundup note + link
│   └── "Read the Full Deep Dive →" button
├── Week 10: Jacob and Esau
│   └── [same structure]
└── ... (all 52 weeks)
```

### 3.2b Content Hierarchy — Deep Dive View (Tier 2)

```
DEEP DIVE PAGE — STANDARD WEEK (one per week, linked from homepage)
├── Week Title & Date Range
├── Scripture Block (e.g., "Genesis 18-23")
├── Chapter Navigation (jump links)
├── VERSE-BY-VERSE SECTION
│   ├── Chapter Header (e.g., Genesis 18)
│   │   ├── Chapter Overview (2-3 paragraphs — added context)
│   │   ├── Verse 1 — Full EVM Commentary
│   │   │   ├── Narrative
│   │   │   ├── Word Study (expandable)
│   │   │   ├── Cross-References (expandable)
│   │   │   ├── Restoration Lens (expandable)
│   │   │   ├── From the Prophets (verified quotes only)
│   │   │   ├── Christological Typology (expandable)
│   │   │   └── Application
│   │   ├── Verse 2 — Full EVM Commentary
│   │   └── ...
│   └── ...
├── WEEKLY CREATOR ROUNDUP
│   ├── Scripture Central — summary + link
│   ├── Follow Him — summary + link
│   └── [all other creators]
└── Sources (link to About > Sources page)
```

```
DEEP DIVE PAGE — SPECIAL WEEK (Easter, Christmas, Introduction)
├── Week Title & Date Range (e.g., "Easter — March 30 – April 5")
├── Theme Banner (e.g., "He Will Swallow Up Death in Victory")
├── Thematic Introduction (2-3 paragraphs setting up the week's theme)
├── PASSAGE-BY-PASSAGE SECTION (organized by theme, not chapter order)
│   ├── Theme Group (e.g., "Old Testament Prophecies of Christ")
│   │   ├── Isaiah 25:8-9 — Full EVM Commentary (same schema as standard weeks)
│   │   ├── Isaiah 53:3-5 — Full EVM Commentary
│   │   ├── Psalms 22:16-18 — Full EVM Commentary
│   │   └── ...
│   ├── Theme Group (e.g., "The Fulfillment and the Restoration")
│   │   ├── Mosiah 3:7 — Full EVM Commentary
│   │   ├── D&C 19:15-19 — Full EVM Commentary
│   │   └── ...
│   └── ...
├── WEEKLY CREATOR ROUNDUP (same as standard weeks)
└── Sources
```

**Key principle:** Special Weeks use the same `commentary.json` per-verse schema as standard weeks. The Deep Dive page presentation may group passages thematically, but the underlying data is identical — same narrative, word study, cross-references, restoration lens, prophetic quotes, typology, and application fields. This means all downstream pipeline stages (hooks, snippets, audio, verification, QA) work without any modification.

---

## 4. DESIGN PRINCIPLES

- **Scripture First** — the actual verse text is always visible and prominent
- **Depth on Demand** — narrative commentary visible by default, word studies and cross-references expand on click
- **Creator Attribution** — always link back, always credit, never replace
- **Mobile-First** — most members study on their phones
- **Fast** — static generation, minimal JavaScript, CDN-cached
- **Reverent but Modern** — not churchy clip art, not Silicon Valley minimalism. Think: a beautiful study Bible meets a modern web app.
- **Editorial, Not Technical** — cream/parchment palette, serif typography (Cormorant Garamond), Cinzel small caps labels. Feels like a premium devotional publication, not a tech product. Intentionally accessible to older readers.
- **Light-First** — default theme is light/cream. Dark mode available via toggle. Target audience (35+ adults) is more comfortable with light backgrounds.

---

## 5. MVP DEFINITION

### MVP Scope
- **Homepage** with weekly sections fully built: hook paragraph, two-column layout (official curriculum left, companion snippets right), link to Deep Dive
- **Deep Dive pages** for Weeks 3-15 live with full verse-by-verse commentary (Week 14 is Easter Special Week with thematic passage-based commentary)
- **About page** with Sources section: dynamic, generated from `data/sources_registry.json`, grouped by category. Contact email for feedback.
- All prophetic quotes verified against Source Registry or stripped
- Clean, mobile-responsive design (two columns stack on mobile)
- Deployed to VPS at everyversematters.com
- **Contact:** `contact@everyversematters.com` (forwarded via ImprovMX). TCR uses `contact@thecovenantrendering.com` (forwarded via Namecheap email forwarding). Kept separate to maintain TCR's scholarly independence.

### MVP Pages
1. **Homepage** — Weekly Feed with sections for all weeks, Deep Dive links for weeks with content
2. **Deep Dive: Weeks 3-15** — Full verse-by-verse commentary (Genesis 1-50, Moses 2-8, Abraham 1-5, Exodus 1-13) including Easter Special Week (thematic passage-based)
3. **About** — Mission, historical inspiration, Sources section, contact email
4. **All Weeks** — Schedule/index with content status per week

### What's NOT in MVP
- User accounts / login
- Personal study journal
- Search
- Audio narration
- Email subscriptions
- User-facing AI chat (Phase 2)
- Archive (previous years)
- Mobile app
- Admin dashboard (use JSON logs for now)

---

## 6. MONETIZATION (FUTURE — NOT MVP)

### Phase 1: Free
- All verse-by-verse commentary free and open
- Build audience, build trust, build SEO authority
- Goal: become the go-to study companion for CFM

### Phase 2: Freemium (when audience warrants)
Potential premium features:
- **Audio narration** of verse-by-verse commentary (listen during commute)
- **Downloadable study guides** (PDF per week, formatted for printing)
- **Personal study journal** (save notes, highlights, insights per verse)
- **Historical archive access** (all 4 scripture volumes from previous CFM cycles)
- **AI-powered Q&A** (ask deeper questions about any verse, get Claude-powered answers)
- **Gospel Doctrine teacher prep mode** (lesson outlines, discussion questions, handouts)

### Phase 3: Partnerships
- Affiliate links to recommended books referenced in commentary
- Sponsored by faithful LDS publishers (Deseret Book, BYU RSC, etc.)
- Never ads from non-LDS sources — this is a sacred space

---

## 7. ROADMAP

### Phase 1: Proof of Concept — Hack Week (Feb 22-27, 2026) [COMPLETE]
- Domain secured, SOT created, pipeline built, MCP server built
- Weeks 3-9 content generated and deployed
- Full Astro site with homepage, Deep Dive, About, All Weeks
- Three-tier content architecture, Source Registry, creator discovery
- TCR integration (Genesis), multi-translation deep dive UI
- Anti-hallucination hardening (3-layer system)
- Automated pipeline via VPS cron (later migrated to GitHub Actions)

### Phase 2: Weekly Production (March–April 2026) [IN PROGRESS]
- [x] First fully automated pipeline run — Week 10, Saturday March 7, 2026
- [x] Verify Week 10 output and adjust if needed
- [x] Special Week pipeline implemented and deployed — Easter Week 14 first successful run (March 28, 2026)
- [x] Weeks 3-15 content live (including first Special Week)
- [x] MCP server HTTP transport — live on port 3002, PM2-managed, auth + rate limiting
- [ ] Implement Church News scraping to auto-populate `sources_registry.json` weekly
- [ ] Source Registry populated with 50+ verified prophetic commentary sources
- [ ] Refine hook and snippet prompts based on reader feedback
- [ ] Individual verse pages for SEO (`/genesis/18/1`)
- [ ] Admin dashboard for pipeline monitoring
- [ ] Add search functionality
- [ ] Social media presence (Instagram, Facebook)

### Phase 3: Growth (May–December 2026)
- [ ] Full year of OT content live (52 weeks, both homepage and Deep Dive)
- [ ] User-facing AI chat live on site (grounded in Deep Dive, audited by Haiku)
- [ ] Email subscription for weekly content notification
- [ ] Source Registry exceeds 200 verified sources
- [ ] Begin backfilling 2022 OT cycle content
- [ ] Personal study features (highlights, notes)
- [ ] Audio narration exploration (TTS on Deep Dive commentary)
- [ ] Individual verse pages for SEO (`/genesis/18/1`) — dedicated URL per verse for deep search indexing
- [ ] Backfill full verse-by-verse commentary for Weeks 1-8 via Anthropic Batch API (50% discount)
- [ ] SEO optimization — target top-3 for verse-specific searches

### Phase 4: Multi-Year Platform (2027+)
- [ ] 2027 curriculum support (New Testament)
- [ ] Full four-year scripture rotation coverage
- [ ] Premium tier launch
- [ ] Mobile app consideration
- [ ] Community features (discussion, sharing)

---

## 8. OPEN QUESTIONS

1. **Content Review Workflow:** For MVP, Aaron reviews JSON files directly. Future: simple admin page that shows flagged verses with approve/edit/reject buttons.
2. **Third-Party Content Permissions:** Linking and summarizing is standard fair use. No embedded content. Include "not affiliated" disclaimer on every page.
3. **Church Trademark Compliance:** Cannot use official Church logos. Must include "not affiliated with The Church of Jesus Christ of Latter-day Saints" disclaimer.
4. **Commentary Versioning:** When prompts improve, re-run pipeline for historical weeks. Track `generated_by` model version in each commentary entry.
5. **Multiple Translations:** KJV is the standard for LDS use. Three translations displayed per verse: KJV (always), JST (when revision exists), TCR (Genesis, authored by Aaron, CC-BY-4.0). See Quality Contract for output rules.
6. **Backfill Strategy:** Weeks 1-8 have rich summaries. Full verse-by-verse backfill via Batch API (50% discount) planned for Phase 2.
7. **Rate Limits:** Monitor Anthropic API rate limits. If weekly pipeline exceeds limits, stagger chapter generation across multiple hours.
8. **Chat Widget Technology:** Custom React component for full control over UX and guardrails.
9. **User Session Management:** Anonymous sessions with no login for MVP. Track sessions via cookie/local storage for conversation continuity. No PII collected.
10. **Rate Limiting:** Need per-session and per-IP rate limits on the user-facing AI to prevent abuse and manage API costs. Suggested: 20 queries per session, 50 per IP per day for free tier.
11. **Companion Snippet Count:** 5-7 per week is the target. Test whether readers prefer fewer (3-4 high-impact) or more (8-10 comprehensive). A/B test in Phase 2.
12. **Source Registry Initial Population:** Priority is General Conference talks cited in Week 9 commentary. Then expand to all CFM creator URLs. Then scholarly sources. Target: 50 verified sources before Week 10 publishes.
13. **Mobile Two-Column Behavior:** Two columns should stack on mobile (official curriculum on top, companion content below). Or should they tab? Test with family feedback.
14. **Homepage Scroll vs Pagination:** For 52 weeks of content, infinite scroll may be too long. Consider showing only current week + 2 previous + 2 upcoming, with "Show All Weeks" expanding. Or use pagination.

### Resolved Decisions

- **Astro vs Next.js** → **Astro.** Chosen for MVP. Static generation, simpler, no server needed. Next.js migration deferred to Phase 3+ if user accounts or server-side features are required.
- **Hook Paragraph Model** → **Claude Sonnet.** Sufficient quality at far lower cost than Opus. One paragraph per week makes cost difference negligible either way. Resolved Week 9.
- **Prophetic Quote Accuracy** → **Three-layer system implemented.** See Quality Contract for details.
- **Deep Dive URL Structure** → `everyversematters.com/deep-dive/2026/week-9` — keeps Deep Dive as its own section for cleaner SEO.

---

## 9. DISCLAIMER (Required on Site)

> EveryVerseMatters.com is an independent study resource and is not affiliated with, endorsed by, or sponsored by The Church of Jesus Christ of Latter-day Saints. Come, Follow Me is a trademark of Intellectual Reserve, Inc. All commentary is AI-generated and should be used as a supplemental study aid, not as authoritative doctrinal interpretation. Third-party content is linked with attribution; all rights remain with the original creators.

---

## Change Log

| Date | Summary |
|------|---------|
| 2026-04-04 | Week 15 deployed (Exodus 7-13, 155 verses, QA 0% flagged). Anthropic API key rotated. Full OT TCR data (34 new books) added to pipeline — TCR context now available for all 52 weeks. |
| 2026-03-28 | SOT restructured into 4-document architecture (SOT, Data Reference, Quality Contract, Operational Playbook). Special Week pipeline implemented and deployed for Easter Week 14. |
| 2026-03-07 | First fully automated GitHub Actions pipeline run (Week 10). Pipeline migrated from VPS cron. |
| 2026-02-23 | TCR integration complete (Genesis, 50 chapters). Multi-translation deep dive UI live. MCP HTTP transport deployed. Anti-hallucination hardening shipped. |
| 2026-02-22 | Hack Week complete. Site live at everyversematters.com. Weeks 3-9 content, full pipeline, MCP server, Astro frontend, Source Registry. |

---

*This document is the constitution for EveryVerseMatters.com. It answers "what are we building and why?" For data schemas and resources, see `EVM_Data_Reference.md`. For quality rules, see `EVM_Quality_Contract.md`. For operational procedures, see `EVM_Operational_Playbook.md`.*

---
**Version 2.1 — April 4, 2026**
