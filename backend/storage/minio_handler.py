import io
import os

import fastapi
import fastapi.concurrency
import minio
import minio.datatypes
import enum
import pathlib
import uuid

import backend.routers.parameters as parameters
from backend.routers.errors import ErrorRegistry

class MinioBucket(str, enum.Enum):
    users_avatars = "users:avatars"
    groups_avatars = "groups:avatars"
    messages_attachments = "messages:attachments"


class MinioClient:
    def __init__(self, endpoint: str, access_key: str, secret_key: str):
        self.client = minio.Minio(endpoint, access_key, secret_key)
        self.client.make_bucket(MinioBucket.users_avatars.value)
        self.client.make_bucket(MinioBucket.groups_avatars.value)
        self.client.make_bucket(MinioBucket.messages_attachments.value)


    async def get_file(self, bucket_name: MinioBucket, object_name: str):
        return await fastapi.concurrency.run_in_threadpool(self.client.get_object, bucket_name.value, object_name)


    async def get_file_stat(self, bucket_name: MinioBucket, object_name: str):
        return await fastapi.concurrency.run_in_threadpool(self.client.stat_object, bucket_name.value, object_name)


    async def put_file(self, bucket_name: MinioBucket, file: fastapi.UploadFile) -> str:
        return await fastapi.concurrency.run_in_threadpool(self.put_file_task, bucket_name, file)


    def put_file_task(self, bucket_name: MinioBucket, file: fastapi.UploadFile) -> str:

        minio_file_name: str = str()
        file_bytes: bytes = bytes()

        match bucket_name:
            case MinioBucket.users_avatars:
                if file.content_type not in parameters.allowed_image_content_types:
                    raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_type_not_allowed_error.error_status_code,
                    detail = ErrorRegistry.file_type_not_allowed_error)

                image_extension: str = pathlib.Path(file.filename).suffix.upper()

                if image_extension not in parameters.allowed_image_extensions:
                    raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_type_not_allowed_error.error_status_code,
                    detail = ErrorRegistry.file_type_not_allowed_error)

                minio_file_name = f"{uuid.uuid4().hex}{image_extension}"

                file_bytes = file.file.read()

                if len(file_bytes) > parameters.max_avatar_size_bytes:
                    raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_size_too_large.error_status_code,
                    detail = ErrorRegistry.file_size_too_large)

        self.client.put_object(str(bucket_name.value), minio_file_name, io.BytesIO(file_bytes), len(file_bytes), file.content_type)

        return minio_file_name

    async def delete_file(self, bucket_name: MinioBucket, object_name: str):
        fastapi.concurrency.run_in_threadpool(self.delete_file_task, bucket_name, object_name)


    def delete_file_task(self, bucket_name: MinioBucket, object_name: str):
        self.client.remove_object(bucket_name.value, object_name)


minio_client: MinioClient = MinioClient(os.getenv("MINIO_ENDPOINT"), os.getenv("MINIO_ACCESS_KEY"), os.getenv("MINIO_SECRET_KEY"))


async def get_minio_client() -> minio.Minio:
    return minio_client.client