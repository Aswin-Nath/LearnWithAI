from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.crud.auth import UserCRUD

_logger = logging.getLogger(__name__)


async def get_current_user(
    user_id: str = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user from X-User-Id header.
    
    Simple authentication without JWT - frontend sends user ID in header.
    
    Args:
        user_id (str): User ID from X-User-Id header
        db (Session): Database session
    
    Returns:
        User: Current authenticated user
    
    Raises:
        HTTPException (401): If user_id is missing or user not found
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    try:
        user = UserCRUD.get_user_by_id(db, int(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return user
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID"
        )
    except Exception as e:
        _logger.debug("User retrieval failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

