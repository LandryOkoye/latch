# Latch

*An agent that owns the space between "I'll get back to you" and whether anyone ever did.*

## The Problem

Every organization runs on commitments that are made out loud and never written down anywhere that matters. A vendor says "I'll get the proofs to you by Friday." A teammate says "I'll send the revised timeline Monday." A client says "we'll circle back once finance has looked at it." Each of these is a real promise with a real deadline — and the moment the meeting ends, responsibility for tracking it evaporates. Nobody owns the space between the promise and its resolution.

This isn't a failure of any one person's diligence. It's a structural gap. The person who made the promise has no system nagging them. The person who's owed the promise has no reliable way to know if it's already slipping until it's too late. There is no error message for something that simply didn't happen — silence is indistinguishable from "handled" until the deadline has already passed and the damage is already done. Multiply this across a dozen meetings a week, each with two or three commitments buried in the conversation, and you get the real, invisible failure mode behind slipped deliverables, blown timelines, and eroded trust between teams and vendors: not incompetence, just an accountability gap that no existing tool is built to watch.

Latch closes that gap. It attends your meetings, listens to the full conversation, and pulls out every commitment anyone in the room made — not just the ones that get written down afterward — and turns each one into a tracked, chased, and eventually resolved thread.

## Who It's For

Latch is built for a **delivery or account manager at a small agency or consultancy** — someone running 6–12 client, vendor, and internal calls a week where commitments fly in both directions and none of them are ever ticketed. This role is a strong fit because:

- Counterparties are reachable by ordinary email, so pursuit is real, not simulated.
- Missed commitments have a visible, immediate cost: slipped deliverables, lapsed approvals, damaged client trust.
- Over time, tracking every commitment produces something nobody in this role has ever had: an empirical answer to "which of our vendors actually hold their dates."

The same mechanic generalizes to any professional who spends their week making and chasing promises on other people's behalf — case managers, project coordinators, permit expediters — but Latch is built and demonstrated around this one persona first.

## How It Works

1. **Latch attends the meeting.** Whether that's a bot joining the call directly or a transcript handed to it afterward, Latch listens to the entire conversation — not a summary, the actual back-and-forth — because commitments are made in passing, in the middle of unrelated discussion, by anyone in the room, including the user themselves.
2. **The Extractor agent turns talk into tracked loops.** Every real commitment — "I'll send X by Friday," "we'll look into Y and get back to you" — becomes a **loop**: who owns it, what evidence would count as closed, and a due window that's either stated outright or inferred from how it was phrased. Vague suggestions and hypotheticals ("we should think about doing X sometime") are deliberately *not* extracted — precision matters as much as recall.
3. **A scheduler watches every open loop.** Once a loop's window lapses, the **Pursuer agent** decides what to do next — check the counterparty's own system of record first, then the inbox, then draft and send a follow-up quoting the original commitment verbatim. It's judgment applied to each loop's specific history, not a fixed script: a fresh loop gets a first email; a loop that's already been chased twice and deferred once gets escalated to a human instead of chased again.
4. **The Adjudicator agent reads what comes back and decides what it actually means.** A reply isn't just "resolved" or "not resolved" — it's classified as closed, deferred (a new promise with no resolution — spawns a linked child loop and keeps the parent's history intact), transferred to someone else (re-targets the loop and hands the new owner a message that carries the full history, so they don't start from zero), disputed, or genuinely ambiguous. A claimed closure is checked against the counterparty's own system of record before it's believed — Latch doesn't take anyone's word for it.
5. **Every counterparty accrues a reliability record.** Because every loop's full lifecycle is tracked — how many touches it took, whether it closed on time or had to be escalated — Latch produces an answer nobody had access to before: an empirical scorecard of which vendors, clients, and teammates actually follow through.

## Architecture

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
        │              LEDGER (SQLite, WAL mode)              │
        │  loops (tree via parent_id) · events                │
        └───────────────┬────────────────────────────────────┘
                        │  (scheduler tick: window lapsed?)
                        ▼
        ┌────────────────────────────────────────────────────┐
        │  AGENT 2: PURSUER  (Strands, tools + reasoning)     │
        │  TOOLS: check_sheet_record, check_inbox_for_evidence,│
        │         draft_followup, send_email, send_telegram,   │
        │         escalate_to_human                            │
        │  Chooses a strategy from each loop's own state —     │
        │  touch count, prior deferrals, channels already tried│
        └───────────────┬────────────────────────────────────┘
                        │  reply arrives (IMAP poll, Message-ID
                        │  threading + subject-token fallback)
                        ▼
        ┌────────────────────────────────────────────────────┐
        │  AGENT 3: ADJUDICATOR  (Strands, structured_output) │
        │  reply → {verdict, confidence, evidence_span,        │
        │           new_owner?, new_commitment?}               │
        │  CLOSED → verified against system of record          │
        │  DEFERRED → spawns a linked child loop                │
        │  TRANSFERRED → re-targets owner, carries history      │
        │  DISPUTED / AMBIGUOUS → escalates, never guesses      │
        └───────────────┬────────────────────────────────────┘
                        ▼
              ┌──────────────────────────────┐
              │  STREAMLIT REVIEWER UI        │
              │  worklist (priority-ranked) · │
              │  loop detail & timeline ·     │
              │  reliability board            │
              └──────────────────────────────┘
```

The domain model (`packages/core`), the agent runtime (`services/agent`), and the reviewer UI (`apps/reviewer`) share one definition of what a loop is, so the deployable agent runtime can ship to Bedrock AgentCore independently of the UI.

## The Adjudication Taxonomy

This is the core judgment call the whole system is built around — a reply is never just "done" or "not done":

| Verdict | Trigger | Required action |
|---|---|---|
| **CLOSED** | Reply asserts the commitment is done | Verified against the counterparty's system of record. Confirmed → `CLOSED_VERIFIED`. Can't be confirmed → `CLOSED_CLAIMED`, flagged for human review. |
| **DEFERRED** | A new promise is made, nothing is resolved | Spawns a linked **child loop** with a new window. The parent's history stays intact; `deferral_count` increments. |
| **TRANSFERRED** | Responsibility has moved to someone else | Re-targets the loop's owner and generates a **history-carrying handoff message** — the original quote, the deadline, and a summary of everything tried so far — so the new owner never starts from zero. |
| **DISPUTED** | The premise itself is rejected | Escalated to a human with the correction. Latch does not re-send the same chase against a disputed premise. |
| **AMBIGUOUS** | Confidence is too low to classify safely | Escalated to a human with a drafted clarifying question. Latch never guesses. |

Every verdict carries an `evidence_span` — the exact substring of the reply the decision rests on — surfaced directly in the reviewer UI, highlighted, next to the loop it resolved.

## Strands Agents Usage

| Feature | Where used |
|---|---|
| `Agent` + system prompt | All three agents (Extractor, Pursuer, Adjudicator) |
| `@tool` decorator | Pursuer's six-tool surface: sheet lookup, inbox check, drafting, email, Telegram, human escalation |
| `structured_output` | Extractor (`list[Loop]`) and Adjudicator (`Verdict`) — typed Pydantic contracts, not string parsing |
| Model-driven tool selection | The Pursuer decides its own strategy per loop from state — no hard-coded escalation ladder |
| Multi-agent composition | Extractor → ledger → Pursuer → Adjudicator, each with a distinct role, prompt, and failure mode |
| State across turns | Touch count, deferral count, and channel history all feed back into what the Pursuer does next |
| Amazon Bedrock AgentCore | The agent runtime is deployed and independently invocable |

## Setup

Requires Python 3.10+ and an AWS account with Bedrock model access enabled for Amazon Nova Pro in `us-east-1`.

```bash
git clone <this-repo>
cd latch
make install              # venv + editable installs for all three packages
cp .env.example .env      # fill in: AWS credentials, a dedicated Gmail account +
                           # App Password, a Google service-account JSON + Sheet ID,
                           # optionally a Telegram bot token
make seed                 # resets the ledger and loads a realistic, pre-aged worklist
make ingest                # runs the FileAdapter over demo/transcripts to extract loops live
make run-ui                # opens the Streamlit reviewer at localhost:8501
```

Or run `make demo` to seed, ingest, and bring up the scheduler and UI together in one command.

## Roadmap

- **Live meeting ingestion** — join calls directly via a hosted meeting bot (the `AttendeeAdapter` slot already exists in the architecture; `FileAdapter` is the ingestion path used today).
- **Public-hosted reviewer UI** as a standing live demo link, alongside the deployed AgentCore runtime.
- **Telegram as an active second pursuit channel**, to fully exercise channel-switching once email has been tried without a reply.
- **Richer reliability scoring** — trendlines per counterparty over time, not just a point-in-time snapshot.
- **Multi-tenant support** for a team of coordinators sharing one reliability record across shared vendors.

## License

MIT — see `LICENSE`.
