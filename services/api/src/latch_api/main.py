from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from latch_core import ledger

from latch_api.routes import loops, reliability

app = FastAPI(title="Latch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ledger.init_db()

app.include_router(loops.router)
app.include_router(reliability.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
