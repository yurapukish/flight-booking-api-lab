from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from sqlalchemy import select


def require_admin(
        x_user_email: str = Header(...),
        db: Session = Depends(get_db),
) -> User:
    """Отримати інформацію чи адмін."""
    query = select(User).where(User.email == x_user_email)

    user_info = db.execute(query).scalar_one_or_none()
    if user_info is None:
        raise HTTPException(401, "Unknown user")
    if not user_info.is_admin:
        raise HTTPException(403, "Admin required")

    return user_info
