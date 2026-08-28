
# to execute evaluation across a collection of benchmark shopping sessions

class BenchmarkRunner:
    def __init__(
        self,
        evaluation_service=None,
    ):
        self.evaluation_service = evaluation_service

    async def run(
        self,
        sessions: list[dict],
    ) -> dict:

        results = []
        for session in sessions:
            result = await self.evaluate_session(session)
            results.append(result)

        return {
            "sessions": results,
            "count": len(results),
        }

    async def evaluate_session(
        self,
        session: dict,
    ) -> dict:

        return {
            "session_id": session.get("session_id"),
            "status": "evaluation_initialized",
        }