from typing import Protocol

from latch_core.models import MeetingTranscript


class TranscriptAdapter(Protocol):
    def fetch(self) -> MeetingTranscript:
        """Return a MeetingTranscript. Every adapter normalises to this one shape —
        nothing downstream knows or cares which adapter produced it."""
        ...
