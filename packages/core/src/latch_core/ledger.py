"""The ledger: loops and their event history. SQLite locally; DynamoDB in AWS
(LATCH_DYNAMODB_TABLE), so the deployed agents, API, and UI share one ledger.
Both backends expose the same functions."""

from latch_core import config

if config.DYNAMODB_TABLE:
    from latch_core.ledger_dynamodb import *  # noqa: F403
else:
    from latch_core.ledger_sqlite import *  # noqa: F403
