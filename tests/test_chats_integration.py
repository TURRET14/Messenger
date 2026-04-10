import sqlalchemy

from backend.storage.database import Chat, ChatKind, ChatMembership, ChatRole


def test_group_chat_channel_and_membership_routes(client, ctx):
    # Проверяет создание и управление групповыми чатами и каналами, включая роли, название, аватар и состав участников.
    users = ctx.seed_users()
    ctx.run(ctx.create_friendship(users["ivan"], users["maria"]))
    ctx.run(ctx.create_friendship(users["ivan"], users["oleg"]))

    ctx.authorize(client, users["ivan"])
    create_group = client.post("/chats/group", json={"name": "Поездка на Байкал"})
    assert create_group.status_code == 201
    group_chat_id = create_group.json()["id"]

    chats_response = client.get("/chats")
    assert chats_response.status_code == 200
    assert chats_response.json()[0]["name"] == "Поездка на Байкал"

    chat_response = client.get(f"/chats/id/{group_chat_id}")
    assert chat_response.status_code == 200
    assert chat_response.json()["chat_kind"] == "GROUP"

    add_maria_response = client.post(f"/chats/id/{group_chat_id}/users", json={"id": users["maria"].id})
    assert add_maria_response.status_code == 201
    maria_membership_id = add_maria_response.json()["id"]

    add_oleg_response = client.post(f"/chats/id/{group_chat_id}/users", json={"id": users["oleg"].id})
    assert add_oleg_response.status_code == 201
    oleg_membership_id = add_oleg_response.json()["id"]

    add_admin_response = client.post(f"/chats/id/{group_chat_id}/admins", json={"id": users["maria"].id})
    assert add_admin_response.status_code == 204

    members_response = client.get(f"/chats/id/{group_chat_id}/memberships")
    assert members_response.status_code == 200
    assert len(members_response.json()) == 3

    membership_response = client.get(f"/chats/id/{group_chat_id}/memberships/id/{maria_membership_id}")
    assert membership_response.status_code == 200
    assert membership_response.json()["chat_role"] == "ADMIN"

    rename_response = client.patch(f"/chats/id/{group_chat_id}/name", json={"name": "Планы на выходные"})
    assert rename_response.status_code == 204

    avatar_response = client.put(
        f"/chats/id/{group_chat_id}/avatar",
        files={"file": ("baikal.png", b"\x89PNG\r\n\x1a\nchat-avatar", "image/png")},
    )
    assert avatar_response.status_code == 204
    assert client.get(f"/chats/id/{group_chat_id}/avatar").status_code == 200

    delete_admin_response = client.delete(f"/chats/id/{group_chat_id}/admins/id/{users['maria'].id}")
    assert delete_admin_response.status_code == 204

    delete_oleg_response = client.delete(f"/chats/id/{group_chat_id}/users/id/{users['oleg'].id}")
    assert delete_oleg_response.status_code == 204

    update_owner_response = client.patch(f"/chats/id/{group_chat_id}/owner", json={"id": users["maria"].id})
    assert update_owner_response.status_code == 204

    client.cookies.clear()
    ctx.authorize(client, users["maria"])
    delete_chat_response = client.delete(f"/chats/id/{group_chat_id}")
    assert delete_chat_response.status_code == 204
    assert ctx.run(ctx.scalar(sqlalchemy.select(Chat).where(Chat.id == group_chat_id))) is None

    client.cookies.clear()
    ctx.authorize(client, users["ivan"])
    create_channel_response = client.post("/chats/channels", json={"name": "Новости проекта"})
    assert create_channel_response.status_code == 201
    assert client.get(f"/chats/id/{create_channel_response.json()['id']}").json()["chat_kind"] == "CHANNEL"
    assert ctx.run(ctx.scalar(sqlalchemy.select(ChatMembership).where(ChatMembership.id == oleg_membership_id))) is None


def test_private_chat_profile_and_leave_routes(client, ctx):
    # Проверяет создание приватного чата, маршрут профиля пользователя и удаление приватного чата при выходе участника.
    users = ctx.seed_users()
    ctx.authorize(client, users["ivan"])

    create_private = client.post("/chats/private", json={"id": users["maria"].id})
    assert create_private.status_code == 201
    private_chat_id = create_private.json()["id"]

    profile_response = client.get(f"/users/id/{users['maria'].id}/profile")
    assert profile_response.status_code == 200
    assert profile_response.json()["chat_kind"] == "PROFILE"

    client.cookies.clear()
    ctx.authorize(client, users["maria"])
    leave_response = client.delete(f"/chats/id/{private_chat_id}/users/me")
    assert leave_response.status_code == 204
    assert ctx.run(ctx.scalar(sqlalchemy.select(Chat).where(Chat.id == private_chat_id))) is None


def test_chat_routes_reject_invalid_operations(client, ctx):
    # Проверяет ошибки чатов: владелец не может выйти из своего чата, а неучастник не должен видеть чужой групповой чат.
    users = ctx.seed_users()
    ctx.run(ctx.create_friendship(users["ivan"], users["maria"]))

    group_chat = ctx.run(
        ctx.create_chat(
            chat_kind=ChatKind.GROUP,
            owner_user_id=users["ivan"].id,
            name="Книжный клуб",
            members=[(users["ivan"], ChatRole.OWNER), (users["maria"], ChatRole.USER)],
        )
    )

    ctx.authorize(client, users["ivan"])
    leave_owner_response = client.delete(f"/chats/id/{group_chat.id}/users/me")
    assert leave_owner_response.status_code == 400

    client.cookies.clear()
    ctx.authorize(client, users["anna"])
    hidden_chat_response = client.get(f"/chats/id/{group_chat.id}")
    assert hidden_chat_response.status_code == 404


def test_chat_routes_reject_foreign_membership_and_missing_avatar(client, ctx):
    # Проверяет, что нельзя запросить чужое membership через другой чат и нельзя получить аватар чата, если он ещё не установлен.
    users = ctx.seed_users()
    ctx.run(ctx.create_friendship(users["ivan"], users["maria"]))

    first_group = ctx.run(
        ctx.create_chat(
            chat_kind=ChatKind.GROUP,
            owner_user_id=users["ivan"].id,
            name="Подготовка к походу",
            members=[(users["ivan"], ChatRole.OWNER), (users["maria"], ChatRole.USER)],
        )
    )
    second_group = ctx.run(
        ctx.create_chat(
            chat_kind=ChatKind.GROUP,
            owner_user_id=users["ivan"].id,
            name="Покупки на дачу",
            members=[(users["ivan"], ChatRole.OWNER), (users["maria"], ChatRole.USER)],
        )
    )
    foreign_membership = ctx.run(
        ctx.scalar(
            sqlalchemy.select(ChatMembership).where(
                sqlalchemy.and_(ChatMembership.chat_id == second_group.id, ChatMembership.chat_user_id == users["maria"].id)
            )
        )
    )

    ctx.authorize(client, users["ivan"])
    missing_avatar_response = client.get(f"/chats/id/{first_group.id}/avatar")
    assert missing_avatar_response.status_code == 404

    foreign_membership_response = client.get(f"/chats/id/{first_group.id}/memberships/id/{foreign_membership.id}")
    assert foreign_membership_response.status_code == 403
