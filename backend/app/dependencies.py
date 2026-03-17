from functools import lru_cache
from app.config import Settings, get_settings
from app.services.conversation_fetcher import ConversationFetcher, GrpcConversationFetcher


def get_fetcher() -> ConversationFetcher:
    settings = get_settings()
    return GrpcConversationFetcher(
        host=settings.conversations_grpc_host,
        port=settings.conversations_grpc_port,
    )
