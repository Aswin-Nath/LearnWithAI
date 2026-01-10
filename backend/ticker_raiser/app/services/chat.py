from sqlalchemy.orm import Session
from typing import List
from app.core.logger import get_logger
from app.crud.chat import ChatMessageCRUD
from app.models.models import ChatMessage

logger =get_logger("chat_service")


class ChatService:
    """Service for managing chat messages and conversation history."""

    @staticmethod
    def insert_user_message(
        db: Session,
        user_id: int,
        problem_id: int,
        content: str
    ) -> ChatMessage:
        """
        Insert a user message into the database.
        
        Args:
            db: Database session
            user_id: User ID
            problem_id: Problem ID
            content: Message content
        
        Returns:
            Created ChatMessage object
        """
        return ChatMessageCRUD.insert_message(
            db=db,
            user_id=user_id,
            problem_id=problem_id,
            role="user",
            content=content
        )

    @staticmethod
    def insert_ai_message(
        db: Session,
        user_id: int,
        problem_id: int,
        content: str
    ) -> ChatMessage:
        """
        Insert an AI/assistant message into the database.
        
        Args:
            db: Database session
            user_id: User ID
            problem_id: Problem ID
            content: Message content
        
        Returns:
            Created ChatMessage object
        """
        return ChatMessageCRUD.insert_message(
            db=db,
            user_id=user_id,
            problem_id=problem_id,
            role="assistant",
            content=content
        )

    @staticmethod
    def get_conversation_history(
        db: Session,
        user_id: int,
        problem_id: int,
        limit: int = 10
    ) -> List[ChatMessage]:
        """
        Get conversation history for a user-problem pair.
        
        Args:
            db: Database session
            user_id: User ID
            problem_id: Problem ID
            limit: Number of recent messages to retrieve (default: 10)
        
        Returns:
            List of ChatMessage objects ordered chronologically (oldest to newest)
        """
        messages = ChatMessageCRUD.fetch_last_n_messages(
            db=db,
            user_id=user_id,
            problem_id=problem_id,
            n=limit
        )
        logger.debug(
            f"[ChatService] Retrieved {len(messages)} messages for "
            f"user_id={user_id}, problem_id={problem_id}"
        )
        return messages

    @staticmethod
    def insert_conversation_pair(
        db: Session,
        user_id: int,
        problem_id: int,
        user_content: str,
        ai_content: str
    ) -> tuple[ChatMessage, ChatMessage]:
        """
        Insert both user and AI messages atomically.
        Ensures conversation coherence by inserting both messages together.
        
        Args:
            db: Database session
            user_id: User ID
            problem_id: Problem ID
            user_content: User message content
            ai_content: AI response content
        
        Returns:
            Tuple of (user_message, ai_message)
        
        Raises:
            Exception: If either message insertion fails
        """
        try:
            user_msg = ChatService.insert_user_message(
                db=db,
                user_id=user_id,
                problem_id=problem_id,
                content=user_content
            )
            
            ai_msg = ChatService.insert_ai_message(
                db=db,
                user_id=user_id,
                problem_id=problem_id,
                content=ai_content
            )
            
            logger.info(
                f"[ChatService] ✓ Inserted conversation pair for "
                f"user_id={user_id}, problem_id={problem_id}"
            )
            return user_msg, ai_msg
            
        except Exception as e:
            logger.error(
                f"[ChatService]  Failed to insert conversation pair: {str(e)}",
                exc_info=True
            )
            raise
