
# to build and maintain context supplied to agent decisions

class ContextManager:
    def __init__(
        self,
        short_term_memory=None,
        long_term_memory=None,
        context_distiller=None,
    ):
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.context_distiller = context_distiller

    async def get_context(
        self,
        session_id: str,
    ) -> dict:
        short_term = {}
        long_term = {}

        if self.short_term_memory:
            short_term = await self.short_term_memory.get(session_id)

        if self.long_term_memory:
            long_term = await self.long_term_memory.get(session_id)

        return {
            "session_id": session_id,
            "short_term": short_term,
            "long_term": long_term,
        }

    # persist contextual info
    async def update_context(
        self,
        session_id: str,
        context: dict,
    ) -> dict:
        if self.context_distiller:
            context = await self.context_distiller.distill(context)

        if self.short_term_memory:
            await self.short_term_memory.update(
                session_id,
                context.get("short_term", {}),
            )

        if self.long_term_memory:
            await self.long_term_memory.update(
                session_id,
                context.get("long_term", {}),
            )

        return context