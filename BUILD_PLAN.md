# BUILD PLAN — Loop-Closing Agent ("Agents for Humans" Hackathon)

> **Audience:** the builder + any AI coding agent assisting them.
> **Format note:** every task has an ID, an explicit acceptance criterion, and a
> hard cut rule. An agent picking this up mid-build should read §0 → §3 → find the
> lowest unchecked task ID → execute → verify against its acceptance criterion.

---

## 0. FIXED CONTEXT (do not re-litigate)

| Field | Value |
|---|---|
| Hackathon | Agents for Humans (AWS / Devpost) |
| Track | **Professional Agents** |
| Deadline | **2026-09-14, 17:00 PDT** |
| Build window | 5 working days |
| Target internal freeze | End of Day 4 (feature freeze); Day 5 = video + submission |
| Language | **Python only** |
| Required framework | **Strands Agents SDK (Python)** |
| Model provider | Amazon Bedrock (Claude) |
| Deployment | Amazon Bedrock AgentCore (scores extra on Technical Implementation) |
| Credits | $50 AWS — reserve for Bedrock inference + AgentCore. **Do not spend on infra.** |
| License | MIT or Apache-2.0, visible in repo About section |

### Judging criteria (build decisions must map to these)

1. **Technological Implementation** — how thoroughly and skilfully Strands Agents is used; live demo and/or AgentCore deployment strengthens this.
2. **Design** — a complete, coherent product experience, not a proof of concept.
3. **Potential Impact** — credible, specific case for a real audience, demonstrated.
4. **Creativity & Originality** — non-obvious use of Strands; genuine understanding of the problem space.
5. **Presentation** — video clearly shows the thing working end to end.

### Deliverables checklist (all required)

- [ ] Text description (problem / who it's for / how it works)
- [ ] **Public** repo, MIT or Apache-2.0, README, setup instructions
- [ ] Architecture diagram
- [ ] Demo video, **max 5 minutes**
- [ ] AWS Builder ID
- [ ] (Optional, scores higher) Live demo link
- [ ] (Bonus points) Post on builder.aws.com with "Agents for Humans" in the title, published before deadline

---

## 1. THE PRODUCT (one paragraph, memorise this)

Commitments are made out loud in meetings and in email — "I'll send the revised
scope Thursday", "we'll confirm the vendor date by end of week" — and then nobody
owns the gap between the promise and its resolution. There is no error message
for something that simply didn't happen. This agent listens to meetings, extracts
every commitment as a tracked **loop**, watches for evidence that each one actually
closed, and when a loop goes past its window it chases the responsible party by
email. Critically, it **reads the reply and decides what the reply actually meant**:
closed, deferred, transferred to someone else, disputed, or ambiguous. A deferral
spawns a child loop. A transfer re-points the loop at a new owner and carries the
history across. A claimed closure is verified against a system of record before it
is believed. Over time this produces a reliability record for every counterparty.

**One-line pitch:** *An agent that owns the space between "I'll get back to you" and
whether anyone ever did.*

---

## 2. LOCKED DECISIONS

### 2.1 Persona (LOCKED — swap only via §2.6)

**Delivery / account manager at a small agency or consultancy.**

Justification:
- 6–12 client, vendor and internal calls a week; commitments in both directions are made verbally and never ticketed.
- Counterparties are reachable by ordinary email — the pursuit loop is real, not simulated.
- No PHI, no HIPAA, no regulated data, no fake portal.
- Missed loops have visible cost: slipped deliverables, lapsed approvals, blown client trust.
- The reliability scorecard has an obvious buyer here ("which of our vendors actually hold dates").

Demo scenario to build around: a delivery manager running a client project with two
vendors. Three meetings' worth of commitments, one of which quietly goes stale.

### 2.2 Data sources (LOCKED — cap is one opener, two evidence sources, two channels)

| Role | Source | Notes |
|---|---|---|
| Loop-opening | Meeting transcripts | Via **Attendee hosted free tier** (`app.attendee.dev`). Use **closed-caption-based transcription** (free). |
| Loop-opening (fallback) | Pasted `.vtt` / `.txt` transcript file | Built FIRST. Never removed. |
| Closure evidence | Inbound email (attachments, content) | |
| Closure evidence | Google Sheet acting as the counterparty's system of record | e.g. a shared deliverables tracker |
| Pursuit | Outbound email | Primary channel |
| Pursuit | Telegram bot | Secondary channel; proves *channel switching* as a strategy |

**Email transport decision:** dedicated Gmail account + **IMAP polling (read) and SMTP
(send)** using an App Password with 2-Step Verification enabled. No OAuth consent
screen, no domain purchase, no public webhook endpoint, no DNS.
→ **Verify App Passwords still work for your account type on Day 1 (task D1-T2).**
→ Fallbacks if blocked: Zoho Mail free tier (IMAP/SMTP), or Resend/Postmark inbound
(requires a domain).

### 2.3 Architecture principle (LOCKED)

**The agent is transcript-shaped, not Attendee-shaped.**

All ingestion adapters normalise to one internal structure:

```python
# core/models.py
class Utterance(BaseModel):
    speaker: str
    speaker_email: str | None
    timestamp: float          # seconds from meeting start
    text: str

class MeetingTranscript(BaseModel):
    meeting_id: str
    title: str
    occurred_at: datetime
    participants: list[Participant]   # name + email
    utterances: list[Utterance]
```

`FileAdapter` and `AttendeeAdapter` both emit `MeetingTranscript`. Nothing downstream
knows or cares which one ran. **If Attendee breaks on demo day, the product still works.**

### 2.4 UI decision (LOCKED)

**Streamlit.** Chosen for speed given a Python-new builder. Cost: less design polish
than a hand-built page, and Design is a judged criterion — so §6 includes a mandatory
styling pass. Do not substitute FastAPI + a hand-rolled frontend; it will eat Day 4.

### 2.5 Naming

Working name: **`Latch`**. Repo name `latch`. Do not use "loop registry" or
"accountability infrastructure" in any public copy — those describe the architecture,
not the user's problem.

### 2.6 Persona swap protocol

If the persona must change, only §2.1 and the seed data in `demo/seed.py` may change.
Every other section stays. Do not restart.

---

## 3. ARCHITECTURE

```
                    ┌───────────────────────────────────┐
                    │        INGESTION ADAPTERS          │
                    │  FileAdapter  |  AttendeeAdapter   │
                    └───────────────┬───────────────────┘
                                    │  MeetingTranscript
                                    ▼
        ┌────────────────────────────────────────────────────┐
        │  AGENT 1: EXTRACTOR  (Strands, structured_output)   │
        │  transcript → list[Loop]                            │
        │  captures: promise, owner, window (stated|inferred),│
        │            closure_criterion, stakes, source_quote  │
        └───────────────┬────────────────────────────────────┘
                        ▼
        ┌────────────────────────────────────────────────────┐
        │              LEDGER (SQLite)                        │
        │  loops · events · counterparties · reliability       │
        └───────────────┬────────────────────────────────────┘
                        │  (scheduler tick: window lapsed?)
                        ▼
        ┌────────────────────────────────────────────────────┐
        │  AGENT 2: PURSUER  (Strands, tools + reasoning)     │
        │  TOOLS: check_sheet_record, check_inbox_for_evidence,│
        │         search_prior_thread, draft_followup,         │
        │         send_email, send_telegram, escalate_to_human │
        │  Chooses strategy from state: touch count, prior     │
        │  deferrals, counterparty reliability, channel history│
        └───────────────┬────────────────────────────────────┘
                        │  reply arrives (IMAP poll)
                        ▼
        ┌────────────────────────────────────────────────────┐
        │  AGENT 3: ADJUDICATOR  (Strands, structured_output) │
        │  reply → {verdict, confidence, evidence_span,        │
        │           new_owner?, new_commitment?}               │
        │  verdict ∈ CLOSED | DEFERRED | TRANSFERRED |         │
        │            DISPUTED | AMBIGUOUS                      │
        │  CLOSED claims → must pass verification tool         │
        │  DEFERRED     → spawn child loop                     │
        │  TRANSFERRED  → re-target + carry history            │
        │  AMBIGUOUS / low confidence → escalate to human      │
        └───────────────┬────────────────────────────────────┘
                        ▼
              ┌──────────────────────────────┐
              │  STREAMLIT REVIEWER UI        │
              │  worklist · loop tree ·       │
              │  drafts · reliability board   │
              └──────────────────────────────┘
```

### 3.1 Why this is not a thin pipeline (say this in the video)

- The Adjudicator makes a **judgement under ambiguity** and can decline to decide.
- Loops form a **tree** — deferrals spawn children, so state accumulates and changes future behaviour.
- The Pursuer **re-plans** when a counterparty transfers ownership, which was not anticipated at extraction time.
- Strategy is **selected from state**, not a fixed template ladder. Same loop, different history, different action.
- Closure claims are **verified against a record**, not believed.

### 3.2 Monorepo layout (LOCKED)

Single public repo. Backend, AI/agents, shared domain code, and frontend all live
here. Three top-level units, one shared package, one virtualenv.

```
latch/                                  # ← the monorepo root; this is the public repo
├── README.md                         # root README is what judges read first
├── LICENSE                           # MIT
├── ARCHITECTURE.md
├── architecture.png
├── Makefile                          # single entrypoint for every command
├── pyproject.toml                    # workspace root; dev tooling config
├── .env.example                      # ONE env file for the whole repo
├── .gitignore
│
├── packages/
│   └── core/                         # SHARED domain layer — no I/O, no agents
│       ├── pyproject.toml
│       └── src/latch_core/
│           ├── __init__.py
│           ├── models.py             # Loop, Utterance, MeetingTranscript, Verdict, LoopEvent
│           ├── ledger.py             # SQLite CRUD + loop-tree helpers
│           ├── priority.py           # computed priority score (§4)
│           └── config.py             # env loading, paths
│
├── services/
│   └── agent/                        # BACKEND + AI — the only deployable unit
│       ├── pyproject.toml
│       ├── Dockerfile                # for AgentCore
│       ├── requirements.txt          # deployment deps only, NOT the UI's
│       └── src/latch_agent/
│           ├── __init__.py
│           ├── agents/
│           │   ├── extractor.py      # Strands Agent 1
│           │   ├── pursuer.py        # Strands Agent 2
│           │   └── adjudicator.py    # Strands Agent 3
│           ├── tools/
│           │   ├── email_tools.py    # IMAP read, SMTP send
│           │   ├── sheet_tools.py    # Google Sheets record check
│           │   ├── telegram_tools.py
│           │   └── ledger_tools.py
│           ├── ingest/
│           │   ├── base.py           # Adapter protocol
│           │   ├── file_adapter.py   # .vtt / .txt  ← BUILD FIRST
│           │   └── attendee_adapter.py
│           ├── scheduler.py          # tick loop: find lapsed → invoke Pursuer
│           └── main.py               # AgentCore entrypoint
│
├── apps/
│   └── reviewer/                     # FRONTEND — Streamlit
│       ├── pyproject.toml
│       ├── .streamlit/config.toml    # theme — see D4-T2
│       └── src/latch_reviewer/
│           ├── app.py                # entrypoint
│           ├── views/
│           │   ├── worklist.py
│           │   ├── loop_detail.py
│           │   └── reliability.py
│           └── components/
│               ├── status_pill.py
│               ├── loop_tree.py
│               └── evidence_span.py  # highlighted adjudication evidence
│
├── demo/
│   ├── transcripts/                  # 3 hand-written transcripts
│   ├── seed.py                       # inserts PRE-AGED loops
│   └── DEMO_SCRIPT.md
│
├── tests/
│   ├── test_extractor.py
│   ├── test_adjudicator.py           # the 12 reply fixtures — see D3-T3
│   └── test_ledger.py
│
└── docs/
    └── adr/                          # 3–5 short decision records (see §3.4)
```

**Dependency direction is one-way and must stay that way:**

```
apps/reviewer  ──┐
                 ├──►  packages/core
services/agent ──┘
```

`packages/core` imports nothing from `services/` or `apps/`. The frontend never
imports the agent runtime; it reads the ledger. This is what lets you deploy
`services/agent` to AgentCore without dragging Streamlit along.

### 3.3 Monorepo conventions (read before D1-T0)

**One virtualenv at the root.** Do not create a venv per package. That is correct for
a production monorepo and wrong for a five-day build.

**Wire the packages with editable installs.** This is the piece that will be unfamiliar
coming from Maven. From the repo root, once:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e packages/core
pip install -e services/agent
pip install -e apps/reviewer
```

After that, `from latch_core.models import Loop` works from anywhere in the repo,
and edits to `packages/core` are picked up immediately with no reinstall. Never use
`sys.path` hacks or relative imports across top-level units.

**One `.env` at the root.** `packages/core/config.py` loads it. Do not scatter env
files per package; you will lose an hour to a missing variable at 2am.

**One SQLite file at the root** (`latch.db`, gitignored). Both the agent runtime and
the reviewer open it. Enable WAL mode so the Streamlit reader and the scheduler writer
don't lock each other:

```python
conn.execute("PRAGMA journal_mode=WAL;")
```

Do this on Day 1 in `ledger.py`. Discovering `database is locked` while recording the
video is a genuinely bad afternoon.

**Makefile is the only interface.** Every command in this plan should be a target, so
that an agent or a fresh clone never has to guess:

```makefile
install:     ## one-time setup: venv + editable installs
seed:        ## reset db and load pre-aged demo loops
ingest:      ## run FileAdapter over demo/transcripts
run-agent:   ## start the scheduler tick loop
run-agent-fast: ## same, compressed clock for recording
run-ui:      ## streamlit run apps/reviewer/src/latch_reviewer/app.py
test:        ## pytest tests/
demo:        ## seed + ingest + run-agent-fast + run-ui
```

The `demo` target matters most. On recording day you want one command that puts the
whole system into a known state.

**Only `services/agent` is packaged for deployment.** Its `requirements.txt` and
Dockerfile must not include Streamlit, gspread-for-the-UI, or anything the reviewer
needs. Keep the deployment surface small or AgentCore builds get slow and flaky.

**Commit convention.** Prefix every commit with the unit it touches: `core:`,
`agent:`, `reviewer:`, `demo:`, `docs:`. Costs nothing, and a judge skimming your
commit history sees a structured project rather than 60 commits called "fix".

### 3.4 Why a monorepo, and how to say it in 15 seconds

If asked, or in the README: the domain model, the agent runtime, and the reviewer
share one definition of what a loop is. Splitting them across repos would mean
versioning that contract across three places during a five-day build. One repo, one
`packages/core`, one source of truth. The deployable unit is still isolated, so
AgentCore only ever ships the agent runtime.

Write this up as `docs/adr/0001-monorepo.md`, three paragraphs. Add two more ADRs
during the build (0002: transcript-shaped ingestion; 0003: adjudication taxonomy).
Architecture decision records are cheap to write and they read as engineering
maturity under the Design and Technological Implementation criteria.

---

## 4. DATA MODEL

```python
class WindowSource(str, Enum):
    STATED = "stated"        # "by Thursday"
    INFERRED = "inferred"    # "I'll look into it" → default by commitment type

class LoopStatus(str, Enum):
    OPEN = "open"
    AWAITING_REPLY = "awaiting_reply"
    CLOSED_VERIFIED = "closed_verified"
    CLOSED_CLAIMED = "closed_claimed"      # counterparty says so, unverified
    ESCALATED_TO_HUMAN = "escalated_to_human"
    ABANDONED = "abandoned"

class Loop(BaseModel):
    id: str
    parent_id: str | None            # child loops from deferrals
    promise: str
    source_quote: str                # verbatim, for the UI
    source_meeting_id: str | None
    owner_name: str
    owner_email: str
    counterparty_org: str
    due_at: datetime
    window_source: WindowSource      # SHOW THIS IN THE UI
    closure_criterion: str           # what evidence would count
    stakes: Literal["low","medium","high"]
    status: LoopStatus
    touch_count: int = 0
    deferral_count: int = 0
    channels_tried: list[str] = []
    created_at: datetime
    events: list[LoopEvent] = []
```

**Priority score** (this is the answer to the triage objection — it is *computed*, not asserted):

```
priority = (days_past_window * W1)
         + (stakes_weight * W2)
         + (deferral_count * W3)
         + (touch_count * W4)
         + (counterparty_unreliability * W5)
```

Show the score breakdown on hover/expander in the UI. A judge seeing *why* a loop
is ranked first is worth more than the ranking itself.

---

## 5. ADJUDICATION TAXONOMY (the core IP — implement exactly)

| Verdict | Trigger | Required action |
|---|---|---|
| `CLOSED` | Reply asserts completion | **Verify** via `check_sheet_record` / attachment check. Pass → `CLOSED_VERIFIED`. Fail → `CLOSED_CLAIMED` + flag to human. |
| `DEFERRED` | New promise, no resolution ("looking into it", "by Friday") | Spawn **child loop** with new window (stated or inferred). Parent stays open. `deferral_count += 1`. |
| `TRANSFERRED` | Ownership moved ("forwarded to Dana") | Re-target `owner_email`, write handoff event, generate a **history-carrying** message to the new owner so they don't start from zero. |
| `DISPUTED` | Premise rejected ("we never received it") | Loop failed at an earlier stage. Escalate to human with the correction, do not re-send the same chase. |
| `AMBIGUOUS` | Cannot determine, or confidence < 0.7 | Escalate to human with a drafted clarifying question. **Never guess.** |

Every verdict must return `evidence_span`: the exact substring of the reply the
decision rests on. Render it highlighted in the UI. This is a 10-second video moment
and it makes the agent look accountable rather than magical.

---

## 6. DAY-BY-DAY

### DAY 1 — Foundations + Strands literacy + the un-sinkable path

> Goal by end of day: a hand-written transcript goes in, real Loop rows come out,
> and you can send and read an email from Python.

- [ ] **D1-T0 — Monorepo scaffold (45m).** Create the tree from §3.2, the three `pyproject.toml` files, root venv, three editable installs, root `.env.example`, `.gitignore`, and a Makefile with stub targets. Push the empty structure to GitHub as the first commit, public, MIT.
  - *Accept:* from the repo root, `python -c "from latch_core.models import Loop"` fails only because `models.py` is empty, not because of an import path error. `make install` works from a clean clone.
  - *Do this first.* Retrofitting a monorepo on Day 3 costs three hours and breaks the AgentCore packaging.
- [ ] **D1-T1 — Strands spike (2h).** Build a throwaway agent with two toy tools and one `structured_output` call against Bedrock. Do NOT touch the real project.
  - *Accept:* an agent that calls a tool you wrote and returns a validated Pydantic object.
  - *Note:* Python 3.10+. `pip install strands-agents strands-agents-tools`. Confirm Bedrock model access is enabled in your region before anything else.
- [ ] **D1-T2 — Email transport (2h).** Dedicated Gmail, 2SV on, App Password. `imaplib` read + `smtplib` send.
  - *Accept:* script sends an email to yourself and reads the reply body back within 60s.
  - *If blocked:* switch to Zoho free tier. **Timebox to 2h — do not lose a day here.**
- [ ] **D1-T3 — Ledger (1.5h).** Fill in `packages/core/src/latch_core/models.py` and `ledger.py`. SQLite at the repo root, **WAL mode on** (§3.3). Include `parent_id` and the events table from day one; retrofitting the tree later is painful.
  - *Accept:* create, read, update, and fetch-children all work from a REPL, and a second process can read while the first holds a write connection.
- [ ] **D1-T4 — Demo transcripts (1h).** Write 3 realistic transcripts by hand in `demo/transcripts/`. Include: 2 clearly stated deadlines, 2 vague commitments with no date, 1 commitment made *by* the user (loops run both ways), and 1 near-miss that should NOT be extracted ("we should probably look at that sometime").
  - *Accept:* the negative example exists. Precision matters as much as recall.
- [ ] **D1-T5 — FileAdapter (1h).** `.vtt` and plain-text → `MeetingTranscript`.
  - *Accept:* all 3 transcripts parse.
- [ ] **D1-T6 — Extractor agent (2h).** Strands agent, `structured_output` → `list[Loop]`.
  - *Accept:* correctly extracts the stated-deadline commitments, marks the vague ones `INFERRED`, and does **not** extract the near-miss.

**Day 1 cut rule:** if D1-T6 isn't working by end of day, cut D1-T2 to send-only and finish extraction first. Extraction is the spine.

---

### DAY 2 — Pursuit + scheduler + the first real round trip

> Goal by end of day: a lapsed loop causes a real email to leave your machine.

- [ ] **D2-T1 — Pursuer agent (3h).** Strands agent with tools: `check_sheet_record`, `check_inbox_for_evidence`, `draft_followup`, `send_email`, `send_telegram`, `escalate_to_human`. Prompt it to **choose** and to **state its reasoning**, not to follow a fixed ladder.
  - *Accept:* given two loops with different histories (one fresh, one twice-deferred with email already tried), the agent picks different actions and explains why.
- [ ] **D2-T2 — Sheet tool (1.5h).** Google Sheet as the counterparty's system of record. Service account + `gspread`.
  - *Accept:* `check_sheet_record(loop_id)` returns a real row or `None`.
- [ ] **D2-T3 — Scheduler (1.5h).** `scheduler.py`: tick every N seconds, find loops past `due_at` in state `OPEN`, invoke Pursuer, write events. Add a `--fast` flag that compresses time for demo recording.
  - *Accept:* a loop seeded 3 days overdue triggers a pursuit within one tick.
- [ ] **D2-T4 — Seed script (1h).** `demo/seed.py` inserts pre-aged loops.
  - *Accept:* one command produces a realistic 12-loop worklist with varied ages, stakes and histories.
- [ ] **D2-T5 — First live round trip (1h).** Overdue loop → agent drafts → real email lands in a second inbox.
  - *Accept:* you receive an email that correctly names the promise, the deadline, and quotes the original commitment.

---

### DAY 3 — The Adjudicator (this is the day that wins or loses it)

> Goal by end of day: an unscripted human reply is correctly classified, and a
> deferral spawns a visible child loop.

- [ ] **D3-T1 — IMAP reply matcher (1.5h).** Thread replies back to loops via `Message-ID` / `In-Reply-To`, with a subject-token fallback (`[OVR-a3f9]`).
  - *Accept:* a reply from a phone client (which mangles threading) still matches.
- [ ] **D3-T2 — Adjudicator agent (3h).** Strands + `structured_output` → `{verdict, confidence, evidence_span, new_owner, new_commitment}`. Implement all five verdicts from §5.
  - *Accept:* returns a valid verdict object with a non-empty `evidence_span` for every fixture.
- [ ] **D3-T3 — Adjudication fixtures (1.5h).** `tests/test_adjudicator.py` with at least 12 real-world replies, minimum two per verdict. Include these exact hard cases:
  - "The patient/client was seen on the 14th." → `CLOSED` (then verify)
  - "We're looking into it." → `DEFERRED`, no date → inferred window
  - "I've forwarded this to Dana in scheduling." → `TRANSFERRED`
  - "We never received it." → `DISPUTED`
  - "Yes." → `AMBIGUOUS`
  - "Sorry for the delay, it went out Tuesday." → `CLOSED` claimed, verification must **fail** → `CLOSED_CLAIMED` + human flag
  - *Accept:* ≥10/12 correct. Write down the failures; they're honest material for the README.
- [ ] **D3-T4 — Child loop spawning (1.5h).** `DEFERRED` creates a child with a new window, linked to the parent.
  - *Accept:* the ledger returns a two-level tree and the parent stays open.
- [ ] **D3-T5 — Re-targeting (1.5h).** `TRANSFERRED` re-points the owner and generates a history-carrying message to the new party.
  - *Accept:* the new message contains the original quote, the date, and a summary of what's happened since. The new owner does not start from zero.

**Day 3 cut rule:** if you are behind, cut D3-T5 (re-targeting) before D3-T4 (child loops). The tree is more visible in the video.

---

### DAY 4 — UI, reliability board, AgentCore, Attendee. FEATURE FREEZE AT EOD.

- [ ] **D4-T1 — Streamlit reviewer (3h).** Build out `apps/reviewer/`. Three views, one file each under `views/`, shared widgets under `components/`:
  1. **Worklist** — sorted by computed priority, with an expander showing the score breakdown.
  2. **Loop detail** — timeline of events, the source quote, the drafted intervention, Approve / Edit / Send buttons, and the highlighted `evidence_span` on any adjudicated reply.
  3. **Reliability board** — per-counterparty: loops opened, closed on time, median touches to closure, deferral rate.
  - *Accept:* a stranger can open it and understand what the product does without narration.
- [ ] **D4-T2 — Styling pass (1h).** Non-negotiable; Design is judged. Set a custom Streamlit theme, use one accent colour, consistent status pills, `st.column_config` for tables. Remove every default-looking element.
  - *Accept:* it does not look like a Streamlit tutorial.
- [ ] **D4-T3 — Attendee adapter (2h).** Hosted free tier + closed-caption transcription. Bot joins a real meeting, transcript webhook or poll → `MeetingTranscript` → Extractor.
  - *Accept:* a real 3-minute call you run with a friend produces real extracted loops.
  - **Hard timebox: 2h. If it's not working, ship the FileAdapter and say nothing about it in the video.** The product does not depend on this.
- [ ] **D4-T4 — AgentCore deployment (2h).** Deploy the agent runtime. Keep the Streamlit UI wherever is easiest.
  - *Accept:* a live URL that works from a phone on mobile data.
  - *Cut rule:* if it fights you past 2h, abandon it and record locally. It's a score bonus, not a requirement.
- [ ] **D4-T5 — FEATURE FREEZE.** No new features after this point. Anything unfinished is now a "Roadmap" line in the README.

---

### DAY 5 — Video, repo, submission

- [ ] **D5-T1 — Rehearse (1h).** Run the demo script end to end three times. Fix only what breaks.
- [ ] **D5-T2 — Record (2h).** See §7. Expect 4–6 takes.
- [ ] **D5-T3 — Architecture diagram (45m).** Use §3's ASCII as the source. Excalidraw or draw.io. Export PNG.
- [ ] **D5-T4 — README (1h).** Problem, persona, architecture, adjudication taxonomy table, setup instructions that actually work from a clean clone, honest limitations, roadmap. Add LICENSE and set it in the repo About section.
- [ ] **D5-T5 — builder.aws.com post (1h).** Title must contain "Agents for Humans". Write about the adjudication taxonomy and what the fixtures got wrong — build-journey posts about real failures read better than victory laps. **Must be publicly published before the deadline.**
- [ ] **D5-T6 — Submit (45m).** Devpost form, AWS Builder ID, repo URL, video, diagram, live demo link. **Submit at least 6 hours before the deadline.**

---

## 7. DEMO VIDEO SCRIPT (5:00 hard cap)

State the seeding out loud, once, early. Judges forgive disclosed seeding and
punish discovered seeding.

| Time | Content |
|---|---|
| 0:00–0:35 | **Problem.** A real commitment made out loud in a call. Nobody ticketed it. Nobody owns the gap. Name the persona and the cost. |
| 0:35–1:05 | **Ingestion.** Transcript → extracted loops. Show the `INFERRED` vs `STATED` window badge. Show that the near-miss sentence was correctly *not* extracted. |
| 1:05–1:25 | **Worklist.** "These loops are pre-aged so you can see the state after two weeks — everything from here is live." Open the priority breakdown. |
| 1:25–2:05 | **Pursuit.** Agent picks a loop, states its reasoning, checks the sheet first, finds nothing, drafts, sends. Show the email arriving. |
| 2:05–3:05 | **THE MONEY SHOT.** A real reply comes back: *"We're looking into it, I'll check Friday."* Adjudicator returns `DEFERRED`, highlights the evidence span, spawns a child loop, and the tree appears in the UI. Then a second reply transfers ownership; the agent re-targets and carries the history. |
| 3:05–3:35 | **Verification.** A reply claims it's done. Agent checks the record, finds nothing, marks it `CLOSED_CLAIMED` and flags a human. Say plainly: it does not take their word for it. |
| 3:35–4:15 | **Reliability board.** Per-counterparty closure record built from the run. This is the second-order payoff. |
| 4:15–4:45 | **Architecture.** 20 seconds on Strands: three agents, structured output, tool selection, AgentCore. |
| 4:45–5:00 | **Impact + live link.** "Email this address and watch the agent adjudicate your reply." |

**Recording rules**
- Keep the real inbox and real timestamps on screen during 2:05–3:05. Provenance is the whole point.
- Get the reply from someone who has not seen the script.
- No slide-only stretches longer than 20 seconds.
- Voiceover only. Do not appear on camera. Do not apologise for anything.

---

## 8. STRANDS USAGE — score this criterion deliberately

| Feature | Where used | Why it earns the score |
|---|---|---|
| `Agent` + system prompt | All 3 agents | Baseline |
| `@tool` decorator | 8+ custom tools | Non-trivial tool surface |
| `structured_output` | Extractor, Adjudicator | Typed Pydantic contracts, not string parsing |
| Model-driven tool selection | Pursuer | The agent decides strategy; no hard-coded ladder |
| Multi-agent composition | Extractor → Pursuer → Adjudicator | Distinct roles, distinct prompts, distinct failure modes |
| Sessions / state | Loop history across turns | State accumulates and changes later behaviour |
| MCP (optional, if time) | Any external tool with an existing server | Native SDK feature; cheap points |
| AgentCore | Deployment | Explicitly named as strengthening the score |

Put this table in the README. Make the judge's job easy.

---

## 9. HARD "DO NOT" LIST

- **Do not** build SMS, WhatsApp or voice. Verification delays will sink you.
- **Do not** attempt real-time in-meeting extraction. Post-meeting only.
- **Do not** self-host Attendee. Hosted free tier only.
- **Do not** add a third closure-evidence source. Two is the cap.
- **Do not** build auth, multi-tenancy, or user accounts.
- **Do not** replace Streamlit with a custom frontend. `apps/web/` is a slot for after the hackathon, not during it. A React frontend means a second toolchain, CORS, and an API layer you have not budgeted for.
- **Do not** create a venv per package, add Poetry/PDM workspaces, uv workspaces, Docker Compose for local dev, or a CI pipeline. The monorepo is for code organisation, not for demonstrating build tooling. Editable installs and a Makefile are enough.
- **Do not** let `packages/core` import from `services/` or `apps/`. If you feel the need, the thing belongs in core.
- **Do not** split into more top-level units. Three is the cap.
- **Do not** add features after the Day 4 freeze.
- **Do not** claim in any public copy that nothing like this exists. Referral and follow-up automation is a populated commercial category. Position on the specific mechanic — cross-boundary pursuit of commitments that were never structured tickets — not on emptiness.
- **Do not** use unsourced statistics. If a number goes in the video, it has a citation in the README.
- **Do not** record anyone in a meeting without telling them first.

---

## 10. RISK REGISTER

| Risk | Likelihood | Mitigation | Owner action |
|---|---|---|---|
| Gmail App Password blocked | Medium | Zoho free tier fallback | Test Day 1, 2h timebox |
| Bedrock model access not enabled in region | Medium | Request access first thing | D1-T1, before anything else |
| Attendee bot fails to join | Medium | FileAdapter is the primary path | Timeboxed to 2h on Day 4 |
| Adjudicator accuracy too low | Medium | Fixtures on Day 3 catch it early; low confidence → escalate rather than guess | D3-T3 |
| AgentCore deployment fights back | Medium | Record locally, submit repo without live link | 2h cap |
| Credits exhausted by debugging | Low–Medium | Cache LLM responses during dev; use a cheaper model for iteration, Claude for the recorded run | Day 1 onward |
| Video runs over 5:00 | High | Cut the architecture section first, then reliability board | Rehearse 3× |
| Python inexperience slows Days 1–2 | Medium | Days 1–2 are deliberately over-specified; scope was set assuming this | — |
| Cross-package import errors eat hours | Medium | Editable installs done once on Day 1, before any real code exists | D1-T0 |
| SQLite locked between scheduler and UI | Medium–High | WAL mode set in `ledger.py` on Day 1 | D1-T3 |
| AgentCore build pulls in UI deps and fails | Medium | `services/agent/requirements.txt` stays minimal and separate | D4-T4 |

---

## 11. IF YOU ONLY GET THREE DAYS

Ship in this order and stop wherever you run out:

1. FileAdapter → Extractor → Ledger → Streamlit worklist
2. Scheduler → Pursuer → real outbound email
3. Adjudicator with `DEFERRED` + child loop spawning

Those three, working, beat all five days half-finished. The adjudication moment is
the differentiator; everything else is table stakes.
