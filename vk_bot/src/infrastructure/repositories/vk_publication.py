import logging
from urllib.parse import urlencode

import aiohttp

from src.domain.interfaces import IVKPublicationRepository

logger = logging.getLogger(__name__)


class VKPublicationRepository(IVKPublicationRepository):
    def __init__(
            self,
            token: str,
            group_id: int | str | None,
            photo_token: str | None = None,
            api_version: str = "5.199"
    ):
        self.__token = token
        self.__photo_token = photo_token or token
        self.__group_id = int(group_id) if group_id else None
        self.__api_version = api_version

    async def publish_headliner(
            self,
            name: str,
            description: str,
            photo: str | None
    ) -> int | None:
        if not self.__token or not self.__group_id:
            raise RuntimeError("VK_API_TOKEN or GROUP_ID is missing.")

        attachment = None
        if photo:
            try:
                attachment = await self.__upload_wall_photo(photo)
            except Exception as e:
                logger.warning(f"Failed to upload wall photo, post will be created without attachment: {e}")

        message = f"{name}\n\n{description}"
        if photo and not attachment:
            message = f"{message}\n\nФото: {photo}"
        response = await self.__vk_call("wall.post", {
            "owner_id": -self.__group_id,
            "from_group": 1,
            "message": message[:4096],
            "attachments": attachment,
        })
        return response.get("post_id")

    async def __upload_wall_photo(self, photo_url: str) -> str | None:
        photo_bytes = await self.__download_photo_bytes(photo_url)
        if not photo_bytes:
            return None

        upload_server = await self.__vk_call(
            "photos.getWallUploadServer",
            {"group_id": self.__group_id},
            token=self.__photo_token
        )
        upload_url = upload_server["upload_url"]

        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field(
                "photo",
                photo_bytes,
                filename="headliner.jpg",
                content_type="image/jpeg"
            )
            async with session.post(upload_url, data=form) as upload_response:
                upload_data = await upload_response.json(content_type=None)

        saved = await self.__vk_call("photos.saveWallPhoto", {
            "group_id": self.__group_id,
            "photo": upload_data.get("photo"),
            "server": upload_data.get("server"),
            "hash": upload_data.get("hash"),
        }, token=self.__photo_token)
        if not saved:
            return None

        photo = saved[0]
        return f"photo{photo['owner_id']}_{photo['id']}"

    @staticmethod
    async def __download_photo_bytes(photo_url: str) -> bytes | None:
        if not photo_url.startswith(("http://", "https://")):
            return None

        async with aiohttp.ClientSession() as session:
            async with session.get(photo_url) as response:
                response.raise_for_status()
                return await response.read()

    async def __vk_call(self, method: str, params: dict, token: str | None = None):
        call_params = {
            **{key: value for key, value in params.items() if value is not None},
            "access_token": token or self.__token,
            "v": self.__api_version
        }
        url = f"https://api.vk.ru/method/{method}"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=urlencode(call_params)) as response:
                data = await response.json(content_type=None)

        if "error" in data:
            error = data["error"]
            raise RuntimeError(
                f"VK API {method} error {error.get('error_code')}: "
                f"{error.get('error_msg')}"
            )
        return data.get("response")
