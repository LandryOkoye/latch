from bedrock_agentcore.runtime import BedrockAgentCoreApp

from latch_core import ledger
from latch_core.models import MeetingTranscript

from latch_agent import scheduler
from latch_agent.agents.adjudicator import adjudicate, apply_verdict
from latch_agent.agents.extractor import extract_loops
from latch_agent.agents.pursuer import pursue

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Single AgentCore entrypoint for the deployed agent runtime. Dispatches
    on payload['action']: 'extract' | 'pursue' | 'adjudicate' | 'tick'."""
    ledger.init_db()
    action = payload.get("action")

    if action == "tick":
        return scheduler.tick()

    if action == "extract":
        transcript = MeetingTranscript(**payload["transcript"])
        loops = extract_loops(transcript)
        for loop in loops:
            ledger.create_loop(loop)
        return {"loops_created": [loop.id for loop in loops]}

    if action == "pursue":
        return {"result": pursue(payload["loop_id"])}

    if action == "adjudicate":
        loop_id = payload["loop_id"]
        reply_text = payload["reply_text"]
        loop = ledger.get_loop(loop_id)
        if loop is None:
            return {"error": f"unknown loop {loop_id}"}
        verdict = adjudicate(loop, reply_text)
        updated = apply_verdict(loop_id, reply_text, verdict)
        return {"verdict": verdict.model_dump(mode="json"), "loop_status": updated.status.value}

    return {"error": f"unknown action: {action!r}"}


if __name__ == "__main__":
    app.run()
