import re
from datetime import datetime
from pathlib import Path

from latch_core.models import MeetingTranscript, Participant, Utterance

_HEADER_LINE_RE = re.compile(r"^([A-Z_]+):\s*(.*)$")
_PARTICIPANT_RE = re.compile(r"^-\s*(.+?)\s*<(.+?)>\s*$")
_UTTERANCE_RE = re.compile(r"^\[(\d{2}):(\d{2})\]\s*([^:]+):\s*(.*)$")

_VTT_TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})")
_VTT_VOICE_RE = re.compile(r"^<v\s+([^>]+)>(.*?)(?:</v>)?$")


class FileAdapter:
    """Loads a MeetingTranscript from a hand-written .txt or .vtt file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def fetch(self) -> MeetingTranscript:
        if self.path.suffix.lower() == ".vtt":
            return _parse_vtt(self.path)
        return _parse_txt(self.path)


def _parse_txt(path: Path) -> MeetingTranscript:
    lines = path.read_text(encoding="utf-8").splitlines()

    meeting_id = ""
    title = ""
    occurred_at = datetime.now()
    participants: list[Participant] = []
    utterances: list[Utterance] = []

    body_start = len(lines)
    in_participants = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            body_start = i + 1
            break
        if stripped == "PARTICIPANTS:":
            in_participants = True
            continue
        if in_participants:
            match = _PARTICIPANT_RE.match(stripped)
            if match:
                participants.append(Participant(name=match.group(1), email=match.group(2)))
            continue
        match = _HEADER_LINE_RE.match(stripped)
        if match:
            key, value = match.group(1), match.group(2)
            if key == "MEETING_ID":
                meeting_id = value
            elif key == "TITLE":
                title = value
            elif key == "OCCURRED_AT":
                occurred_at = datetime.fromisoformat(value)

    email_by_name = {p.name: p.email for p in participants}

    for line in lines[body_start:]:
        match = _UTTERANCE_RE.match(line.strip())
        if not match:
            continue
        minutes, seconds, speaker, text = match.groups()
        speaker = speaker.strip()
        utterances.append(
            Utterance(
                speaker=speaker,
                speaker_email=email_by_name.get(speaker),
                timestamp=float(int(minutes) * 60 + int(seconds)),
                text=text.strip(),
            )
        )

    return MeetingTranscript(
        meeting_id=meeting_id or path.stem,
        title=title or path.stem,
        occurred_at=occurred_at,
        participants=participants,
        utterances=utterances,
    )


def _vtt_timestamp_to_seconds(ts: str) -> float:
    match = _VTT_TIME_RE.search(ts)
    if not match:
        return 0.0
    hours, minutes, seconds, millis = (int(g) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def _parse_vtt(path: Path) -> MeetingTranscript:
    """Standard WebVTT cues, with optional `<v Speaker>` voice tags and optional
    `NOTE MEETING_ID:` / `NOTE TITLE:` / `NOTE OCCURRED_AT:` metadata lines."""
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", text.strip())

    meeting_id = ""
    title = ""
    occurred_at = datetime.fromtimestamp(path.stat().st_mtime)
    utterances: list[Utterance] = []
    speakers_seen: dict[str, None] = {}

    for block in blocks:
        block_lines = [line for line in block.splitlines() if line.strip()]

        for line in block_lines:
            if line.upper().startswith("NOTE MEETING_ID:"):
                meeting_id = line.split(":", 1)[1].strip()
            elif line.upper().startswith("NOTE TITLE:"):
                title = line.split(":", 1)[1].strip()
            elif line.upper().startswith("NOTE OCCURRED_AT:"):
                occurred_at = datetime.fromisoformat(line.split(":", 1)[1].strip())

        cue_idx = next((i for i, line in enumerate(block_lines) if "-->" in line), None)
        if cue_idx is None:
            continue

        start_str = block_lines[cue_idx].split("-->")[0].strip()
        timestamp = _vtt_timestamp_to_seconds(start_str)

        speaker = "Unknown"
        content_parts = []
        for line in block_lines[cue_idx + 1 :]:
            voice_match = _VTT_VOICE_RE.match(line.strip())
            if voice_match:
                speaker = voice_match.group(1).strip()
                content_parts.append(voice_match.group(2).strip())
            else:
                content_parts.append(line.strip())
        content = " ".join(p for p in content_parts if p)
        if not content:
            continue

        speakers_seen.setdefault(speaker, None)
        utterances.append(Utterance(speaker=speaker, speaker_email=None, timestamp=timestamp, text=content))

    participants = [Participant(name=name) for name in speakers_seen]

    return MeetingTranscript(
        meeting_id=meeting_id or path.stem,
        title=title or path.stem,
        occurred_at=occurred_at,
        participants=participants,
        utterances=utterances,
    )
