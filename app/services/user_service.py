from typing import Optional, List
from contextlib import contextmanager
from app.config.database import get_db
from app.repositories.user_repository import UserRepository
from app.models.user_model import User


class UserService:

    @staticmethod
    @contextmanager
    def _get_repository():
        db_gen = get_db()
        db = next(db_gen)
        try:
            yield UserRepository(db)
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    def add_user(
        self,
        chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        location: Optional[str] = None,
        is_active: bool = True
    ) -> bool:
        try:
            with self._get_repository() as repo:
                repo.add_user(
                    chat_id=chat_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    location=location,
                    is_active=is_active
                )
                return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False

    def remove_user(self, chat_id: int) -> bool:
        try:
            with self._get_repository() as repo:
                return repo.remove_user(chat_id)
        except Exception as e:
            print(f"Error removing user: {e}")
            return False

    def get_user(self, chat_id: int) -> Optional[User]:
        try:
            with self._get_repository() as repo:
                return repo.get_user(chat_id)
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    def update_user(self, chat_id: int, **kwargs) -> bool:
        try:
            with self._get_repository() as repo:
                user = repo.update_user(chat_id, **kwargs)
                return user is not None
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    def get_active_users(self) -> List[User]:
        try:
            with self._get_repository() as repo:
                return repo.get_active_users()
        except Exception as e:
            print(f"Error getting active users: {e}")
            return []

    def get_all_users(self) -> List[User]:
        try:
            with self._get_repository() as repo:
                return repo.get_all_users()
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []

    def get_users_by_location(self, location: str) -> List[User]:
        try:
            with self._get_repository() as repo:
                return repo.get_users_by_location(location)
        except Exception as e:
            print(f"Error getting users by location: {e}")
            return []

    def upsert_user(
        self,
        chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        location: Optional[str] = None,
        is_active: bool = True
    ) -> Optional[User]:
        try:
            with self._get_repository() as repo:
                return repo.upsert_user(
                    chat_id=chat_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    location=location,
                    is_active=is_active
                )
        except Exception as e:
            print(f"Error upserting user: {e}")
            return None


user_service = UserService()
