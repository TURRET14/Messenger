import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import Sequence

from backend.storage import *

async def get_all_chat_attachments_to_delete(
    selected_chat: Chat,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> list[BucketWithFiles]:

    attachments_to_delete: list[BucketWithFiles] = list()

    if selected_chat.avatar_photo_path:
        attachments_to_delete.append(BucketWithFiles(bucket_name = MinioBucket.chats_avatars, file_names = [selected_chat.avatar_photo_path]))

    message_attachment_files_list: Sequence[str] = ((await db.execute(
    sqlalchemy.select(MessageAttachment.attachment_file_path)
    .select_from(Message)
    .where(Message.chat_id == selected_chat.id)
    .join(MessageAttachment, MessageAttachment.message_id == Message.id)))
    .scalars().all())

    attachments_to_delete.append(BucketWithFiles(bucket_name = MinioBucket.messages_attachments, file_names = list(message_attachment_files_list)))

    return attachments_to_delete