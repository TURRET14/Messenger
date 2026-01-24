import io
import os

import minio
import minio.datatypes
import fastapi


class MinioClient:
    def __init__(self, endpoint: str, access_key: str, secret_key: str):
        self.client = minio.Minio(endpoint, access_key, secret_key, secure = True)
        self.client.make_bucket("user_avatars")
        self.client.make_bucket("group_avatars")


    async def upload_user_avatar(self, name: str, file: fastapi.UploadFile):
        file_content = await file.read()
        self.client.put_object("user_avatars", name, io.BytesIO(file_content), len(file_content), file.content_type)


    async def upload_group_avatar(self, name: str, file: fastapi.UploadFile):
        file_content = await file.read()
        self.client.put_object("group_avatars", name, io.BytesIO(file_content), len(file_content), file.content_type)


    async def delete_user_avatar(self, name: str):
        self.client.remove_object("user_avatars", name)


    async def delete_group_avatar(self, name: str):
        self.client.remove_object("group_avatars", name)


    async def get_user_avatar_object(self, name: str) -> minio.datatypes.BaseHTTPResponse:
        return self.client.get_object("user_avatars", name)


    async def get_group_avatar_object(self, name: str) -> minio.datatypes.BaseHTTPResponse:
        return self.client.get_object("group_avatars", name)


    async def get_user_avatar_stat(self, name: str) -> minio.datatypes.Object:
        return self.client.stat_object("user_avatars", name)


    async def get_group_avatar_stat(self, name: str) -> minio.datatypes.Object:
        return self.client.stat_object("group_avatars", name)


minio_client: MinioClient = MinioClient(os.getenv("MINIO_ENDPOINT"), os.getenv("MINIO_ACCESS_KEY"), os.getenv("MINIO_SECRET_KEY"))

def get_minio_client() -> MinioClient:
    return minio_client