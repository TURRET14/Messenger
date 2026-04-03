import fastapi
import fastapi.encoders
import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
import utils

async def validate_chat_user_membership(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> ChatMembership | None:

    chat_membership: ChatMembership | None = await utils.get_chat_user_membership(selected_chat.id, selected_user.id, db)

    if not chat_membership:
        if selected_chat.chat_kind != ChatKind.PROFILE:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.chat_membership_not_found_error.error_status_code, detail = ErrorRegistry.chat_membership_not_found_error)

    return chat_membership


async def validate_message_belonging_to_chat(
    selected_chat: Chat,
    selected_message: Message):

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_does_not_belong_to_chat_error.error_status_code, detail = ErrorRegistry.message_does_not_belong_to_chat_error)


async def validate_chat_has_comments(
    selected_chat: Chat):

    if selected_chat.chat_kind not in [ChatKind.CHANNEL, ChatKind.PROFILE]:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_allowed_chat_type_error.error_status_code, detail = ErrorRegistry.not_allowed_chat_type_error)


async def validate_chat_does_not_have_comments(
    selected_chat: Chat):

    if selected_chat.chat_kind in [ChatKind.CHANNEL, ChatKind.PROFILE]:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_allowed_chat_type_error.error_status_code, detail = ErrorRegistry.not_allowed_chat_type_error)


async def validate_message_is_root(
    selected_message: Message):

    if selected_message.parent_message_id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_does_not_have_comments_error.error_status_code, detail = ErrorRegistry.message_does_not_have_comments_error)


async def validate_is_user_message_sender(
    selected_message: Message,
    selected_user: User):

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_is_not_message_sender_error.error_status_code, detail = ErrorRegistry.user_is_not_message_sender_error)


async def validate_is_user_not_message_sender(
    selected_message: Message,
    selected_user: User):

    if selected_message.sender_user_id == selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_is_not_message_sender_error.error_status_code, detail = ErrorRegistry.user_is_not_message_sender_error)


async def validate_is_message_already_marked_as_received(
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if (await db.execute(sqlalchemy.select(MessageReceipt).where(sqlalchemy.and_(MessageReceipt.message_id == selected_message.id, MessageReceipt.receiver_user_id == selected_user.id)))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_was_already_marked_as_read_error.error_status_code, detail = ErrorRegistry.message_was_already_marked_as_read_error)


async def validate_is_user_allowed_to_post(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    chat_membership: ChatMembership | None = await validate_chat_user_membership(selected_chat, selected_user, db)

    if selected_chat.chat_kind == ChatKind.CHANNEL:
        if chat_membership and chat_membership.chat_role not in [ChatRole.ADMIN, ChatRole.OWNER]:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_enough_permissions_to_post_error.error_status_code, detail=ErrorRegistry.not_enough_permissions_to_post_error)
    if selected_chat.chat_kind == ChatKind.PROFILE:
        if selected_chat.owner_user_id != selected_user.id:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_enough_permissions_to_post_error.error_status_code, detail = ErrorRegistry.not_enough_permissions_to_post_error)


async def validate_post_message(
    selected_chat: Chat,
    selected_user: User,
    message_reply_message_id: int | None,
    message_parent_message_id: int | None,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await validate_is_user_allowed_to_post(selected_chat, selected_user, db)

    if message_parent_message_id:
        if selected_chat.chat_kind in [ChatKind.CHANNEL, ChatKind.PROFILE]:
            parent_message: Message | None = ((await db.execute(
            sqlalchemy.select(Message)
            .where(Message.id == message_parent_message_id)))
            .scalars().first())

            if not parent_message:
                raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.bad_request_error.error_status_code, detail = ErrorRegistry.bad_request_error)

            await validate_message_is_root(parent_message)
        else:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_allowed_chat_type_error.error_status_code, detail = ErrorRegistry.not_allowed_chat_type_error)

    if message_reply_message_id:
        reply_message: Message | None = ((await db.execute(
        sqlalchemy.select(Message)
        .where(Message.id == message_reply_message_id)))
        .scalars().first())

        if not reply_message:
                raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.bad_request_error.error_status_code, detail = ErrorRegistry.bad_request_error)

        await validate_message_belonging_to_chat(selected_chat, reply_message)
        if message_parent_message_id != reply_message.parent_message_id:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.reply_message_belongs_to_different_parent_message_error.error_status_code, detail = ErrorRegistry.reply_message_belongs_to_different_parent_message_error)


async def validate_update_delete_message(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    is_delete: bool,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await validate_is_user_allowed_to_post(selected_chat, selected_user, db)

    await validate_message_belonging_to_chat(selected_chat, selected_message)

    if is_delete:
        if selected_chat.owner_user_id != selected_user.id:
            await validate_is_user_message_sender(selected_message, selected_user)
    else:
        await validate_is_user_message_sender(selected_message, selected_user)