import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import Sequence

from backend.storage import *

async def get_all_user_attachments_to_delete(
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> list[BucketWithFiles]:

    attachments_to_delete: list[BucketWithFiles] = list()

    if selected_user.avatar_photo_path:
        attachments_to_delete.append(BucketWithFiles(MinioBucket.users_avatars, [selected_user.avatar_photo_path]))

    chat_avatars_files_list: Sequence[str] = ((await db.execute(
    sqlalchemy.select(Chat.avatar_photo_path)
    .select_from(Chat)
    .where(sqlalchemy.and_(Chat.owner_user_id == selected_user.id, Chat.avatar_photo_path is not None))))
    .scalars().all())

    attachments_to_delete.append(BucketWithFiles(MinioBucket.chats_avatars, list(chat_avatars_files_list)))

    message_attachment_files_list: Sequence[str] = ((await db.execute(
    sqlalchemy.select(MessageAttachment.attachment_file_path)
    .select_from(Message)
    .where(Message.chat_id.in_(
    sqlalchemy.select(Chat.id)
    .select_from(ChatMembership)
    .where(ChatMembership.chat_user_id == selected_user.id)
    .join(Chat, Chat.id == ChatMembership.chat_id)
    .where(sqlalchemy.or_(Chat.owner_user_id == selected_user.id, Chat.chat_kind == ChatKind.PRIVATE))))
    .join(MessageAttachment, MessageAttachment.message_id == Message.id)))
    .scalars().all())

    attachments_to_delete.append(BucketWithFiles(MinioBucket.messages_attachments, list(message_attachment_files_list)))

    return attachments_to_delete