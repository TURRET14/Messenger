import os
import minio
import minio.datatypes


class MinioClient:
    def __init__(self, endpoint: str, access_key: str, secret_key: str):
        self.client = minio.Minio(endpoint, access_key, secret_key, secure = True)
        self.client.make_bucket("users:avatars")
        self.client.make_bucket("groups:avatars")
        self.client.make_bucket("messages:attachments")


minio_client: MinioClient = MinioClient(os.getenv("MINIO_ENDPOINT"), os.getenv("MINIO_ACCESS_KEY"), os.getenv("MINIO_SECRET_KEY"))

async def get_minio_client() -> minio.Minio:
    return minio_client.client