from backend.storage.database import ChatKind, ChatRole


def test_message_websocket_routes_accept_authenticated_connections(client, ctx):
    # Проверяет, что все websocket-подписки на события сообщений доступны участнику чата с действующей сессией.
    users = ctx.seed_users()
    chat = ctx.run(
        ctx.create_chat(
            chat_kind=ChatKind.GROUP,
            owner_user_id=users["ivan"].id,
            name="План на субботу",
            members=[(users["ivan"], ChatRole.OWNER), (users["maria"], ChatRole.USER)],
        )
    )
    root_message = ctx.run(ctx.create_message(chat=chat, sender=users["ivan"], message_text="Собираемся у вокзала в девять."))

    ctx.authorize(client, users["maria"])

    with client.websocket_connect(f"/chats/{chat.id}/messages/post?parent_message_id={root_message.id}"):
        pass
    with client.websocket_connect(f"/chats/{chat.id}/messages/put?parent_message_id={root_message.id}"):
        pass
    with client.websocket_connect(f"/chats/{chat.id}/messages/delete?parent_message_id={root_message.id}"):
        pass
    with client.websocket_connect(f"/chats/{chat.id}/messages/read"):
        pass


def test_chat_websocket_routes_accept_authenticated_connections(client, ctx):
    # Проверяет, что websocket-подписки на события чатов и участников доступны авторизованному пользователю.
    users = ctx.seed_users()
    chat = ctx.run(
        ctx.create_chat(
            chat_kind=ChatKind.GROUP,
            owner_user_id=users["ivan"].id,
            name="Книжный клуб",
            members=[(users["ivan"], ChatRole.OWNER), (users["maria"], ChatRole.USER)],
        )
    )

    ctx.authorize(client, users["maria"])

    with client.websocket_connect("/chats/post"):
        pass
    with client.websocket_connect("/chats/put"):
        pass
    with client.websocket_connect("/chats/delete"):
        pass
    with client.websocket_connect(f"/chats/{chat.id}/memberships/post"):
        pass
    with client.websocket_connect(f"/chats/{chat.id}/memberships/put"):
        pass
    with client.websocket_connect(f"/chats/{chat.id}/memberships/delete"):
        pass
    with client.websocket_connect("/chats/messages/last"):
        pass
