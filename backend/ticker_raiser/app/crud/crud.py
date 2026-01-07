from sqlalchemy.orm import Session
from app.models.models import ChatMessage


class ChatMessageCRUD:
    @staticmethod
    def insert_message(db: Session, user_id: int, problem_id: int, role: str, content: str) -> ChatMessage:
        """
        Insert a chat message (user or assistant) into the database.
        
        Args:
            db: Database session
            user_id: User who sent/received the message
            problem_id: Problem being discussed
            role: 'user' or 'assistant'
            content: Message content
        
        Returns:
            The created ChatMessage object
        """
        message = ChatMessage(
            user_id=user_id,
            problem_id=problem_id,
            role=role,
            content=content
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def fetch_last_n_messages(db: Session, user_id: int, problem_id: int, n: int = 10) -> list:
        """
        Fetch the last N messages for a user-problem pair.
        
        Args:
            db: Database session
            user_id: User ID
            problem_id: Problem ID
            n: Number of messages to fetch (default 10)
        
        Returns:
            List of ChatMessage rows ordered by creation time (oldest to newest)
        """
        from sqlalchemy import desc
        messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id,
            ChatMessage.problem_id == problem_id
        ).order_by(desc(ChatMessage.created_at)).limit(n).all()
        messages.reverse()
        return messages