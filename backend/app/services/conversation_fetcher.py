import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import grpc
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ConversationData:
    conversation_id: str
    end_timestamp_ns: int
    transcript_turns: list[dict] = field(default_factory=list)
    generated_summary: Optional[str] = None


class ConversationFetcher(ABC):
    @abstractmethod
    async def fetch_recent(
        self,
        tenant_id: str,
        jwt_token: str,
        since_ns: int,
        limit: int = 10,
        environment: Optional[str] = None,
        experience_id: Optional[str] = None,
    ) -> list[ConversationData]:
        ...


class GrpcConversationFetcher(ConversationFetcher):
    def __init__(self, host: str, port: int, rest_base_url: str, environment: str = "prod"):
        self.host = host
        self.port = port
        self.rest_base_url = rest_base_url.rstrip("/")
        self.environment = environment

    async def fetch_recent(
        self,
        tenant_id: str,
        jwt_token: str,
        since_ns: int,
        limit: int = 10,
        environment: Optional[str] = None,
        experience_id: Optional[str] = None,
    ) -> list[ConversationData]:
        env = environment or self.environment

        # Step 1: Fetch conversation IDs and end timestamps via gRPC
        conv_ids = await self._fetch_conversation_ids(
            tenant_id, jwt_token, since_ns, limit, env, experience_id
        )
        if not conv_ids:
            return []

        # Step 2: Fetch full details per conversation via REST
        results = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for conv_id, end_ts_ns in conv_ids:
                data = await self._fetch_conversation_details(
                    client, tenant_id, conv_id, end_ts_ns, jwt_token, env
                )
                if data is not None:
                    results.append(data)

        return results

    async def _fetch_conversation_ids(
        self,
        tenant_id: str,
        jwt_token: str,
        since_ns: int,
        limit: int,
        environment: str,
        experience_id: Optional[str] = None,
    ) -> list[tuple[str, int]]:
        try:
            from uniphore.conversations.v1 import service_pb2, service_pb2_grpc
        except ImportError:
            logger.error("uniphore-protos package not installed")
            return []

        from google.protobuf.timestamp_pb2 import Timestamp

        Req = service_pb2.ListConversationsRequestV2

        credentials = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel(f"{self.host}:{self.port}", credentials)
        stub = service_pb2_grpc.ConversationsServiceStub(channel)

        metadata = [("authorization", f"Bearer {jwt_token}")]

        since_ts = Timestamp(
            seconds=since_ns // 1_000_000_000,
            nanos=since_ns % 1_000_000_000,
        )
        time_filter = Req.Filter(
            field=Req.CONVERSATION_FIELD_END_TIMESTAMP,
            operator=Req.CONVERSATION_FILTER_OPERATOR_GREATER_THAN_OR_EQUAL,
            timestamp_value=since_ts,
        )

        if experience_id:
            group_filter = Req.GroupFilter(
                left_filter=time_filter,
                right_filter=Req.Filter(
                    field=Req.CONVERSATION_FIELD_CONVERSATION_EXPERIENCE_ID,
                    operator=Req.CONVERSATION_FILTER_OPERATOR_EQUAL,
                    string_value=experience_id,
                ),
                operator=Req.CONVERSATION_LOGICAL_OPERATOR_AND,
            )
        else:
            group_filter = Req.GroupFilter(
                left_filter=time_filter,
            )

        fields = [
            Req.CONVERSATION_FIELD_CONVERSATION_ID,
            Req.CONVERSATION_FIELD_END_TIMESTAMP,
        ]

        order_by = [
            Req.OrderBy(
                field=Req.CONVERSATION_FIELD_END_TIMESTAMP,
                direction=Req.CONVERSATION_ORDER_DIRECTION_DESC,
            )
        ]

        request = Req(
            tenant_id=tenant_id,
            environment=environment,
            group_filter=group_filter,
            fields=fields,
            order_by=order_by,
            page_size=limit,
        )

        try:
            response = stub.ListConversationsV2(request, metadata=metadata)
        except grpc.RpcError as e:
            logger.error("gRPC error fetching conversation IDs: %s", e)
            return []

        results = []
        for conv in response.conversations:
            ts = conv.session.end_timestamp
            end_ns = ts.seconds * 1_000_000_000 + ts.nanos
            results.append((conv.conversation_id, end_ns))
        logger.info("gRPC returned %d conversation IDs", len(results))
        return results

    async def _fetch_conversation_details(
        self,
        client: httpx.AsyncClient,
        tenant_id: str,
        conversation_id: str,
        end_timestamp_ns: int,
        jwt_token: str,
        environment: str,
    ) -> Optional[ConversationData]:
        url = f"{self.rest_base_url}/diana/v2/conversations/{tenant_id}/{conversation_id}"
        params = {"environment": environment}
        headers = {
            "X-Source": "service",
            "X-Tenant-Id": tenant_id,
            "Authorization": f"Bearer {jwt_token}",
        }

        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "REST error fetching conversation %s: HTTP %s",
                conversation_id,
                e.response.status_code,
            )
            return ConversationData(
                conversation_id=conversation_id,
                end_timestamp_ns=end_timestamp_ns,
            )
        except Exception:
            logger.exception("Unexpected error fetching conversation %s", conversation_id)
            return ConversationData(
                conversation_id=conversation_id,
                end_timestamp_ns=end_timestamp_ns,
            )

        # Extract transcript turns — words are objects with a "text" field
        turns = []
        transcript_data = body.get("transcript") or {}
        for turn in transcript_data.get("turns", []):
            words_text = " ".join(
                w["text"] for w in turn.get("words", []) if isinstance(w, dict) and w.get("text")
            )
            turns.append({
                "order": turn.get("order", 0),
                "words": words_text,
                "participant_type": turn.get("participantType", "UNKNOWN"),
            })

        # Extract generated summary from summary.genAiSummary.sections
        generated_summary = None
        summary_data = body.get("summary") or {}
        gen_ai = summary_data.get("genAiSummary") or {}
        sections = gen_ai.get("sections") or []
        if sections:
            generated_summary = "\n".join(
                f"{s['id']}: {s['text']}"
                for s in sections
                if isinstance(s, dict) and s.get("text")
            ) or None

        return ConversationData(
            conversation_id=conversation_id,
            end_timestamp_ns=end_timestamp_ns,
            transcript_turns=turns,
            generated_summary=generated_summary,
        )
