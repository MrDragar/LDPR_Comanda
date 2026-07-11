import aioboto3
import boto3
import asyncio
from src.domain.interfaces import IS3Storage


class S3Storage(IS3Storage):
    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str, endpoint_url: str | None = None):
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint_url = endpoint_url
        self.session = aioboto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key)

    async def upload_photo(self, file_bytes: bytes, filename: str) -> str:
        async with self.session.client("s3", region_name=self.region, endpoint_url=self.endpoint_url) as s3:
            await s3.put_object(Bucket=self.bucket, Key=filename, Body=file_bytes,
                                ContentType="image/jpeg", ACL='public-read')
            endpoint = self.endpoint_url or 'https://s3.amazonaws.com'
            return f"{endpoint}/{self.bucket}/{filename}"

    async def generate_presigned_put_url(self, object_key: str, content_type: str, expires_in: int = 3600) -> str:
        def _sync_generate():
            client = boto3.client(
                's3',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=self.endpoint_url,
                region_name=self.region
            )
            return client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket, 'Key': object_key, 'ContentType': content_type,
                    'ACL': 'public-read'
                },
                ExpiresIn=expires_in
            )
        return await asyncio.to_thread(_sync_generate)
