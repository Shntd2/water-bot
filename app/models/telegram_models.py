from typing import Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field
import json
from pathlib import Path


class User(BaseModel):
    chat_id: int = Field(..., description="Telegram chat ID")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    location: Optional[str] = Field(None, description="Water alert location to monitor")
    subscribed_at: datetime = Field(default_factory=datetime.now, description="Subscription timestamp")
    is_active: bool = Field(default=True, description="Whether the subscription is active")
    last_notified: Optional[datetime] = Field(None, description="Last notification timestamp")
    last_location_changed: Optional[datetime] = Field(None, description="Last location change timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserDatabase:

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).resolve().parent.parent / "data" / "users.json"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._users: dict[int, User] = {}
        self._load()

    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for chat_id_str, user_data in data.items():
                        chat_id = int(chat_id_str)
                        if 'subscribed_at' in user_data:
                            user_data['subscribed_at'] = datetime.fromisoformat(user_data['subscribed_at'])
                        if user_data.get('last_notified'):
                            user_data['last_notified'] = datetime.fromisoformat(user_data['last_notified'])
                        if user_data.get('last_location_changed'):
                            user_data['last_location_changed'] = datetime.fromisoformat(user_data['last_location_changed'])
                        self._users[chat_id] = User(**user_data)
            except Exception as e:
                print(f"Error loading user database: {e}")
                self._users = {}

    def _save(self):
        try:
            data = {}
            for chat_id, user in self._users.items():
                data[str(chat_id)] = user.model_dump(mode='json')

            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving user database: {e}")

    def add_user(self, user: User) -> bool:
        self._users[user.chat_id] = user
        self._save()
        return True

    def remove_user(self, chat_id: int) -> bool:
        if chat_id in self._users:
            del self._users[chat_id]
            self._save()
            return True
        return False

    def get_user(self, chat_id: int) -> Optional[User]:
        return self._users.get(chat_id)

    def update_user(self, chat_id: int, **kwargs) -> bool:
        if chat_id in self._users:
            user = self._users[chat_id]
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            self._save()
            return True
        return False

    def get_active_users(self) -> list[User]:
        return [user for user in self._users.values() if user.is_active]

    def get_all_users(self) -> list[User]:
        return list(self._users.values())

    def get_users_by_location(self, location: str) -> list[User]:
        return [
            user for user in self._users.values()
            if user.is_active and user.location == location
        ]


user_db = UserDatabase()
