"""
JODOHKU.MY — Chat Service
Real implementation: conversations, messages, WebSocket, content filter
"""
import uuid
from datetime import datetime
from typing import Optional, Dict
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import select, desc, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import (
    Conversation, Message, ConversationStatus, MessageStatus, IceBreaker
)
from app.models.user import User, SubscriptionTier
from app.services.content_filter import ContentFilterService

# In-memory WebSocket connections: {user_id: WebSocket}
_ws_connections: Dict[str, WebSocket] = {}

# Default ice breakers
DEFAULT_ICE_BREAKERS = [
    {"text_ms": "Assalamualaikum! Apakah hobi yang paling anda minati?", "text_en": "Assalamualaikum! What is your favourite hobby?"},
    {"text_ms": "Salam kenal! Apakah impian anda dalam 5 tahun akan datang?", "text_en": "Nice to meet you! What are your dreams for the next 5 years?"},
    {"text_ms": "Apakah nilai yang paling anda utamakan dalam sebuah hubungan?", "text_en": "What values do you prioritize most in a relationship?"},
    {"text_ms": "Apakah buku atau ilmu yang sedang anda pelajari sekarang?", "text_en": "What book or knowledge are you currently learning?"},
    {"text_ms": "Bagaimana anda menghabiskan hujung minggu yang ideal?", "text_en": "How do you spend your ideal weekend?"},
]


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_conversations(self, user_id: UUID, tier: str, status: str, page: int) -> dict:
        offset = (page - 1) * 20
        query = (
            select(Conversation)
            .where(or_(
                Conversation.initiator_id == user_id,
                Conversation.recipient_id == user_id,
            ))
        )
        if status:
            try:
                query = query.where(Conversation.status == ConversationStatus(status))
            except ValueError:
                pass

        query = query.order_by(desc(Conversation.last_message_at)).offset(offset).limit(20)
        result = await self.db.execute(query)
        convos = result.scalars().all()

        items = []
        for c in convos:
            partner_id = c.recipient_id if c.initiator_id == user_id else c.initiator_id
            partner = await self.db.get(User, partner_id)
            if not partner:
                continue

            # Count unread
            unread = (await self.db.execute(
                select(func.count()).select_from(Message).where(
                    Message.conversation_id == c.id,
                    Message.sender_id != user_id,
                    Message.status != MessageStatus.READ,
                )
            )).scalar() or 0

            # Get partner's first approved photo
            from app.models.user import UserPhoto
            from sqlalchemy import select as _select
            photo_result = await self.db.execute(
                _select(UserPhoto).where(
                    UserPhoto.user_id == partner_id,
                    UserPhoto.is_approved == True,
                ).order_by(UserPhoto.sort_order).limit(1)
            )
            partner_photo = photo_result.scalar_one_or_none()
            photo_url = partner_photo.file_url if partner_photo else None

            is_blurred = tier == SubscriptionTier.RAHMAH.value
            is_online = partner.last_active_at and (datetime.utcnow() - partner.last_active_at).seconds < 300

            # Get partner display name from profile
            from app.models.user import UserProfile
            profile_result = await self.db.execute(
                _select(UserProfile).where(UserProfile.user_id == partner_id)
            )
            partner_profile = profile_result.scalar_one_or_none()
            partner_display_name = (
                partner_profile.display_name
                if partner_profile and partner_profile.display_name
                else partner.code_name
            )

            items.append({
                "id": str(c.id),
                "partner_user_id": str(partner_id),
                "partner_code_name": partner.code_name,
                "partner_display_name": partner_display_name,
                "partner_photo_url": photo_url if not is_blurred else None,
                "partner_tier": partner.current_tier.value,
                "partner": {
                    "code": partner.code_name,
                    "name": partner_display_name,
                    "score": None,
                    "online": is_online,
                    "photo_url": photo_url if not is_blurred else None,
                    "user_id": str(partner_id),
                },
                "status": c.status.value,
                "last_message": c.last_message_preview,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
                "unread_count": unread,
                "is_online": is_online,
                "is_blurred": is_blurred,
            })

        return {"conversations": items, "page": page}

    async def get_messages(self, user_id: UUID, conversation_id: UUID, before: str, limit: int) -> dict:
        # Verify user is in conversation
        convo = await self.db.get(Conversation, conversation_id)
        if not convo or (convo.initiator_id != user_id and convo.recipient_id != user_id):
            return {"messages": []}

        query = select(Message).where(Message.conversation_id == conversation_id)
        if before:
            try:
                before_dt = datetime.fromisoformat(before)
                query = query.where(Message.created_at < before_dt)
            except ValueError:
                pass

        query = query.order_by(desc(Message.created_at)).limit(limit)
        result = await self.db.execute(query)
        messages = list(reversed(result.scalars().all()))

        # Mark as read
        await self.db.execute(
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.status != MessageStatus.READ,
            )
            .values(status=MessageStatus.READ)
        )
        await self.db.flush()

        return {
            "messages": [
                {
                    "id": str(m.id),
                    "sender_id": str(m.sender_id),
                    "is_mine": m.sender_id == user_id,
                    "mine": m.sender_id == user_id,
                    "content": m.content,
                    "text": m.content,
                    "status": m.status.value,
                    "is_ice_breaker": m.is_ice_breaker,
                    "created_at": m.created_at.isoformat(),
                }
                for m in messages
            ]
        }

    async def send_message(
        self, sender_id: UUID, conversation_id: UUID,
        content: str, is_ice_breaker: bool, sender_tier: str
    ) -> dict:
        convo = await self.db.get(Conversation, conversation_id)
        if not convo:
            raise Exception("Perbualan tidak ditemui.")

        # Block messaging until recipient accepts
        if convo.status == ConversationStatus.PENDING:
            return {
                "sent": False,
                "blocked": True,
                "reason_ms": "Lamaran masih menunggu kelulusan. Anda boleh berbual setelah diterima.",
                "reason_en": "Proposal is pending acceptance. Chat will unlock once accepted.",
            }

        if convo.status == ConversationStatus.CLOSED:
            return {
                "sent": False,
                "blocked": True,
                "reason_ms": "Perbualan ini telah ditutup.",
                "reason_en": "This conversation has been closed.",
            }

        # Tier message limits
        tier_limits = {
            SubscriptionTier.RAHMAH.value: 10,
            SubscriptionTier.GOLD.value: 30,
        }
        if sender_tier in tier_limits:
            msg_count = (await self.db.execute(
                select(func.count()).select_from(Message).where(
                    Message.conversation_id == conversation_id,
                    Message.sender_id == sender_id,
                )
            )).scalar() or 0
            if msg_count >= tier_limits[sender_tier]:
                return {"sent": False, "reason_ms": f"Had mesej untuk pelan anda telah dicapai."}

        msg = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            is_ice_breaker=is_ice_breaker,
            status=MessageStatus.SENT,
        )
        self.db.add(msg)

        # Update conversation
        convo.last_message_preview = content[:100]
        convo.last_message_at = datetime.utcnow()
        convo.message_count = (convo.message_count or 0) + 1

        await self.db.flush()

        # Broadcast via WebSocket to recipient
        recipient_id = convo.recipient_id if convo.initiator_id == sender_id else convo.initiator_id
        await self._broadcast_ws(str(recipient_id), {
            "type": "message:new",
            "conversation_id": str(conversation_id),
            "content": content,
            "sender_id": str(sender_id),
        })

        return {
            "id": str(msg.id),
            "sent": True,
            "content": content,
            "created_at": msg.created_at.isoformat(),
        }

    async def initiate_conversation(
        self, initiator_id: UUID, target_id: UUID,
        first_message: str, is_ice_breaker: bool, initiator_tier: str
    ) -> dict:
        # Check if conversation already exists
        existing = await self.db.execute(
            select(Conversation).where(
                or_(
                    and_(Conversation.initiator_id == initiator_id, Conversation.recipient_id == target_id),
                    and_(Conversation.initiator_id == target_id, Conversation.recipient_id == initiator_id),
                )
            )
        )
        convo = existing.scalar_one_or_none()

        if not convo:
            convo = Conversation(
                initiator_id=initiator_id,
                recipient_id=target_id,
                status=ConversationStatus.PENDING,
                last_message_at=datetime.utcnow(),
            )
            self.db.add(convo)
            await self.db.flush()

        # Send first message
        result = await self.send_message(
            sender_id=initiator_id,
            conversation_id=convo.id,
            content=first_message,
            is_ice_breaker=is_ice_breaker,
            sender_tier=initiator_tier,
        )

        return {
            "conversation_id": str(convo.id),
            "message": result,
            "status": convo.status.value,
        }

    async def get_ice_breakers(self) -> dict:
        await self._seed_icebreakers_if_empty()
        result = await self.db.execute(select(IceBreaker).where(IceBreaker.is_active == True))
        breakers = result.scalars().all()

        if breakers:
            return {"ice_breakers": [{"id": str(b.id), "text_ms": b.text_ms, "text_en": b.text_en} for b in breakers]}
        return {"ice_breakers": [{"id": str(i), "text_ms": b["text_ms"], "text_en": b["text_en"]} for i, b in enumerate(DEFAULT_ICE_BREAKERS)]}

    async def handle_whatsapp_request(self, user_id: UUID, conversation_id: UUID, action: str, user_tier: str) -> dict:
        if user_tier == SubscriptionTier.RAHMAH.value:
            return {"success": False, "reason_ms": "Ciri ini hanya untuk pengguna Gold ke atas."}
        convo = await self.db.get(Conversation, conversation_id)
        if not convo:
            return {"success": False, "reason_ms": "Perbualan tidak ditemui."}
        return {"success": True, "action": action}

    async def record_strike(self, user_id: UUID, reason: str):
        user = await self.db.get(User, user_id)
        if user:
            user.strike_count = (user.strike_count or 0) + 1
            if user.strike_count >= 3:
                from app.models.user import AccountStatus
                user.status = AccountStatus.SUSPENDED
            await self.db.flush()

    # ── WebSocket ──

    async def register_ws_connection(self, user_id: UUID, websocket: WebSocket):
        _ws_connections[str(user_id)] = websocket

    async def unregister_ws_connection(self, user_id: UUID):
        _ws_connections.pop(str(user_id), None)

    async def handle_ws_message(self, user_id: UUID, data: dict):
        content = data.get("content", "")
        conversation_id = data.get("conversation_id")
        if content and conversation_id:
            filter_svc = ContentFilterService()
            result = filter_svc.scan_message(content)
            if not result["is_clean"]:
                await self.record_strike(user_id, result["reason"])
                ws = _ws_connections.get(str(user_id))
                if ws:
                    await ws.send_json({"type": "message:blocked", "reason_ms": result["reason_ms"]})
                return
            user = await self.db.get(User, user_id)
            tier = user.current_tier.value if user else "rahmah"
            await self.send_message(user_id, UUID(conversation_id), content, False, tier)

    async def handle_ws_read(self, user_id: UUID, data: dict):
        conversation_id = data.get("conversation_id")
        if conversation_id:
            await self.db.execute(
                update(Message)
                .where(
                    Message.conversation_id == UUID(conversation_id),
                    Message.sender_id != user_id,
                )
                .values(status=MessageStatus.READ)
            )
            await self.db.flush()

    async def broadcast_typing(self, user_id: UUID, conversation_id: str, is_typing: bool):
        convo = await self.db.get(Conversation, UUID(conversation_id))
        if convo:
            recipient_id = convo.recipient_id if convo.initiator_id == user_id else convo.initiator_id
            await self._broadcast_ws(str(recipient_id), {
                "type": "typing:start" if is_typing else "typing:stop",
                "conversation_id": conversation_id,
                "user_id": str(user_id),
            })

    async def _broadcast_ws(self, user_id: str, data: dict):
        ws = _ws_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                _ws_connections.pop(user_id, None)

    async def _seed_icebreakers_if_empty(self):
        count = (await self.db.execute(select(func.count()).select_from(IceBreaker))).scalar()
        if count and count > 0:
            return
        for b in DEFAULT_ICE_BREAKERS:
            self.db.add(IceBreaker(text_ms=b["text_ms"], text_en=b["text_en"], is_active=True))
        await self.db.flush()
