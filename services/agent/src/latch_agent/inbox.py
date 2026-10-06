import re

from latch_core import config, ledger
from latch_core.models import Loop, LoopEventType, LoopStatus

from latch_agent.agents.adjudicator import adjudicate, apply_verdict
from latch_agent.tools import email_tools

_ADJUDICABLE = {LoopStatus.OPEN, LoopStatus.AWAITING_REPLY}
_BOUNCE_SENDERS = ("mailer-daemon", "postmaster")
# Gmail-style attribution line, which mail clients often wrap onto a second line.
_ATTRIBUTION_RE = re.compile(r"^On\b[^\n]*(?:\n[^\n]*)?\bwrote:[ \t]*$", re.MULTILINE)


def strip_quoted(body: str) -> str:
    """Drop the quoted chase from a reply, so the Adjudicator judges only what
    the counterparty actually wrote (the quote repeats the original promise)."""
    body = body.replace("\r\n", "\n")
    match = _ATTRIBUTION_RE.search(body)
    if match:
        body = body[: match.start()]
    body = body.split("-----Original Message-----")[0]
    return "\n".join(line for line in body.splitlines() if not line.lstrip().startswith(">")).strip()


def _active_loop(loop: Loop) -> Loop:
    """A reply threaded to a deferred loop belongs to its newest descendant,
    which carries the live commitment."""
    children = ledger.fetch_children(loop.id)
    while children:
        loop = children[-1]
        children = ledger.fetch_children(loop.id)
    return loop


def process_replies(limit: int = 25) -> list[dict]:
    """Match new inbound emails to loops, record them, and adjudicate each one.
    A reply is processed once: its Message-ID is stored on the REPLY_RECEIVED
    event, and messages already in the ledger are skipped."""
    processed = []
    for folder in config.IMAP_REPLY_FOLDERS:
        for msg in email_tools.fetch_recent_emails(folder=f'"{folder}"', limit=limit):
            message_id = msg["message_id"]
            sender = (msg["from"] or "").lower()
            if not message_id or any(s in sender for s in _BOUNCE_SENDERS):
                continue
            if ledger.find_event_by_message_id(message_id):
                continue
            loop_id = email_tools.find_loop_id_for_reply(msg)
            if loop_id is None:
                continue

            loop = _active_loop(ledger.get_loop(loop_id))
            reply_text = strip_quoted(msg["body"])
            ledger.record_event(
                loop.id, LoopEventType.REPLY_RECEIVED, channel="email",
                detail=f"reply from {msg['from']}", message_id=message_id, reply_text=reply_text,
            )
            result = {"loop_id": loop.id, "message_id": message_id, "verdict": None, "status": loop.status.value}
            if loop.status in _ADJUDICABLE:
                verdict = adjudicate(loop, reply_text)
                updated = apply_verdict(loop.id, reply_text, verdict)
                result.update(verdict=verdict.verdict.value, status=updated.status.value)
            processed.append(result)
    return processed
