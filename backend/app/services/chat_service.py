from __future__ import annotations

from app.schemas.api import ClarificationResponse, ConversationStatePayload
from app.services.metric_service import MetricService
from app.services.nlu import QueryParser


class ChatService:
    def __init__(self, metric_service: MetricService, parser: QueryParser) -> None:
        self.metric_service = metric_service
        self.parser = parser
        self.sessions: dict[str, ConversationStatePayload] = {}

    def handle_message(self, session_id: str, message: str) -> dict:
        state = self.sessions.setdefault(session_id, ConversationStatePayload())
        parsed = self.parser.parse(message, state)
        if parsed.clarification:
            new_state = ConversationStatePayload(
                unresolved_query=parsed.clarification["state"],
                last_query_plan=state.last_query_plan,
            )
            self.sessions[session_id] = new_state
            response = ClarificationResponse(
                message=parsed.clarification["message"],
                options=parsed.clarification["options"],
                conversation_state=new_state,
            )
            return response.model_dump()

        answer = self.metric_service.execute_plan(parsed.plan, parsed.question or message)
        resolved_state = ConversationStatePayload(unresolved_query=None, last_query_plan=parsed.plan)
        answer["conversation_state"] = resolved_state.model_dump()
        self.sessions[session_id] = resolved_state
        return answer

