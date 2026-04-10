import sqlalchemy

from backend.storage import minio_handler
from backend.storage.database import ChatKind, ChatRole, Message, MessageAttachment, MessageReceipt


def test_message_attachment_comment_search_and_read_routes(client, ctx):
    # Проверяет вложения, поиск, комментарии в канале и отметки о прочтении в групповом чате.
    users = ctx.seed_users()
    group_chat = ctx.run(
        ctx.create_chat(
            chat_kind=ChatKind.GROUP,
            owner_user_id=users["ivan"].id,
            name="Рабочие заметки",
            members=[(users["ivan"], ChatRole.OWNER), (users["maria"], ChatRole.USER)],
        )
    )
    channel_chat = ctx.run(
        ctx.create_chat(
            chat_kind=ChatKind.CHANNEL,
            owner_user_id=users["ivan"].id,
            name="Объявления команды",
            members=[(users["ivan"], ChatRole.OWNER), (users["maria"], ChatRole.USER)],
        )
    )

    ctx.authorize(client, users["ivan"])
    post_root_response = client.post(
        f"/chats/id/{group_chat.id}/messages",
        data={"message_text": "Смету пришлю сегодня вечером."},
        files=[("file_attachments_list", ("smeta.txt", "Версия 1".encode("utf-8"), "text/plain"))],
    )
    assert post_root_response.status_code == 201
    root_message_id = post_root_response.json()["id"]

    attachment = ctx.run(ctx.scalar(sqlalchemy.select(MessageAttachment).where(MessageAttachment.message_id == root_message_id)))
    assert attachment is not None
    assert ctx.run(ctx.object_exists_in_minio(minio_handler.MinioBucket.messages_attachments, attachment.attachment_file_path)) is True

    channel_root_response = client.post(
        f"/chats/id/{channel_chat.id}/messages",
        data={"message_text": "Сегодня в восемь будет созвон по плану."},
    )
    assert channel_root_response.status_code == 201
    channel_root_message_id = channel_root_response.json()["id"]

    channel_comment_response = client.post(
        f"/chats/id/{channel_chat.id}/messages",
        data={"message_text": "Если опоздаете, напишите в чат.", "parent_message_id": str(channel_root_message_id)},
    )
    assert channel_comment_response.status_code == 201
    comment_message_id = channel_comment_response.json()["id"]

    client.cookies.clear()
    ctx.authorize(client, users["maria"])

    chat_messages_response = client.get(f"/chats/id/{group_chat.id}/messages")
    assert chat_messages_response.status_code == 200
    assert chat_messages_response.json()[0]["message_text"] == "Смету пришлю сегодня вечером."

    single_message_response = client.get(f"/chats/id/{group_chat.id}/messages/id/{root_message_id}")
    assert single_message_response.status_code == 200
    assert single_message_response.json()["sender_user_id"] == users["ivan"].id

    attachments_response = client.get(f"/chats/id/{group_chat.id}/messages/id/{root_message_id}/attachments")
    assert attachments_response.status_code == 200
    assert attachments_response.json()[0]["id"] == attachment.id

    attachment_file_response = client.get(
        f"/chats/id/{group_chat.id}/messages/id/{root_message_id}/attachments/id/{attachment.id}"
    )
    assert attachment_file_response.status_code == 200
    assert attachment_file_response.content == "Версия 1".encode("utf-8")

    comments_response = client.get(f"/chats/id/{channel_chat.id}/messages/id/{channel_root_message_id}/comments")
    assert comments_response.status_code == 200
    assert comments_response.json()[0]["id"] == comment_message_id

    comment_search_response = client.get(
        f"/chats/id/{channel_chat.id}/messages/id/{channel_root_message_id}/comments/search",
        params={"message_text": "опоздаете", "offset_multiplier": 0},
    )
    assert comment_search_response.status_code == 200
    assert comment_search_response.json()[0]["message_text"] == "Если опоздаете, напишите в чат."

    root_search_response = client.get(
        f"/chats/id/{group_chat.id}/messages/search",
        params={"message_text": "смету", "offset_multiplier": 0},
    )
    assert root_search_response.status_code == 200
    assert root_search_response.json()[0]["id"] == root_message_id

    last_message_response = client.get(f"/chats/id/{group_chat.id}/messages/last")
    assert last_message_response.status_code == 200
    assert last_message_response.json()["message"]["id"] == root_message_id

    read_response = client.post(f"/chats/id/{group_chat.id}/messages/id/{root_message_id}/read")
    assert read_response.status_code == 201
    receipt_id = read_response.json()["id"]
    assert ctx.run(ctx.scalar(sqlalchemy.select(MessageReceipt).where(MessageReceipt.id == receipt_id))) is not None

    duplicate_read_response = client.post(f"/chats/id/{group_chat.id}/messages/id/{root_message_id}/read")
    assert duplicate_read_response.status_code == 400

    client.cookies.clear()
    ctx.authorize(client, users["ivan"])
    update_response = client.put(
        f"/chats/id/{group_chat.id}/messages/id/{root_message_id}",
        json={"message_text": "Смету пришлю сегодня до девяти вечера."},
    )
    assert update_response.status_code == 204

    updated_message = ctx.run(ctx.scalar(sqlalchemy.select(Message).where(Message.id == root_message_id)))
    assert updated_message.message_text == "Смету пришлю сегодня до девяти вечера."

    delete_response = client.delete(f"/chats/id/{group_chat.id}/messages/id/{root_message_id}")
    assert delete_response.status_code == 204
    assert ctx.run(ctx.scalar(sqlalchemy.select(Message).where(Message.id == root_message_id))) is None
    assert ctx.run(ctx.scalar(sqlalchemy.select(Message).where(Message.id == comment_message_id))) is not None


def test_message_routes_reject_invalid_operations(client, ctx):
    # Проверяет ошибки сообщений: пустой текст и попытку отметить своё сообщение как прочитанное.
    users = ctx.seed_users()
    group_chat = ctx.run(
        ctx.create_chat(
            chat_kind=ChatKind.GROUP,
            owner_user_id=users["ivan"].id,
            name="Обсуждение макета",
            members=[(users["ivan"], ChatRole.OWNER), (users["maria"], ChatRole.USER)],
        )
    )
    root_message = ctx.run(ctx.create_message(chat=group_chat, sender=users["ivan"], message_text="Покажу черновик вечером."))

    ctx.authorize(client, users["ivan"])
    empty_message_response = client.post(f"/chats/id/{group_chat.id}/messages", data={"message_text": ""})
    assert empty_message_response.status_code in {400, 422}

    own_read_response = client.post(f"/chats/id/{group_chat.id}/messages/id/{root_message.id}/read")
    assert own_read_response.status_code == 400


def test_message_routes_reject_foreign_attachment_and_foreign_edit(client, ctx):
    # Проверяет, что нельзя получить вложение не того сообщения и нельзя редактировать сообщение другого участника.
    users = ctx.seed_users()
    group_chat = ctx.run(
        ctx.create_chat(
            chat_kind=ChatKind.GROUP,
            owner_user_id=users["ivan"].id,
            name="План созвона",
            members=[(users["ivan"], ChatRole.OWNER), (users["maria"], ChatRole.USER)],
        )
    )

    ctx.authorize(client, users["ivan"])
    first_message_response = client.post(
        f"/chats/id/{group_chat.id}/messages",
        data={"message_text": "Черновик плана уже у меня."},
        files=[("file_attachments_list", ("plan.txt", "Черновик".encode("utf-8"), "text/plain"))],
    )
    assert first_message_response.status_code == 201
    first_message_id = first_message_response.json()["id"]

    second_message_response = client.post(
        f"/chats/id/{group_chat.id}/messages",
        data={"message_text": "Отправлю итоговую версию позже."},
    )
    assert second_message_response.status_code == 201
    second_message_id = second_message_response.json()["id"]

    attachment = ctx.run(
        ctx.scalar(sqlalchemy.select(MessageAttachment).where(MessageAttachment.message_id == first_message_id))
    )
    assert attachment is not None

    client.cookies.clear()
    ctx.authorize(client, users["maria"])

    foreign_attachment_response = client.get(
        f"/chats/id/{group_chat.id}/messages/id/{second_message_id}/attachments/id/{attachment.id}"
    )
    assert foreign_attachment_response.status_code == 400

    foreign_edit_response = client.put(
        f"/chats/id/{group_chat.id}/messages/id/{first_message_id}",
        json={"message_text": "Попробую исправить чужое сообщение."},
    )
    assert foreign_edit_response.status_code == 403
