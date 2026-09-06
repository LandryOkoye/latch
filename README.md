# Latch

*An agent that owns the space between "I'll get back to you" and whether anyone ever did.*

Status: scaffolding in progress. See `BUILD_PLAN.md` for the day-by-day build plan and `THESIS.md` for the underlying problem framing.

## What it is

Commitments made out loud in meetings and email ("I'll send the revised scope Thursday") have no system that owns the gap between promise and resolution. Latch listens to meeting transcripts, extracts every commitment as a tracked **loop**, watches for evidence that each one closed, and chases overdue ones by email — reading replies and deciding what they actually mean (closed, deferred, transferred, disputed, or ambiguous), rather than just alerting a human.

## Setup

```bash
make install
cp .env.example .env   # fill in credentials
make demo
```

## License

MIT — see `LICENSE`.
