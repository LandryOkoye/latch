import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from latch_core import ledger

from latch_agent.ingest.file_adapter import parse_transcript_text

from latch_api import agents
from latch_api.limits import ingest_limit
from latch_api.schemas import IngestResult

router = APIRouter(prefix="/api", tags=["meetings"])

MAX_TRANSCRIPT_CHARS = 20_000


class IngestRequest(BaseModel):
    text: str = Field(max_length=MAX_TRANSCRIPT_CHARS)


@router.post("/meetings", response_model=IngestResult)
def ingest_meeting(request: IngestRequest) -> IngestResult:
    transcript = parse_transcript_text(request.text, fallback_id=f"pasted-{uuid.uuid4().hex[:8]}")
    if not transcript.utterances:
        raise HTTPException(status_code=422, detail="No utterances found. Use lines like `[00:38] Marcus Lee: I'll send the proofs by Friday.`")
    if ledger.meeting_ingested(transcript.meeting_id):
        raise HTTPException(status_code=409, detail=f"Meeting {transcript.meeting_id!r} was already ingested.")
    ingest_limit.check()

    result = agents.invoke({"action": "extract", "transcript": transcript.model_dump(mode="json")})
    loops = [ledger.get_loop(loop_id) for loop_id in result["loops_created"]]
    return IngestResult(meeting_id=transcript.meeting_id, title=transcript.title, loops=loops)
