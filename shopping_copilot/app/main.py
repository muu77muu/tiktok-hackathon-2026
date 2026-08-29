from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Shopping Copilot",
    description=("a CannotTok special"),
)

app.include_router(router, prefix="/api")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "shopping-copilot",
    }