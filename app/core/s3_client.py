import aiobotocore.session
from aiobotocore.config import AioConfig
from app.core.config import settings
import logging
import io

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

    async def upload_file(self, file_object: io.BytesIO, bucket_name: str, file_key: str, content_type: str = None) -> str:
        """
        Uploads a file-like object to an S3 bucket.

        Args:
            file_object: A file-like object in binary mode (e.g., opened with 'rb').
            bucket_name: The name of the S3 bucket.
            file_key: The desired key (path) for the file in the bucket.
            content_type: The MIME type of the file (e.g., 'image/jpeg').

        Returns:
            The S3 URL of the uploaded file.
        """
        client = await self.get_client()
        try:
            put_object_params = {
                "Bucket": bucket_name,
                "Key": file_key,
                "Body": file_object.read()
            }
            if content_type:
                put_object_params["ContentType"] = content_type

            await client.put_object(**put_object_params)
            
            s3_url = f"{settings.S3_ENDPOINT_URL}/{bucket_name}/{file_key}"
            logging.info(f"Successfully uploaded file to {s3_url}")
            return s3_url
        except Exception as e:
            logging.error(f"Failed to upload file to S3: {e}")
            raise

    async def delete_file(self, bucket_name: str, file_key: str):
        """
        Deletes a file from an S3 bucket using delete_objects.

        Args:
            bucket_name: The name of the S3 bucket.
            file_key: The key (path) of the file to delete in the bucket.
        """
        client = await self.get_client()
        try:
            await client.delete_objects(
                Bucket=bucket_name,
                Delete={
                    "Objects": [
                        {"Key": file_key}
                    ]
                }
            )
            logging.info(f"Successfully deleted file {file_key} from bucket {bucket_name} using delete_objects")
        except Exception as e:
            logging.error(f"Failed to delete file {file_key} from S3: {e}")
            raise

s3_client_manager = AsyncS3Client()