import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.infrastructure.search.local_indexes import warm_indexes

app = FastAPI(
    title="Shopping Copilot",
    description=("a CannotTok special"),
)

@app.on_event("startup")
def _warm_retrieval_indexes():
    # ~2s npz load + ~20s BM25 build; warmed off the event loop so the
    # server accepts requests immediately and the first search finds them hot
    threading.Thread(target=warm_indexes, daemon=True).start()

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(router, prefix="/api")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "shopping-copilot",
    }