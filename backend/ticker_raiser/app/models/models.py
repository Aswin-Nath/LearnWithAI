from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, func, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid as uuid_lib
from datetime import datetime, timezone
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    role = Column(String(20), nullable=False, default="USER")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    blacklisted_tokens = relationship("BlacklistedToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("role IN ('USER', 'PROBLEM_SETTER')", name="users_role_check"),
    )


class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    jti = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid_lib.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    access_token_expires_at = Column(DateTime(timezone=True), nullable=False)
    refresh_token_expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    login_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    device_info = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
    blacklisted_tokens = relationship("BlacklistedToken", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "is_active", name="idx_sessions_user_active"),
    )


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    token_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True)
    token_type = Column(String(20), nullable=False)  # ACCESS or REFRESH
    token_value_hash = Column(Text, unique=True, nullable=False, index=True)
    revoked_type = Column(String(20), nullable=False)  # LOGOUT, TOKEN_ROTATION, SECURITY_EVENT, ADMIN_REVOKE
    reason = Column(Text, nullable=True)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="blacklisted_tokens")
    session = relationship("Session", back_populates="blacklisted_tokens")

    __table_args__ = (
        CheckConstraint("token_type IN ('ACCESS', 'REFRESH')", name="blacklisted_tokens_token_type_check"),
        CheckConstraint("revoked_type IN ('LOGOUT', 'TOKEN_ROTATION', 'SECURITY_EVENT', 'ADMIN_REVOKE')", name="blacklisted_tokens_revoked_type_check"),
    )


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    constraints = Column(Text, nullable=True)
    difficulty = Column(String(20), nullable=False)  # EASY, MEDIUM, HARD
    time_limit_ms = Column(Integer, nullable=False, default=1000)  # milliseconds
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    editorial_url_link = Column(String(500), nullable=True)  # Cloudinary PDF URL for editorial
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    creator = relationship("User")
    test_cases = relationship("TestCase", back_populates="problem", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="problem", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("difficulty IN ('EASY', 'MEDIUM', 'HARD')", name="problems_difficulty_check"),
        CheckConstraint("time_limit_ms > 0", name="problems_time_limit_positive"),
    )


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True)
    input_data = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_sample = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    problem = relationship("Problem", back_populates="test_cases")
    
    __table_args__ = (
        UniqueConstraint("problem_id", "created_at", name="idx_test_cases_problem_time"),
    )


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(Text, nullable=False)
    language = Column(String(30), nullable=False, default="python")
    status = Column(String(30), nullable=False, default="PENDING", index=True)  # PENDING, ACCEPTED, WRONG_ANSWER, RUNTIME_ERROR, TIME_LIMIT_EXCEEDED
    test_cases_passed = Column(Integer, nullable=False, default=0)
    total_test_cases = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    problem = relationship("Problem", back_populates="submissions")
    user = relationship("User")

    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'ACCEPTED', 'WRONG_ANSWER', 'RUNTIME_ERROR', 'TIME_LIMIT_EXCEEDED')", name="submissions_status_check"),
        CheckConstraint("test_cases_passed >= 0 AND test_cases_passed <= total_test_cases", name="submissions_check"),
        UniqueConstraint("user_id", "problem_id", "created_at", name="idx_submissions_user_problem_time"),
    )
