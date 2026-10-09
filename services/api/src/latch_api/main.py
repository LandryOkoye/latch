import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from latch_core import ledger

from latch_api import agents
from latch_api.routes import loops, meetings, reliability

log = logging.getLogger("latch.api")

TICK_SECONDS = 60
# In AWS this process drives the agent scheduler (LATCH_RUN_SCHEDULER=1); locally
# `make run-agent` runs it instead.
RUN_SCHEDULER = os.environ.get("LATCH_RUN_SCHEDULER") == "1"
# The built React app, served from the same origin in production.
WEB_DIST = os.environ.get("LATCH_WEB_DIST")


def _scheduler_loop(stop: threading.Event) -> None:
    while not stop.wait(TICK_SECONDS):
        try:
            result = agents.invoke({"action": "tick"})
            if result.get("replies") or result.get("pursued"):
                log.info("tick: %s", result)
        except Exception:
            log.exception("scheduler tick failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    ledger.init_db()
    stop = threading.Event()
    if RUN_SCHEDULER:
        threading.Thread(target=_scheduler_loop, args=(stop,), daemon=True, name="scheduler").start()
    yield
    stop.set()


app = FastAPI(title="Latch API", lifespan=lifespan)
app.include_router(loops.router)
app.include_router(reliability.router)
app.include_router(meetings.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


if WEB_DIST:
    _dist = Path(WEB_DIST)
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def web(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        file = (_dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(_dist.resolve()):
            return FileResponse(file)
        return FileResponse(_dist / "index.html")
