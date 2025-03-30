from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from ..database.models import ChatLog
from ..models import ChatLogCreate
import uuid

class ChatLogService:
    def __init__(self, db: Session):
        self.db = db

    def create_chat_log(self, chat_log: ChatLogCreate) -> ChatLog:
        """Create a new chat log entry."""
        db_chat_log = ChatLog(
            id=str(uuid.uuid4()),
            agent_id=chat_log.agent_id,
            request_message=chat_log.request_message,
            response_message=chat_log.response_message,
            input_tokens=chat_log.input_tokens,
            output_tokens=chat_log.output_tokens,
            total_tokens=chat_log.total_tokens,
            requestor_id=chat_log.requestor_id,
            model_name=chat_log.model_name,
            duration_ms=chat_log.duration_ms,
            status=chat_log.status,
            error_message=chat_log.error_message,
            metadata=chat_log.metadata
        )
        self.db.add(db_chat_log)
        self.db.commit()
        self.db.refresh(db_chat_log)
        return db_chat_log

    def get_chat_logs_by_agent(self, agent_id: str) -> List[ChatLog]:
        """Get all chat logs for a specific agent."""
        return self.db.query(ChatLog).filter(ChatLog.agent_id == agent_id).all()

    def get_chat_logs_by_timerange(self, start_time: datetime, end_time: datetime) -> List[ChatLog]:
        """Get chat logs within a specific time range."""
        return self.db.query(ChatLog).filter(
            ChatLog.timestamp >= start_time,
            ChatLog.timestamp <= end_time
        ).all()

    def get_chat_log(self, chat_log_id: str) -> Optional[ChatLog]:
        """Get a specific chat log by ID."""
        return self.db.query(ChatLog).filter(ChatLog.id == chat_log_id).first()

    def get_token_usage_by_agent(self, agent_id: str) -> dict:
        """Get total token usage statistics for an agent."""
        logs = self.db.query(ChatLog).filter(ChatLog.agent_id == agent_id).all()
        return {
            "total_input_tokens": sum(log.input_tokens for log in logs),
            "total_output_tokens": sum(log.output_tokens for log in logs),
            "total_tokens": sum(log.total_tokens for log in logs),
            "total_interactions": len(logs)
        } 