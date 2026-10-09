"""DynamoDB ledger: one table. A loop is item (PK=LOOP#<id>, SK=LOOP); its events
share the partition as (PK=LOOP#<id>, SK=EVENT#<occurred_at>#<event id>), so one
query loads a loop with its history. A sparse GSI on message_id threads replies.
Listing scans the table, which is fine at a single team's scale."""

import uuid
from datetime import datetime
from enum import Enum

import boto3
from boto3.dynamodb.conditions import Attr, Key

from latch_core import config
from latch_core.models import Loop, LoopEvent, LoopEventType, LoopStatus

__all__ = [
    "init_db", "reset_db", "delete_events", "create_loop", "get_loop", "update_loop", "list_loops",
    "meeting_ingested", "fetch_children", "record_event", "find_event_by_message_id",
]

_UPDATABLE_FIELDS = set(Loop.model_fields) - {"id", "events"}
_MESSAGE_ID_INDEX = "message_id-index"

_table = boto3.resource("dynamodb", region_name=config.AWS_REGION).Table(config.DYNAMODB_TABLE)


def _pk(loop_id: str) -> str:
    return f"LOOP#{loop_id}"


def _to_loop(item: dict, events: list[LoopEvent] | None = None) -> Loop:
    fields = {k: v for k, v in item.items() if k not in {"PK", "SK"}}
    return Loop.model_validate({**fields, "events": events or []})


def _to_event(item: dict) -> LoopEvent:
    return LoopEvent.model_validate({k: v for k, v in item.items() if k not in {"PK", "SK"}})


def _scan(**kwargs) -> list[dict]:
    items, start = [], None
    while True:
        page = _table.scan(**kwargs, **({"ExclusiveStartKey": start} if start else {}))
        items.extend(page["Items"])
        start = page.get("LastEvaluatedKey")
        if not start:
            return items


def _loops_where(condition=None) -> list[Loop]:
    filter_expression = Attr("SK").eq("LOOP") if condition is None else Attr("SK").eq("LOOP") & condition
    return [_to_loop(item) for item in _scan(FilterExpression=filter_expression)]


def init_db() -> None:
    """Create the table if it doesn't exist yet."""
    client = _table.meta.client
    if config.DYNAMODB_TABLE in client.list_tables()["TableNames"]:
        return
    client.create_table(
        TableName=config.DYNAMODB_TABLE,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "message_id", "AttributeType": "S"},
        ],
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": _MESSAGE_ID_INDEX,
                "KeySchema": [{"AttributeName": "message_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    client.get_waiter("table_exists").wait(TableName=config.DYNAMODB_TABLE)


def reset_db() -> None:
    """Delete all loops and events. Used by the demo seed script."""
    with _table.batch_writer() as batch:
        for item in _scan(ProjectionExpression="PK, SK"):
            batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})


def delete_events(loop_id: str) -> None:
    items = _table.query(KeyConditionExpression=Key("PK").eq(_pk(loop_id)) & Key("SK").begins_with("EVENT#"))["Items"]
    with _table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})


def create_loop(loop: Loop) -> Loop:
    item = {"PK": _pk(loop.id), "SK": "LOOP", **loop.model_dump(mode="json", exclude={"events"})}
    _table.put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
    record_event(loop.id, LoopEventType.CREATED, detail=f"loop created: {loop.promise!r}")
    return get_loop(loop.id)


def get_loop(loop_id: str) -> Loop | None:
    items, start = [], None
    while True:
        page = _table.query(
            KeyConditionExpression=Key("PK").eq(_pk(loop_id)),
            **({"ExclusiveStartKey": start} if start else {}),
        )
        items.extend(page["Items"])
        start = page.get("LastEvaluatedKey")
        if not start:
            break
    loop_item = next((i for i in items if i["SK"] == "LOOP"), None)
    if loop_item is None:
        return None
    events = sorted((_to_event(i) for i in items if i["SK"].startswith("EVENT#")), key=lambda e: e.occurred_at)
    return _to_loop(loop_item, events)


def update_loop(loop_id: str, **fields) -> Loop | None:
    """Update one or more Loop fields. Enums/datetimes are serialised automatically."""
    unknown = set(fields) - _UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"not updatable fields: {sorted(unknown)}")
    if not fields:
        return get_loop(loop_id)

    names, values, assignments = {}, {}, []
    for i, (key, value) in enumerate(fields.items()):
        if isinstance(value, Enum):
            value = value.value
        elif isinstance(value, datetime):
            value = value.isoformat()
        names[f"#f{i}"] = key
        values[f":v{i}"] = value
        assignments.append(f"#f{i} = :v{i}")
    _table.update_item(
        Key={"PK": _pk(loop_id), "SK": "LOOP"},
        UpdateExpression="SET " + ", ".join(assignments),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ConditionExpression="attribute_exists(PK)",
    )
    return get_loop(loop_id)


def list_loops(status: LoopStatus | None = None) -> list[Loop]:
    loops = _loops_where(Attr("status").eq(status.value) if status else None)
    return sorted(loops, key=lambda loop: loop.due_at)


def meeting_ingested(meeting_id: str) -> bool:
    return bool(_scan(FilterExpression=Attr("SK").eq("LOOP") & Attr("source_meeting_id").eq(meeting_id), ProjectionExpression="PK"))


def fetch_children(loop_id: str) -> list[Loop]:
    return sorted(_loops_where(Attr("parent_id").eq(loop_id)), key=lambda loop: loop.created_at)


def record_event(
    loop_id: str,
    event_type: LoopEventType,
    *,
    channel: str | None = None,
    detail: str = "",
    evidence_span: str | None = None,
    message_id: str | None = None,
    reply_text: str | None = None,
    occurred_at: datetime | None = None,
) -> LoopEvent:
    event = LoopEvent(
        id=str(uuid.uuid4()),
        loop_id=loop_id,
        event_type=event_type,
        occurred_at=occurred_at or datetime.now(),
        channel=channel,
        detail=detail,
        evidence_span=evidence_span,
        message_id=message_id,
        reply_text=reply_text,
    )
    item = {"PK": _pk(loop_id), "SK": f"EVENT#{event.occurred_at.isoformat()}#{event.id}", **event.model_dump(mode="json")}
    if item["message_id"] is None:
        del item["message_id"]  # GSI key attributes must be absent, not null
    _table.put_item(Item=item)
    return event


def find_event_by_message_id(message_id: str) -> LoopEvent | None:
    items = _table.query(IndexName=_MESSAGE_ID_INDEX, KeyConditionExpression=Key("message_id").eq(message_id))["Items"]
    return _to_event(items[0]) if items else None
