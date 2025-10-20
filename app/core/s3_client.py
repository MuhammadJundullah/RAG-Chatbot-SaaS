import aiobotocore.session
from aiobotocore.config import AioConfig
from app.core.config import settings
import logging

class AsyncS3Client:
    def __init__(self):
        self.session = aiobotocore.session.get_session()
        self._client = None

    async def get_client(self):
        if self._client is None:
            try:
                config = AioConfig(signature_version='s3v4')
                self._client = await self.session.create_client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL,
                    aws_access_key_id=settings.S3_AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.S3_AWS_SECRET_ACCESS_KEY,
                    config=config
                ).__aenter__()
            except Exception as e:
                logging.error(f"Failed to create S3 client. Check your .env settings. Error: {e}")
                raise
        return self._client

    async def close(self):
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

s3_client_manager = AsyncS3Client()