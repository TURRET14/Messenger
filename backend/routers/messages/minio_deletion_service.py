import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import Sequence

from backend.storage import *

async def get_all_message_attachments_to_delete(
    selected_message: Message,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> list[BucketWithFiles]:

    attachments_to_delete: list[BucketWithFiles] = list()

    files_list: Sequence[str] = ((await db.execute(
    sqlalchemy.select(MessageAttachment.attachment_file_path)
    .select_from(MessageAttachment)
    .where(sqlalchemy.or_(MessageAttachment.message_id == selected_message.id,
    MessageAttachment.message_id.in_(sqlalchemy.select(Message.id).select_from(Message).where(Message.parent_message_id == selected_message.id))))))
    .scalars().all())

    attachments_to_delete.append(BucketWithFiles(MinioBucket.messages_attachments, list(files_list)))

    return attachments_to_delete