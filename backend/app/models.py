from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(20), default="user")
    certificate_serial_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    sent_messages: Mapped[list["Message"]] = relationship(
        foreign_keys="Message.sender_id", back_populates="sender"
    )
    certificates: Mapped[list["UserCertificate"]] = relationship(back_populates="user")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    signature: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    sender: Mapped[User] = relationship(foreign_keys=[sender_id], back_populates="sent_messages")


class UserCertificate(Base):
    __tablename__ = "user_certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    serial_number: Mapped[str] = mapped_column(String(128), index=True)
    subject: Mapped[str] = mapped_column(String(512))
    issuer: Mapped[str] = mapped_column(String(512))
    not_before: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    not_after: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))

    user: Mapped[User] = relationship(back_populates="certificates")
