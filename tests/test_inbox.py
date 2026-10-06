import pytest

from conftest import make_loop
from latch_agent import inbox
from latch_core import config, ledger
from latch_core.models import LoopEventType, LoopStatus, Verdict, VerdictType

pytestmark = pytest.mark.usefixtures("tmp_db")

_DEFERRED = Verdict(verdict=VerdictType.DEFERRED, confidence=0.9, evidence_span="next week")


@pytest.fixture
def mailbox(monkeypatch):
    """A fake inbox: tests append message dicts; adjudication is stubbed."""
    messages: list[dict] = []
    adjudicated: list[tuple[str, str]] = []

    def fake_adjudicate(loop, reply_text):
        adjudicated.append((loop.id, reply_text))
        return _DEFERRED

    monkeypatch.setattr(config, "IMAP_REPLY_FOLDERS", ["INBOX"])
    monkeypatch.setattr(inbox.email_tools, "fetch_recent_emails", lambda folder, limit: list(messages))
    monkeypatch.setattr(inbox, "adjudicate", fake_adjudicate)
    return messages, adjudicated


def _chased_loop(message_id="<chase@latch>", **overrides):
    loop = ledger.create_loop(make_loop(status=LoopStatus.AWAITING_REPLY, **overrides))
    ledger.record_event(loop.id, LoopEventType.TOUCHED, channel="email", message_id=message_id)
    return loop


def _reply(message_id="<reply@vendor>", in_reply_to="<chase@latch>", body="I'll have it next week.", sender="marcus@example.com", subject="Re: proofs"):
    return {
        "message_id": message_id, "in_reply_to": in_reply_to, "references": in_reply_to,
        "from": sender, "to": "latch@example.com", "subject": subject, "body": body,
    }


def test_strip_quoted_removes_wrapped_attribution_and_quote_lines():
    body = (
        "Sorry, printer delay. Next Wednesday.\n\n"
        "On Sat, Oct 10, 2026 at 3:00 PM Latch <\nlatch@example.com> wrote:\n"
        "> Following up on this from our meeting:\n> \"I'll send the proofs by Friday.\""
    )
    assert inbox.strip_quoted(body) == "Sorry, printer delay. Next Wednesday."
    assert inbox.strip_quoted(body.replace("\n", "\r\n")) == "Sorry, printer delay. Next Wednesday."


def test_reply_is_recorded_adjudicated_and_applied_once(mailbox):
    messages, adjudicated = mailbox
    loop = _chased_loop()
    messages.append(_reply())

    [result] = inbox.process_replies()

    assert result == {"loop_id": loop.id, "message_id": "<reply@vendor>", "verdict": "deferred", "status": "awaiting_reply"}
    assert adjudicated == [(loop.id, "I'll have it next week.")]
    events = [e.event_type for e in ledger.get_loop(loop.id).events]
    assert LoopEventType.REPLY_RECEIVED in events and LoopEventType.DEFERRED in events
    assert len(ledger.fetch_children(loop.id)) == 1

    assert inbox.process_replies() == []
    assert len(adjudicated) == 1


def test_subject_token_matches_when_threading_headers_are_missing(mailbox):
    messages, adjudicated = mailbox
    loop = _chased_loop()
    messages.append(_reply(in_reply_to=None, subject=f"Re: proofs [LATCH-{loop.id[:8]}]"))

    inbox.process_replies()

    assert adjudicated[0][0] == loop.id


def test_bounces_and_unrelated_mail_are_ignored(mailbox):
    messages, adjudicated = mailbox
    _chased_loop()
    messages.append(_reply(message_id="<bounce@google>", sender="Mail Delivery Subsystem <mailer-daemon@googlemail.com>"))
    messages.append(_reply(message_id="<newsletter@x>", in_reply_to=None, subject="Weekly digest"))

    assert inbox.process_replies() == []
    assert adjudicated == []


def test_reply_to_deferred_parent_goes_to_newest_child(mailbox):
    messages, adjudicated = mailbox
    parent = _chased_loop()
    child = ledger.create_loop(make_loop(parent_id=parent.id, status=LoopStatus.OPEN))
    messages.append(_reply())

    [result] = inbox.process_replies()

    assert result["loop_id"] == child.id
    assert adjudicated[0][0] == child.id


def test_reply_to_escalated_loop_is_recorded_but_not_adjudicated(mailbox):
    messages, adjudicated = mailbox
    loop = _chased_loop()
    ledger.update_loop(loop.id, status=LoopStatus.ESCALATED_TO_HUMAN)
    messages.append(_reply())

    [result] = inbox.process_replies()

    assert result["verdict"] is None
    assert adjudicated == []
    assert ledger.get_loop(loop.id).events[-1].event_type == LoopEventType.REPLY_RECEIVED
