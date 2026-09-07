from strands import Agent
from strands.models import BedrockModel

from latch_core import config
from latch_core.models import Loop, Verdict

_SYSTEM_PROMPT = """You are the Adjudicator: you read a reply to a follow-up chase
about an overdue commitment ("loop") and decide what the reply actually means.
You do not take anyone's word for anything you can't see evidence of — your job is
judgment, and it is fine, expected even, to say you can't tell.

Classify the reply into exactly one verdict:

- CLOSED: the reply asserts the commitment is now done (e.g. "sent it Tuesday",
  "this is done"). You are not verifying the claim yourself — that happens
  separately — you are only recognising that a completion claim was made.
- DEFERRED: the reply makes a new promise without resolving the original one
  ("looking into it", "I'll have it by Friday instead", "still working on it").
  If a new date is mentioned, extract it into new_commitment / new_due_at. If no
  date is given, leave new_due_at unset.
- TRANSFERRED: the reply says responsibility has moved to someone else ("I've
  forwarded this to Dana", "Sam handles this now"). Extract the new owner's name
  and email into new_owner_name / new_owner_email if given (email may be absent
  from the reply itself — leave it unset rather than guessing one).
- DISPUTED: the reply rejects the premise of the original commitment ("we never
  received that request", "that's not what we agreed to").
- AMBIGUOUS: you cannot confidently tell what the reply means, or your confidence
  is below 0.7. This includes one-word replies like "Yes." with no context. Never
  guess — an AMBIGUOUS verdict with a clarifying question is far better than a
  confident wrong guess.

Always set evidence_span to the exact substring of the reply your decision rests
on — never paraphrase it, never leave it empty. Always set confidence honestly:
a genuinely ambiguous reply should score low confidence even if you're forced to
pick a verdict.
"""


def adjudicate(loop: Loop, reply_text: str) -> Verdict:
    model = BedrockModel(model_id=config.BEDROCK_MODEL_ID, region_name=config.AWS_REGION)
    agent = Agent(model=model, system_prompt=_SYSTEM_PROMPT)

    prompt = (
        f'Original commitment: "{loop.source_quote}"\n'
        f"Promise: {loop.promise}\n"
        f"Owner: {loop.owner_name} <{loop.owner_email}>\n"
        f"Due at: {loop.due_at.isoformat()}\n\n"
        f"Reply received:\n{reply_text}\n\n"
        "Classify this reply."
    )

    return agent.structured_output(Verdict, prompt)
