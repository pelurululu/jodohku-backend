"""
JODOHKU.MY — Chat Routes
Text-only messaging with content filtering and strike enforcement
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ConversationResponse, MessageRequest, MessageResponse,
    WhatsAppRequestAction
)
from app.services.chat_service import ChatService
from app.services.content_filter import ContentFilterService
from app.middleware.auth import get_current_user, get_ws_user

router = APIRouter(prefix="/chat", tags=["Chat & Messaging"])


@router.get("/conversations")
async def get_conversations(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all conversations.
    Sorted by last_message_at descending.
    Shows partner photo (blurred for Rahmah tier).
    """
    service = ChatService(db)
    return await service.get_conversations(
        current_user.id, current_user.current_tier, status, page
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: UUID,
    before: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages in a conversation. Paginated with cursor."""
    service = ChatService(db)
    return await service.get_messages(
        current_user.id, conversation_id, before, limit
    )


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    request: MessageRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a text message.
    
    Content filtering:
    - Regex scan for URLs (https, bitly, tinyurl)
    - Regex scan for phone number requests (whatsapp, 01, fon, tepon, num)
    - Blocked messages trigger strike system
    
    Tier limits enforced:
    - Rahmah: 10 msgs/profile, 3 concurrent chats
    - Gold: 30 msgs/profile, 10 concurrent chats
    - Platinum+: Unlimited
    """
    # Content filter check
    filter_service = ContentFilterService()
    filter_result = filter_service.scan_message(request.content)
    
    if not filter_result["is_clean"]:
        service = ChatService(db)
        await service.record_strike(current_user.id, filter_result["reason"])
        return {
            "sent": False,
            "blocked": True,
            "reason_ms": filter_result["reason_ms"],
            "reason_en": filter_result["reason_en"],
            "strike_count": filter_result.get("new_strike_count"),
        }
    
    service = ChatService(db)
    result = await service.send_message(
        sender_id=current_user.id,
        conversation_id=conversation_id,
        content=request.content,
        is_ice_breaker=request.is_ice_breaker,
        sender_tier=current_user.current_tier,
    )
    return result


@router.post("/initiate")
async def initiate_conversation(
    target_user_id: UUID,
    message: MessageRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate conversation (Lamar).
    Requires at least 1 message (ice-breaker or custom).
    Target receives notification.
    """
    service = ChatService(db)
    result = await service.initiate_conversation(
        initiator_id=current_user.id,
        target_id=target_user_id,
        first_message=message.content,
        is_ice_breaker=message.is_ice_breaker,
        initiator_tier=current_user.current_tier,
    )
    return result


@router.get("/ice-breakers")
async def get_ice_breakers(
    db: AsyncSession = Depends(get_db),
):
    """Get list of available ice-breaker phrases."""
    service = ChatService(db)
    return await service.get_ice_breakers()


# ─── WhatsApp Sharing ───

@router.post("/whatsapp")
async def whatsapp_action(
    request: WhatsAppRequestAction,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    WhatsApp number sharing (Gold+ tier only).
    
    Protocol:
    - Max 3 requests/day (reset 8 AM)
    - Recipient chooses Accept or Reject
    - Rejection locks button for 30 minutes
    - Minimum 5 messages exchanged before eligible
    """
    service = ChatService(db)
    return await service.handle_whatsapp_request(
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        action=request.action,
        user_tier=current_user.current_tier,
    )


# ─── WebSocket Real-time Messaging ───

@router.websocket("/ws/{token}")
async def websocket_chat(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket connection for real-time messaging.
    
    Events:
    - message:new — new message received
    - message:read — message read by recipient
    - user:online — user came online
    - user:offline — user went offline
    - typing:start / typing:stop — typing indicators
    """
    await websocket.accept()
    
    try:
        user = await get_ws_user(token, db)
        if not user:
            await websocket.close(code=4001, reason="Unauthorized")
            return
        
        service = ChatService(db)
        await service.register_ws_connection(user.id, websocket)
        
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            
            if event_type == "message:send":
                await service.handle_ws_message(user.id, data)
            elif event_type == "message:read":
                await service.handle_ws_read(user.id, data)
            elif event_type == "typing:start":
                await service.broadcast_typing(user.id, data["conversation_id"], True)
            elif event_type == "typing:stop":
                await service.broadcast_typing(user.id, data["conversation_id"], False)
    
    except WebSocketDisconnect:
        await service.unregister_ws_connection(user.id)
    except Exception:
        await websocket.close(code=4000)
