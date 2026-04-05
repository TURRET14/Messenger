import dataclasses
import io
import asyncio

import fastapi
import fastapi.concurrency
import minio
import minio.datatypes
import enum
import pathlib
import uuid
import urllib3

import backend.routers.parameters as parameters
from backend.routers.errors import ErrorRegistry
import backend.environment as environment

class MinioBucket(str, enum.Enum):
    users_avatars = "users:avatars"
    chats_avatars = "chats:avatars"
    messages_attachments = "messages:attachments"


@dataclasses.dataclass
class BucketWithFiles:
    bucket_name: MinioBucket
    file_names: list[str]

class MinioClient:
    def __init__(self, endpoint: str, access_key: str, secret_key: str):
        self.client = minio.Minio(endpoint = endpoint, access_key = access_key, secret_key = secret_key)

        self.client.make_bucket(MinioBucket.users_avatars.value)
        self.client.make_bucket(MinioBucket.chats_avatars.value)
        self.client.make_bucket(MinioBucket.messages_attachments.value)


    async def get_file(self, bucket_name: MinioBucket, object_name: str) -> urllib3.BaseHTTPResponse:
        try:
            return await fastapi.concurrency.run_in_threadpool(self.client.get_object, bucket_name.value, object_name)
        except minio.S3Error:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_does_not_exist_error.error_status_code, detail = ErrorRegistry.file_does_not_exist_error)


    async def get_file_stat(self, bucket_name: MinioBucket, object_name: str) -> minio.datatypes.Object:
        try:
            return await fastapi.concurrency.run_in_threadpool(self.client.stat_object, bucket_name.value, object_name)
        except minio.S3Error:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_does_not_exist_error.error_status_code, detail = ErrorRegistry.file_does_not_exist_error)


    async def put_file(self, bucket_name: MinioBucket, file: fastapi.UploadFile) -> str:
        try:
            return await fastapi.concurrency.run_in_threadpool(self.put_file_task, bucket_name, file)
        except minio.S3Error:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.error_uploading_file_error.error_status_code, detail = ErrorRegistry.error_uploading_file_error)


    def put_file_task(self, bucket_name: MinioBucket, file: fastapi.UploadFile) -> str:

        if not file.filename or not file.content_type or not file.size:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.error_uploading_file_error.error_status_code, detail = ErrorRegistry.error_uploading_file_error)

        file_bytes: bytes = bytes()
        image_extension: str = pathlib.Path(file.filename).suffix.upper()
        minio_file_name = f"{uuid.uuid4().hex}{image_extension}"

        match bucket_name:
            case MinioBucket.users_avatars | MinioBucket.chats_avatars:
                if file.content_type not in parameters.ALLOWED_IMAGE_CONTENT_TYPES:
                    raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_type_not_allowed_error.error_status_code,
                    detail = ErrorRegistry.file_type_not_allowed_error)

                if image_extension not in parameters.ALLOWED_IMAGE_EXTENSIONS:
                    raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_type_not_allowed_error.error_status_code,
                    detail = ErrorRegistry.file_type_not_allowed_error)

                if file.size > parameters.MAX_AVATAR_SIZE_BYTES:
                    raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_size_too_large.error_status_code,
                    detail = ErrorRegistry.file_size_too_large)

                file_bytes = file.file.read()

                if len(file_bytes) > parameters.MAX_AVATAR_SIZE_BYTES:
                    raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_size_too_large.error_status_code,
                    detail = ErrorRegistry.file_size_too_large)

            case MinioBucket.messages_attachments:
                if file.size > parameters.MAX_ATTACHMENT_SIZE_BYTES:
                    raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_size_too_large.error_status_code,
                    detail = ErrorRegistry.file_size_too_large)

                file_bytes = file.file.read()

                if len(file_bytes) > parameters.MAX_ATTACHMENT_SIZE_BYTES:
                    raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.file_size_too_large.error_status_code,
                    detail = ErrorRegistry.file_size_too_large)


        self.client.put_object(str(bucket_name.value), minio_file_name, io.BytesIO(file_bytes), len(file_bytes), file.content_type)

        return minio_file_name


    async def delete_file(self, bucket_name: MinioBucket, object_name: str):
        try:
            await fastapi.concurrency.run_in_threadpool(self.delete_file_task, bucket_name, object_name)
        except minio.S3Error:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.error_deleting_file_error.error_status_code, detail = ErrorRegistry.error_deleting_file_error)


    def delete_file_task(self, bucket_name: MinioBucket, object_name: str):
        self.client.remove_object(bucket_name.value, object_name)


    async def delete_all_files(self, buckets_list: list[BucketWithFiles]):
        try:
            tasks_list: list = list()

            for bucket in buckets_list:
                for file_name in bucket.file_names:
                    tasks_list.append(self.delete_file(bucket.bucket_name, file_name))

            await asyncio.gather(*tasks_list)
        except minio.S3Error:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.error_deleting_file_error.error_status_code, detail = ErrorRegistry.error_deleting_file_error)

    @staticmethod
    async def close_file_stream(file: urllib3.BaseHTTPResponse):
        file.close()
        file.release_conn()


minio_client: MinioClient = MinioClient(
    endpoint = environment.MINIO_ENDPOINT,
    access_key = environment.MINIO_ROOT_USER,
    secret_key = environment.MINIO_ROOT_PASSWORD
)


async def get_minio_client() -> MinioClient:
    return minio_client