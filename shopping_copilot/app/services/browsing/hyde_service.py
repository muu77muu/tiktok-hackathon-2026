
# to provide HyDE (Hypothetical Document Embedding) support for highly semantic / abstract browsing queries

class HydeService:
    async def generate_hypothetical_document(
        self,
        query: str,
        scenario: dict | None = None,
    ) -> str | None:
        return None

    def should_use_hyde(
        self,
        query: str,
        scenario: dict | None = None,
    ) -> bool:
        return False