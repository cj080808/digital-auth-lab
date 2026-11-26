from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Message, User
from app.schemas import MessagePage, MessageResponse, success
from app.websocket.connections import connection_manager


router = APIRouter(tags=["chat"])


@router.get("/api/users/online")
def online_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    online_ids = connection_manager.online_user_ids() - {current_user.id}
    if not online_ids:
        return success([])
    users = db.query(User).filter(User.id.in_(online_ids)).order_by(User.username).all()
    return success(
        [
            {
                "id": user.id,
                "username": user.username,
                "displayName": user.display_name,
                "online": True,
            }
            for user in users
        ]
    )


@router.get("/api/messages/private/{user_id}")
def private_messages(
    user_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, alias="pageSize", ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="NOT_FOUND")

    conversation = or_(
        and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
        and_(Message.sender_id == user_id, Message.receiver_id == current_user.id),
    )
    total = db.query(func.count(Message.id)).filter(conversation).scalar() or 0
    rows = (
        db.query(Message)
        .filter(conversation)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    rows.reverse()
    result = MessagePage(
        items=[MessageResponse.model_validate(row, from_attributes=True) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
    return success(result)
