from strands import Agent, tool
from strands.models import BedrockModel

from latch_core import config, ledger
from latch_core.models import LoopEventType, LoopStatus

from latch_agent.tools import email_tools, ledger_tools, sheet_tools, telegram_tools

_SYSTEM_PROMPT = """You are the Pursuer: you chase overdue commitments ("loops") on
behalf of a delivery manager. You decide the right next action yourself, based on
each loop's specific history — there is no fixed script to run every time.

General judgment, not a fixed ladder:
- If nothing has been tried yet, first check for evidence the loop may already be
  resolved (the system-of-record sheet, then the inbox) before contacting anyone.
- If no evidence of resolution turns up, draft a follow-up quoting the original
  commitment and send it by email.
- If email has already been tried without a reply, consider switching channels
  (Telegram) rather than repeating the same thing — but if that channel isn't
  actually available, fall back sensibly instead of pretending it worked.
- Escalate to a human instead of continuing to chase when: the loop has already
  been deferred multiple times, several touches have gone unanswered, or the
  stakes are high enough that continued silent automation isn't appropriate.
- Never fabricate evidence of closure. Never claim to have sent something you did
  not actually send via a tool.

Always end by stating, in plain language, what you did (or deliberately chose not
to do) and why — your reasoning is as important as the action.
"""


@tool
def check_sheet_record(loop_id: str) -> dict:
    """Check the counterparty's system-of-record Google Sheet for a row matching
    this loop. Returns {'found': False} if nothing matches or the sheet isn't
    configured, otherwise the row data with 'found': True."""
    row = sheet_tools.check_sheet_record(loop_id)
    return row if row else {"found": False}


@tool
def check_inbox_for_evidence(loop_id: str) -> dict:
    """Search the inbox for any recent email from the loop's owner that might
    already answer this loop, without sending anything. Returns {'found': False}
    or {'found': True, 'latest': {...}}."""
    loop = ledger.get_loop(loop_id)
    if loop is None or not loop.owner_email:
        return {"found": False}
    matches = [
        m
        for m in email_tools.fetch_recent_emails(limit=15)
        if loop.owner_email.lower() in (m["from"] or "").lower()
    ]
    if not matches:
        return {"found": False}
    return {"found": True, "latest": matches[0]}


@tool
def draft_followup(loop_id: str) -> str:
    """Produce a ready-to-send follow-up message body for this loop, quoting the
    original commitment so the recipient doesn't have to dig for context."""
    loop = ledger.get_loop(loop_id)
    if loop is None:
        return ""
    return (
        f"Hi {loop.owner_name},\n\n"
        f"Following up on this from our meeting:\n"
        f'"{loop.source_quote}"\n\n'
        f"This was expected by {loop.due_at:%B %d}, and I don't have confirmation "
        f"it's been taken care of yet. Could you give me a quick update?\n\n"
        f"Thanks."
    )


@tool
def send_email(loop_id: str, subject: str, body: str) -> str:
    """Send a follow-up email to the loop's owner and record the touch. Returns
    the sent Message-ID."""
    loop = ledger.get_loop(loop_id)
    if loop is None:
        raise ValueError(f"unknown loop {loop_id}")
    message_id = email_tools.send_email(to=loop.owner_email, subject=subject, body=body)
    ledger_tools.record_touch(loop_id, channel="email", detail=f"sent: {subject}")
    return message_id


@tool
def send_telegram(loop_id: str, text: str) -> str:
    """Send a follow-up via Telegram as a secondary channel — use this when email
    has already been tried without success. Returns 'sent' or a string explaining
    why it wasn't (e.g. not configured)."""
    loop = ledger.get_loop(loop_id)
    if loop is None:
        raise ValueError(f"unknown loop {loop_id}")
    sent = telegram_tools.send_telegram(loop.owner_name, text)
    if not sent:
        return "not_configured: no Telegram channel is set up for this counterparty"
    ledger_tools.record_touch(loop_id, channel="telegram", detail="sent via telegram")
    return "sent"


@tool
def escalate_to_human(loop_id: str, reason: str) -> str:
    """Stop automated pursuit and flag this loop for a human to review, with a
    reason. Use this instead of continuing to chase when automation has run its
    course for this loop."""
    ledger.update_loop(loop_id, status=LoopStatus.ESCALATED_TO_HUMAN)
    ledger.record_event(loop_id, LoopEventType.ESCALATED, detail=reason)
    return "escalated"


def pursue(loop_id: str) -> str:
    """Invoke the Pursuer agent on a single overdue loop. Returns the agent's
    final explanation of what it did and why."""
    loop = ledger.get_loop(loop_id)
    if loop is None:
        raise ValueError(f"unknown loop {loop_id}")

    model = BedrockModel(model_id=config.BEDROCK_MODEL_ID, region_name=config.AWS_REGION)
    agent = Agent(
        model=model,
        tools=[
            check_sheet_record,
            check_inbox_for_evidence,
            draft_followup,
            send_email,
            send_telegram,
            escalate_to_human,
        ],
        system_prompt=_SYSTEM_PROMPT,
    )

    events_summary = (
        "\n".join(
            f"- {e.occurred_at.isoformat()} [{e.event_type.value}]"
            + (f" via {e.channel}" if e.channel else "")
            + (f": {e.detail}" if e.detail else "")
            for e in loop.events
        )
        or "(no events yet)"
    )

    prompt = (
        f"Loop ID: {loop.id}\n"
        f"Promise: {loop.promise}\n"
        f'Source quote: "{loop.source_quote}"\n'
        f"Owner: {loop.owner_name} <{loop.owner_email}>\n"
        f"Counterparty org: {loop.counterparty_org}\n"
        f"Due at: {loop.due_at.isoformat()} (now overdue)\n"
        f"Stakes: {loop.stakes}\n"
        f"Status: {loop.status.value}\n"
        f"Touch count: {loop.touch_count}\n"
        f"Deferral count: {loop.deferral_count}\n"
        f"Channels already tried: {loop.channels_tried or 'none'}\n"
        f"Event history:\n{events_summary}\n\n"
        "This loop is past its window. Decide what to do next using your tools, "
        "and explain your reasoning."
    )

    result = agent(prompt)
    return str(result)
