from sqlalchemy import Column, String, Boolean, DateTime, BigInteger, text
from sqlalchemy.sql import func
from app.config.database import Base


class User(Base):

    __tablename__ = "users"

    chat_id = Column(
        BigInteger,
        primary_key=True,
        index=True,
        comment="Telegram chat ID"
    )

    username = Column(
        String(255),
        nullable=True,
        comment="Telegram username"
    )
    first_name = Column(
        String(255),
        nullable=True,
        comment="User's first name"
    )
    last_name = Column(
        String(255),
        nullable=True,
        comment="User's last name"
    )

    location = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Water alert location to monitor"
    )
    is_active = Column(
        Boolean,
        nullable=False,
        server_default=text('true'),
        index=True,
        comment="Whether the subscription is active"
    )

    subscribed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Subscription timestamp"
    )
    last_notified = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last notification timestamp"
    )
    last_location_changed = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last location change timestamp"
    )

    def __repr__(self) -> str:
        return (
            f"<User(chat_id={self.chat_id}, "
            f"username={self.username}, "
            f"location={self.location}, "
            f"is_active={self.is_active})>"
        )

    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "location": self.location,
            "is_active": self.is_active,
            "subscribed_at": self.subscribed_at.isoformat() if self.subscribed_at else None,
            "last_notified": self.last_notified.isoformat() if self.last_notified else None,
            "last_location_changed": self.last_location_changed.isoformat() if self.last_location_changed else None,
        }
