from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserStorage:
    """
    Данные одного пользователя во время создания контента.
    """

    channel: Optional[str] = None

    description: str = ""

    post: str = ""

    photos: list[str] = field(default_factory=list)

    photo_mode: str = "normal"

    before_photo: Optional[str] = None

    after_photo: Optional[str] = None

    generated_image: Optional[bytes] = None

    image_descriptions: list[str] = field(
        default_factory=list
    )


class Storage:
    """
    Простое хранилище пользователей.

    Пока данные находятся в памяти.
    Позже при необходимости можем заменить
    его на SQLite/PostgreSQL, не меняя логику бота.
    """

    def __init__(self):

        self.users: dict[int, UserStorage] = {}


    def get(self, user_id: int) -> UserStorage:

        if user_id not in self.users:

            self.users[user_id] = UserStorage()

        return self.users[user_id]


    def reset(self, user_id: int):

        self.users.pop(
            user_id,
            None,
        )


    def exists(self, user_id: int) -> bool:

        return user_id in self.users


    def clear_photos(self, user_id: int):

        user = self.get(user_id)

        user.photos.clear()

        user.before_photo = None

        user.after_photo = None

        user.generated_image = None


    def add_photo(
        self,
        user_id: int,
        photo_id: str,
    ):

        user = self.get(user_id)

        user.photos.append(photo_id)


    def set_channel(
        self,
        user_id: int,
        channel: str,
    ):

        user = self.get(user_id)

        user.channel = channel


    def set_description(
        self,
        user_id: int,
        description: str,
    ):

        user = self.get(user_id)

        user.description = description


    def set_post(
        self,
        user_id: int,
        post: str,
    ):

        user = self.get(user_id)

        user.post = post


    def set_before_photo(
        self,
        user_id: int,
        photo_id: str,
    ):

        user = self.get(user_id)

        user.before_photo = photo_id


    def set_after_photo(
        self,
        user_id: int,
        photo_id: str,
    ):

        user = self.get(user_id)

        user.after_photo = photo_id


    def set_image_descriptions(
        self,
        user_id: int,
        descriptions: list[str],
    ):

        user = self.get(user_id)

        user.image_descriptions = descriptions


# =========================================================
# GLOBAL STORAGE
# =========================================================

storage = Storage()
