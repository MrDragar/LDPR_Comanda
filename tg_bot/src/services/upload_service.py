import uuid
from src.domain.interfaces import IS3Storage
from src.services.interfaces import IUploadService


class UploadService(IUploadService):
    def __init__(self, s3_storage: IS3Storage):
        self.__s3_storage = s3_storage

    async def get_presigned_url(self, filename: str, content_type: str) -> dict:
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        object_key = f"uploads/{uuid.uuid4().hex}.{ext}"

        upload_url = await self.__s3_storage.generate_presigned_put_url(object_key, content_type)

        file_url = f"{self.__s3_storage.endpoint_url or 'https://s3.amazonaws.com'}/{self.__s3_storage.bucket}/{object_key}"

        return {
            "upload_url": upload_url,
            "file_url": file_url
        }
