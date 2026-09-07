from latch_core import ledger
from latch_core.models import LoopEventType, LoopStatus


def record_touch(loop_id: str, channel: str, detail: str) -> None:
    """Record that a loop was touched via a channel: bump touch_count, track the
    channel, and log the event. Called by the Pursuer's send tools, not by the
    agent directly."""
    loop = ledger.get_loop(loop_id)
    if loop is None:
        return
    channels_tried = list(dict.fromkeys([*loop.channels_tried, channel]))
    ledger.update_loop(
        loop_id,
        touch_count=loop.touch_count + 1,
        channels_tried=channels_tried,
        status=LoopStatus.AWAITING_REPLY,
    )
    ledger.record_event(loop_id, LoopEventType.TOUCHED, channel=channel, detail=detail)
