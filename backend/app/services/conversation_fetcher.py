import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import grpc

logger = logging.getLogger(__name__)


@dataclass
class ConversationData:
    conversation_id: str
    end_timestamp_ns: int
    transcript_turns: list[dict] = field(default_factory=list)
    app_metadata: Optional[str] = None


class ConversationFetcher(ABC):
    @abstractmethod
    async def fetch_recent(
        self,
        tenant_id: str,
        jwt_token: str,
        since_ns: int,
        limit: int = 10,
    ) -> list[ConversationData]:
        ...


class GrpcConversationFetcher(ConversationFetcher):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    async def fetch_recent(
        self,
        tenant_id: str,
        jwt_token: str,
        since_ns: int,
        limit: int = 10,
    ) -> list[ConversationData]:
        try:
            from uniphore.conversations.v1 import conversations_pb2, conversations_pb2_grpc
        except ImportError:
            logger.error("uniphore-protos package not installed")
            return []

        channel = grpc.insecure_channel(f"{self.host}:{self.port}")
        stub = conversations_pb2_grpc.ConversationsServiceStub(channel)

        metadata = [("authorization", f"Bearer {jwt_token}")]

        group_filter = conversations_pb2.ListConversationsRequestV2.GroupFilter(
            left_filter=conversations_pb2.ListConversationsRequestV2.Filter(
                field=conversations_pb2.ListConversationsRequestV2.CONVERSATION_FIELD_END_TIMESTAMP,
                operator=conversations_pb2.ListConversationsRequestV2.CONVERSATION_FILTER_OPERATOR_GREATER_THAN_OR_EQUAL,
                number_value=float(since_ns),
            )
        )

        fields = [
            conversations_pb2.ListConversationsRequestV2.CONVERSATION_FIELD_CONVERSATION_ID,
            conversations_pb2.ListConversationsRequestV2.CONVERSATION_FIELD_END_TIMESTAMP,
            conversations_pb2.ListConversationsRequestV2.CONVERSATION_FIELD_TRANSCRIPT_TURN_ORDER,
            conversations_pb2.ListConversationsRequestV2.CONVERSATION_FIELD_TRANSCRIPT_TURN_WORDS,
            conversations_pb2.ListConversationsRequestV2.CONVERSATION_FIELD_TRANSCRIPT_TURN_PARTICIPANT_TYPE,
            conversations_pb2.ListConversationsRequestV2.CONVERSATION_FIELD_APP_METADATA,
        ]

        order_by = [
            conversations_pb2.ListConversationsRequestV2.OrderBy(
                field=conversations_pb2.ListConversationsRequestV2.CONVERSATION_FIELD_END_TIMESTAMP,
                direction=conversations_pb2.ListConversationsRequestV2.CONVERSATION_ORDER_DIRECTION_DESC,
            )
        ]

        request = conversations_pb2.ListConversationsRequestV2(
            tenant_id=tenant_id,
            environment="prod",
            group_filter=group_filter,
            fields=fields,
            order_by=order_by,
            page_size=limit,
        )

        try:
            response = stub.ListConversationsV2(request, metadata=metadata)
        except grpc.RpcError as e:
            logger.error("gRPC error fetching conversations: %s", e.code())
            return []

        results = []
        for conv in response.conversations:
            turns = []
            for order, words, ptype in zip(
                conv.transcript_turn_order,
                conv.transcript_turn_words,
                conv.transcript_turn_participant_type,
            ):
                turns.append({"order": order, "words": words, "participant_type": ptype})

            results.append(
                ConversationData(
                    conversation_id=conv.conversation_id,
                    end_timestamp_ns=conv.end_timestamp,
                    transcript_turns=turns,
                    app_metadata=conv.app_metadata if conv.app_metadata else None,
                )
            )

        return results
