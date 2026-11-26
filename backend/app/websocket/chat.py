import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Message, User, utc_now
from app.security import COOKIE_NAME, decode_access_token
from app.websocket.connections import connection_manager


router = APIRouter()
MAX_MESSAGE_LENGTH = 2000


def wire_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def error_message(request_id: Optional[str], code: str, message: str) -> dict:
    return {
        "type": "error",
        "requestId": request_id,
        "payload": {"code": code, "message": message},
    }


@router.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket, db: Session = Depends(get_db)):
    token = websocket.cookies.get(COOKIE_NAME)
    if not token:
        await websocket.close(code=4401)
        return
    try:
        user_id = decode_access_token(token)
    except (jwt.InvalidTokenError, ValueError):
        await websocket.close(code=4401)
        return

    if db.get(User, user_id) is None:
        await websocket.close(code=4401)
        return

    await connection_manager.connect(user_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            request_id = None
            try:
                event = json.loads(raw)
                request_id_value = event.get("requestId")
                if isinstance(request_id_value, str):
                    request_id = str(UUID(request_id_value))
                if event.get("type") != "privateMessage":
                    raise ValueError("UNSUPPORTED_MESSAGE")
                payload = event.get("payload")
                if not isinstance(payload, dict):
                    raise ValueError("INVALID_MESSAGE")
                receiver_id = payload.get("receiverId")
                content = payload.get("content")
                if not isinstance(receiver_id, int) or isinstance(receiver_id, bool):
                    raise ValueError("INVALID_MESSAGE")
                if not isinstance(content, str) or not content.strip() or len(content) > MAX_MESSAGE_LENGTH:
                    raise ValueError("INVALID_MESSAGE")
            except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
                await websocket.send_json(error_message(request_id, "VALIDATION_ERROR", "消息格式无效"))
                continue

            sender = db.get(User, user_id)
            receiver = db.get(User, receiver_id)
            if sender is None:
                await websocket.send_json(error_message(request_id, "UNAUTHORIZED", "登录已失效，请重新登录"))
                await websocket.close(code=4401)
                return
            if receiver is None:
                await websocket.send_json(error_message(request_id, "NOT_FOUND", "接收用户不存在"))
                continue
            message = Message(
                sender_id=sender.id,
                receiver_id=receiver.id,
                content=content.strip(),
                created_at=utc_now(),
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            created_at = wire_datetime(message.created_at)
            message_id = message.id
            sender_id = sender.id
            sender_name = sender.display_name

            await websocket.send_json(
                {
                    "type": "messageAccepted",
                    "requestId": request_id,
                    "payload": {"messageId": message_id, "createdAt": created_at},
                }
            )
            await connection_manager.send_user(
                receiver_id,
                {
                    "type": "messageReceived",
                    "requestId": request_id,
                    "payload": {
                        "id": message_id,
                        "senderId": sender_id,
                        "senderName": sender_name,
                        "receiverId": receiver_id,
                        "content": content.strip(),
                        "createdAt": created_at,
                        "signatureStatus": "unverified",
                    },
                },
            )
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect(user_id, websocket)
