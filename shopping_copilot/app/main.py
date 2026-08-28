from fastapi import FastAPI

app = FastAPI(
    title="Shopping Copilot",
    description="This is a CannotTok special edition",
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "shopping-copilot",
    }