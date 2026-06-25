import logging
from supabase import Client
from helpers.config import get_settings
from helpers.supabase_client import get_supabase_client
import re

logger = logging.getLogger('uvicorn.error')

class SupabaseStorageManager:
    def __init__(self):
        self.settings = get_settings()
        self.client: Client = get_supabase_client()
        self.bucket_prefix = "fields"
        self.max_bucket_size = 50 * 1024 * 1024 # 50MB

    def _get_bucket_index(self, bucket_name: str) -> int:
        match = re.search(rf"{self.bucket_prefix}(\d+)", bucket_name)
        return int(match.group(1)) if match else 0

    async def get_or_create_active_bucket(self) -> str:
        """
        Finds the latest bucket (fields1, fields2, ...) and checks its total size.
        If it exceeds 50MB, creates the next one.
        """
        try:
            buckets = self.client.storage.list_buckets()
            relevant_buckets = [b.name for b in buckets if b.name.startswith(self.bucket_prefix)]
            
            if not relevant_buckets:
                # Create the first bucket
                active_bucket = f"{self.bucket_prefix}1"
                self.client.storage.create_bucket(active_bucket, options={"public": False})
                return active_bucket

            # Sort by index to get the latest
            relevant_buckets.sort(key=self._get_bucket_index, reverse=True)
            latest_bucket = relevant_buckets[0]

            # Check bucket size
            # Note: Supabase doesn't provide a direct "bucket size" API easily.
            # We'll list files and sum their sizes.
            files = self.client.storage.from_(latest_bucket).list()
            total_size = sum(f.get('metadata', {}).get('size', 0) for f in files)

            if total_size >= self.max_bucket_size:
                next_index = self._get_bucket_index(latest_bucket) + 1
                active_bucket = f"{self.bucket_prefix}{next_index}"
                self.client.storage.create_bucket(active_bucket, options={"public": False})
                logger.info(f"Created new bucket: {active_bucket} as {latest_bucket} reached limit.")
                return active_bucket
            
            return latest_bucket
        except Exception as e:
            logger.error(f"Error managing Supabase buckets: {e}")
            raise

    async def upload_file(self, file: object, file_name: str, content_type: str) -> dict:
        """
        Uploads a file to the active bucket and returns destination info.
        Accepts a file-like object (bytes or binary stream).
        """
        active_bucket = await self.get_or_create_active_bucket()
        try:
            # reset file pointer if it's a file object
            if hasattr(file, 'seek'):
                file.seek(0)
                
            res = self.client.storage.from_(active_bucket).upload(
                path=file_name,
                file=file,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            return {
                "bucket": active_bucket,
                "path": file_name,
                "full_path": f"{active_bucket}/{file_name}"
            }
        except Exception as e:
            logger.error(f"Error uploading to Supabase Storage: {e}")
            raise

    async def get_file_content(self, bucket_name: str, file_path: str) -> bytes:
        """
        Downloads file content from a specific bucket.
        """
        try:
            return self.client.storage.from_(bucket_name).download(file_path)
        except Exception as e:
            logger.error(f"Error downloading from Supabase Storage: {e}")
            raise

    async def delete_file(self, bucket_name: str, file_path: str):
        """
        Deletes a file from Supabase Storage.
        """
        try:
            self.client.storage.from_(bucket_name).remove([file_path])
        except Exception as e:
            logger.error(f"Error deleting from Supabase Storage: {e}")
            raise
