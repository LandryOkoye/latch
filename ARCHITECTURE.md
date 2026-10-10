# Architecture

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
