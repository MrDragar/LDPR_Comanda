import aioboto3
from src.domain.interfaces import IS3Storage


class S3Storage(IS3Storage):
    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str, endpoint_url: str | None = None):
        self.bucket = bucket
        self.session = aioboto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        self.endpoint_url = endpoint_url
        self.region = region

    async def upload_photo(self, file_bytes: bytes, filename: str) -> str:
        async with self.session.client("s3", region_name=self.region, endpoint_url=self.endpoint_url) as s3:
            await s3.put_object(Bucket=self.bucket, Key=filename, Body=file_bytes, 
                                ContentType="image/jpeg", ACL='public-read')
            return f"{self.endpoint_url or 'https://s3.amazonaws.com'}/{self.bucket}/{filename}"
