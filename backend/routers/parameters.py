REDIS_USER_SESSION_EXPIRATION_TIME_SECONDS: int = 86400
REDIS_REGISTER_SESSION_EXPIRATION_TIME_SECONDS: int = 900

NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION: int = 50

ALLOWED_IMAGE_CONTENT_TYPES: list[str] = ["image/png", "image/jpg", "image/jpeg", "image/webp"]
ALLOWED_IMAGE_EXTENSIONS: list[str] = [".png", ".jpg", ".jpeg", ".webp"]
MAX_AVATAR_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 МиБ
MAX_ATTACHMENT_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 МиБ

# Размер части для потоковой (multipart) загрузки в MinIO. Файл не читается
# в память целиком — отдаётся клиенту MinIO кусками такого размера.
MINIO_UPLOAD_PART_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 МиБ
