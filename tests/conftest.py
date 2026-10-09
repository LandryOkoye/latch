import uuid
from datetime import datetime, timedelta

import pytest

from latch_core import config, ledger
from latch_core.models import Loop, LoopStatus, WindowSource


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """A fresh, empty ledger. With LATCH_DYNAMODB_TABLE set, the same tests run
    against that (throwaway) DynamoDB table instead of a temp SQLite file."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    ledger.init_db()
    if config.DYNAMODB_TABLE:
        ledger.reset_db()


def make_loop(**overrides) -> Loop:
    now = datetime.now()
    fields = dict(
        id=str(uuid.uuid4()),
        promise="Send the proofs",
        source_quote="I'll send the proofs by Friday.",
        owner_name="Marcus Lee",
        owner_email="marcus@example.com",
        counterparty_org="Crestline Print",
        due_at=now - timedelta(days=2),
        window_source=WindowSource.STATED,
        closure_criterion="Proofs received",
        stakes="medium",
        status=LoopStatus.OPEN,
        created_at=now - timedelta(days=9),
    )
    fields.update(overrides)
    return Loop(**fields)
