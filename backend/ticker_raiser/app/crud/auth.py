from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from app.models.models import User, Session as DBSession, BlacklistedToken, ChatMessage
from app.core.security import  hash_token


# User CRUD
class UserCRUD:
    @staticmethod
    def create_user(db: Session, username: str, email: str, hashed_password: str, role: str = "USER") -> User:
        """Create a new user."""
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()


# Session CRUD
class SessionCRUD:
    @staticmethod
    def create_session(
        db: Session,
        session_id: str,
        jti: str,
        user_id: int,
        access_token: str,
        refresh_token: str,
        access_token_expires_at: datetime,
        refresh_token_expires_at: datetime,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> DBSession:
        """Create a new session."""
        session = DBSession(
            session_id=session_id,
            jti=jti,
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_at=access_token_expires_at,
            refresh_token_expires_at=refresh_token_expires_at,
            device_info=device_info,
            ip_address=ip_address,
            is_active=True
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_session_by_id(db: Session, session_id: str) -> Optional[DBSession]:
        """Get session by session ID."""
        return db.query(DBSession).filter(DBSession.session_id == session_id).first()

    @staticmethod
    def get_session_by_jti(db: Session, jti: str) -> Optional[DBSession]:
        """Get session by JTI."""
        return db.query(DBSession).filter(DBSession.jti == jti).first()

    @staticmethod
    def get_active_sessions_by_user(db: Session, user_id: int) -> list[DBSession]:
        """Get all active sessions for a user."""
        return db.query(DBSession).filter(
            DBSession.user_id == user_id,
            DBSession.is_active == True
        ).all()

    @staticmethod
    def mark_session_inactive(db: Session, session_id: str, reason: str = "Logout") -> Optional[DBSession]:
        """Mark a session as inactive."""
        session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
        if session:
            session.is_active = False
            session.revoked_at = datetime.now(timezone.utc)
            session.revoked_reason = reason
            db.commit()
            db.refresh(session)
        return session

    @staticmethod
    def update_last_active(db: Session, session_id: str) -> Optional[DBSession]:
        """Update last active timestamp for a session."""
        session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
        if session:
            session.last_active = datetime.now(timezone.utc)
            db.commit()
            db.refresh(session)
        return session

    @staticmethod
    def revoke_all_user_sessions(db: Session, user_id: int, reason: str = "User revoked all sessions") -> int:
        """Revoke all sessions for a user."""
        now = datetime.now(timezone.utc)
        result = db.query(DBSession).filter(
            DBSession.user_id == user_id,
            DBSession.is_active == True
        ).update({
            DBSession.is_active: False,
            DBSession.revoked_at: now,
            DBSession.revoked_reason: reason
        })
        db.commit()
        return result


# Blacklisted Token CRUD
class BlacklistedTokenCRUD:
    @staticmethod
    def add_token_to_blacklist(
        db: Session,
        user_id: int,
        token_hash: str,
        token_type: str,
        revoked_type: str="manual",
        session_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> BlacklistedToken:
        """Add a token to the blacklist."""
        blacklisted = BlacklistedToken(
            user_id=user_id,
            session_id=session_id,
            token_type=token_type,
            token_value_hash=token_hash,
            revoked_type=revoked_type,
            reason=reason
        )
        db.add(blacklisted)
        db.commit()
        db.refresh(blacklisted)
        return blacklisted

    @staticmethod
    def is_token_blacklisted(db: Session, token_hash: str) -> bool:
        """Check if a token is blacklisted."""
        return db.query(BlacklistedToken).filter(
            BlacklistedToken.token_value_hash == token_hash
        ).first() is not None

    @staticmethod
    def get_blacklisted_tokens_by_user(db: Session, user_id: int) -> list[BlacklistedToken]:
        """Get all blacklisted tokens for a user."""
        return db.query(BlacklistedToken).filter(
            BlacklistedToken.user_id == user_id
        ).all()

    @staticmethod
    def blacklist_user_refresh_tokens(
        db: Session,
        user_id: int,
        reason: str = "Token rotation"
    ) -> int:
        """Blacklist all refresh tokens for a user."""
        # Get all active sessions for the user
        sessions = db.query(DBSession).filter(
            DBSession.user_id == user_id,
            DBSession.is_active == True
        ).all()

        count = 0
        for session in sessions:
            token_hash = hash_token(session.refresh_token)
            # Check if already blacklisted
            if not BlacklistedTokenCRUD.is_token_blacklisted(db, token_hash):
                BlacklistedTokenCRUD.add_token_to_blacklist(
                    db,
                    user_id=user_id,
                    token_hash=token_hash,
                    token_type="REFRESH",
                    revoked_type="TOKEN_ROTATION",
                    session_id=str(session.session_id),
                    reason=reason
                )
                count += 1
        return count


# Chat Message CRUD
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
        
        # Reverse to get chronological order
        messages.reverse()
        return messages
