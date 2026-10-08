from pathlib import Path

import pytest

from conftest import make_loop
from latch_agent.agents.extractor import extract_loops
from latch_agent.ingest import file_adapter
from latch_agent.ingest.file_adapter import FileAdapter, parse_transcript_text
from latch_core import ledger
from latch_core.models import WindowSource

TRANSCRIPTS = Path(__file__).resolve().parents[1] / "demo" / "transcripts"
KICKOFF = TRANSCRIPTS / "2026-08-10-acme-kickoff.txt"


def test_file_adapter_parses_header_participants_and_utterances():
    transcript = FileAdapter(KICKOFF).fetch()

    assert transcript.meeting_id == "2026-08-10-acme-kickoff"
    assert transcript.occurred_at.isoformat() == "2026-08-10T10:00:00"
    assert {p.name for p in transcript.participants} == {"Dana Kim", "Marcus Lee", "Jordan Alvarez", "Priya Shah"}
    marcus = next(u for u in transcript.utterances if u.speaker == "Marcus Lee")
    assert marcus.speaker_email == "marcus@crestlineprint.example"
    assert marcus.timestamp == 38


def test_ingest_extracts_each_meeting_once(tmp_db, monkeypatch):
    calls = []

    def fake_extract(transcript):
        calls.append(transcript.meeting_id)
        return [make_loop(source_meeting_id=transcript.meeting_id)]

    monkeypatch.setattr(file_adapter, "extract_loops", fake_extract)

    first = file_adapter.ingest(TRANSCRIPTS)
    second = file_adapter.ingest(TRANSCRIPTS)

    assert set(first.values()) == {1} and len(first) == 3
    assert set(second.values()) == {None}
    assert len(calls) == 3
    assert len(ledger.list_loops()) == 3


def test_extractor_resolves_weekdays_against_meeting_date():
    """Live Bedrock: 'by Thursday' said on Saturday 2026-10-10 means Thursday 2026-10-15."""
    transcript = parse_transcript_text(
        "OCCURRED_AT: 2026-10-10T10:00:00\nPARTICIPANTS:\n- Tom Becker <tom@harborprint.example>\n---\n"
        "[00:09] Tom Becker: I'll get the printed banners delivered to your office by Thursday.",
        fallback_id="weekday-check",
    )
    [loop] = extract_loops(transcript)
    assert loop.window_source == WindowSource.STATED
    assert loop.due_at.date().isoformat() == "2026-10-15", f"got {loop.due_at:%A %Y-%m-%d}"


def test_extractor_on_kickoff_transcript():
    """Live Bedrock: BUILD_PLAN.md D1-T4 acceptance on the kickoff meeting."""
    loops = extract_loops(FileAdapter(KICKOFF).fetch())
    by_owner = {loop.owner_name: loop for loop in loops}

    assert set(by_owner) == {"Marcus Lee", "Jordan Alvarez", "Dana Kim"}, [l.promise for l in loops]
    assert by_owner["Marcus Lee"].window_source == WindowSource.STATED
    assert by_owner["Marcus Lee"].due_at.date().isoformat() == "2026-08-21"
    assert by_owner["Dana Kim"].window_source == WindowSource.STATED
    assert by_owner["Jordan Alvarez"].window_source == WindowSource.INFERRED
    assert not any("accessibility" in l.promise.lower() for l in loops), "near-miss was extracted"
