from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user_model import User


class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    def add_user(
        self,
        chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        location: Optional[str] = None,
        is_active: bool = True
    ) -> User:
        user = User(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            location=location,
            is_active=is_active,
            subscribed_at=datetime.now()
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user(self, chat_id: int) -> Optional[User]:
        stmt = select(User).where(User.chat_id == chat_id)
        return self.db.scalars(stmt).first()

    def update_user(self, chat_id: int, **kwargs) -> Optional[User]:
        user = self.get_user(chat_id)
        if not user:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def remove_user(self, chat_id: int) -> bool:
        user = self.get_user(chat_id)
        if not user:
            return False

        self.db.delete(user)
        self.db.commit()
        return True

    def get_active_users(self) -> List[User]:
        stmt = select(User).where(User.is_active)
        return list(self.db.scalars(stmt).all())

    def get_all_users(self) -> List[User]:
        stmt = select(User)
        return list(self.db.scalars(stmt).all())

    def get_users_by_location(self, location: str) -> List[User]:
        stmt = select(User).where(User.is_active, User.location == location)
        return list(self.db.scalars(stmt).all())

    def upsert_user(
        self,
        chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        location: Optional[str] = None,
        is_active: bool = True
    ) -> User:
        user = self.get_user(chat_id)
        if user:
            if username is not None:
                user.username = username
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if location is not None:
                user.location = location
            user.is_active = is_active
            self.db.commit()
            self.db.refresh(user)
            return user
        else:
            return self.add_user(
                chat_id=chat_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                location=location,
                is_active=is_active
            )
