redis_session_expiration_time_seconds: int = 86400

number_of_table_entries_in_selection: int = 50

allowed_image_content_types: list[str] = ["image/png", "image/jpg", "image/jpeg", "image/webp"]
allowed_image_extensions: list[str] = [".png", ".jpg", ".jpeg", ".webp"]
max_avatar_size_bytes: int = 50 * 1024 * 1024
default_avatar_path: str = "/images/avatar.png"

max_attachment_size_bytes: int = 100 * 1024 * 1024