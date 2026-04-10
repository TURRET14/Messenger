import sqlalchemy

from backend.storage.database import Chat, ChatKind, ChatRole, Friendship, FriendRequest, User


def test_registration_and_session_routes(client, ctx, email_outbox):
    # Проверяет полный путь регистрации, создания пользователя, входа и управления пользовательскими сессиями через Redis.
    register_response = client.post(
        "/users/register",
        json={
            "username": "светлана_орлова",
            "name": "Светлана",
            "surname": "Орлова",
            "second_name": "Павловна",
            "email_address": "svetlana.orlova@example.com",
            "login": "svetlana.orlova",
            "password": "секрет123",
        },
    )
    assert register_response.status_code == 204
    assert email_outbox[-1]["receiver_email"] == "svetlana.orlova@example.com"

    create_response = client.post("/users", json={"code": email_outbox[-1]["code"]})
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    created_user = ctx.run(ctx.scalar(sqlalchemy.select(User).where(User.id == user_id)))
    profile_chat = ctx.run(
        ctx.scalar(sqlalchemy.select(Chat).where(sqlalchemy.and_(Chat.owner_user_id == user_id, Chat.chat_kind == ChatKind.PROFILE)))
    )
    assert created_user is not None
    assert profile_chat is not None

    login_response = client.post(
        "/login",
        json={"login": "svetlana.orlova", "password": "секрет123"},
        headers={"user-agent": "pytest-browser"},
    )
    assert login_response.status_code == 200
    assert "session_id" in client.cookies

    me_response = client.get("/users/me")
    assert me_response.status_code == 200
    assert me_response.json()["name"] == "Светлана"

    sessions_response = client.get("/users/me/sessions")
    assert sessions_response.status_code == 200
    assert len(sessions_response.json()) == 1

    session_id = sessions_response.json()[0]["session_id"]
    delete_session_response = client.request("DELETE", "/users/me/sessions", json={"session_id": session_id})
    assert delete_session_response.status_code == 204
    assert client.get("/users/me").status_code == 404

    second_login = client.post(
        "/login",
        json={"login": "svetlana.orlova", "password": "секрет123"},
        headers={"user-agent": "pytest-browser-2"},
    )
    assert second_login.status_code == 200
    assert client.delete("/users/me/sessions/all").status_code == 204
    assert client.get("/users/me").status_code == 404


def test_user_profile_search_avatar_email_and_delete_routes(client, ctx, email_outbox):
    # Проверяет маршруты профиля пользователя: чтение, обновление, поиск, смену почты, аватара и окончательное удаление аккаунта.
    users = ctx.seed_users()
    ctx.authorize(client, users["ivan"])

    assert client.get(f"/users/id/{users['maria'].id}").status_code == 200
    assert client.get("/users/me/login").json()["login"] == "ivan.petrov"

    update_response = client.patch(
        "/users/me",
        json={
            "username": "иван_петров_мск",
            "name": "Иван",
            "surname": "Петров",
            "second_name": "Сергеевич",
            "date_of_birth": "1994-04-11",
            "gender": None,
            "email_address": "ivan.petrov@example.com",
            "phone_number": "+79991112233",
            "about": "Готовлю поездку на Байкал и собираю заметки.",
        },
    )
    assert update_response.status_code == 204

    assert client.put("/users/me/login", json={"login": "ivan.petrov.msk"}).status_code == 204
    assert client.put("/users/me/password", json={"old_password": "секрет123", "new_password": "новыйсекрет123"}).status_code == 204

    relogin_response = client.post(
        "/login",
        json={"login": "ivan.petrov.msk", "password": "новыйсекрет123"},
        headers={"user-agent": "pytest-browser-updated"},
    )
    assert relogin_response.status_code == 200

    users_response = client.get("/users")
    usernames = {item["username"] for item in users_response.json()}
    assert "мария_соколова" in usernames

    username_search = client.get("/users/search/by-username", params={"username": "мар", "offset_multiplier": 0})
    assert username_search.status_code == 200
    assert username_search.json()[0]["name"] == "Мария"

    names_search = client.get("/users/search/by-names", params={"name": "Мар", "offset_multiplier": 0})
    assert names_search.status_code == 200
    assert names_search.json()[0]["surname"] == "Соколова"

    empty_search = client.get("/users/search/by-names", params={"offset_multiplier": 0})
    assert empty_search.status_code == 400

    avatar_bytes = b"\x89PNG\r\n\x1a\npng-data"
    avatar_response = client.put("/users/me/avatar", files={"file": ("ivan.png", avatar_bytes, "image/png")})
    assert avatar_response.status_code == 204
    assert client.get("/users/me/avatar").status_code == 200
    assert client.get(f"/users/id/{users['ivan'].id}/avatar").status_code == 200

    change_email_response = client.patch("/users/me/email", json={"email_address": "ivan.new@example.com"})
    assert change_email_response.status_code == 204
    assert email_outbox[-1]["receiver_email"] == "ivan.new@example.com"
    assert client.patch("/users/me/email/confirm", json={"code": email_outbox[-1]["code"]}).status_code == 204

    updated_user = ctx.run(ctx.scalar(sqlalchemy.select(User).where(User.id == users["ivan"].id)))
    assert updated_user.email_address == "ivan.new@example.com"

    delete_response = client.delete("/users/me")
    assert delete_response.status_code == 204
    assert ctx.run(ctx.scalar(sqlalchemy.select(User).where(User.id == users["ivan"].id))) is None


def test_friend_request_friendship_block_and_unblock_routes(client, ctx):
    # Проверяет сценарии заявок в друзья, дружбы, блокировки и разблокировки с сохранением корректного состояния БД.
    users = ctx.seed_users()
    ctx.authorize(client, users["ivan"])

    send_response = client.post("/users/me/friends/requests/send", json={"id": users["maria"].id})
    assert send_response.status_code == 201
    friend_request_id = send_response.json()["id"]

    sent_list = client.get("/users/me/friends/requests/sent")
    assert sent_list.status_code == 200
    assert sent_list.json()[0]["receiver_user_id"] == users["maria"].id

    client.cookies.clear()
    ctx.authorize(client, users["maria"])
    received_list = client.get("/users/me/friends/requests/received")
    assert received_list.status_code == 200
    assert received_list.json()[0]["sender_user_id"] == users["ivan"].id

    accept_response = client.put(f"/users/me/friends/requests/received/id/{friend_request_id}")
    assert accept_response.status_code == 201
    friendship_id = accept_response.json()["id"]

    friends_response = client.get("/users/me/friends")
    assert friends_response.status_code == 200
    assert friends_response.json()[0]["name"] == "Иван"

    friend_username_search = client.get("/users/me/friends/search/by-username", params={"username": "ива", "offset_multiplier": 0})
    assert friend_username_search.status_code == 200

    friend_names_search = client.get("/users/me/friends/search/by-names", params={"name": "Ива", "offset_multiplier": 0})
    assert friend_names_search.status_code == 200

    client.cookies.clear()
    ctx.authorize(client, users["ivan"])
    delete_friendship_response = client.delete(f"/users/me/friends/{friendship_id}")
    assert delete_friendship_response.status_code == 204
    assert ctx.run(ctx.scalar(sqlalchemy.select(Friendship).where(Friendship.id == friendship_id))) is None

    second_request = client.post("/users/me/friends/requests/send", json={"id": users["oleg"].id})
    assert second_request.status_code == 201
    second_request_id = second_request.json()["id"]
    assert client.delete(f"/users/me/friends/requests/sent/id/{second_request_id}").status_code == 204
    assert ctx.run(ctx.scalar(sqlalchemy.select(FriendRequest).where(FriendRequest.id == second_request_id))) is None

    pending_request = ctx.run(ctx.create_friend_request(users["anna"], users["maria"]))
    client.cookies.clear()
    ctx.authorize(client, users["maria"])
    decline_response = client.delete(f"/users/me/friends/requests/received/id/{pending_request.id}")
    assert decline_response.status_code == 204

    ctx.run(ctx.create_friendship(users["ivan"], users["maria"]))
    private_chat = ctx.run(
        ctx.create_chat(
        chat_kind=ChatKind.PRIVATE,
        owner_user_id=None,
        name=None,
        members=[(users["ivan"], ChatRole.USER), (users["maria"], ChatRole.USER)],
        )
    )

    client.cookies.clear()
    ctx.authorize(client, users["ivan"])
    block_response = client.post("/users/me/blocks", json={"id": users["maria"].id})
    assert block_response.status_code == 201
    block_id = block_response.json()["id"]

    assert ctx.run(ctx.get_user_block(users["ivan"].id, users["maria"].id)) is not None
    assert ctx.run(
        ctx.scalar(sqlalchemy.select(Friendship).where(Friendship.user_id == min(users["ivan"].id, users["maria"].id)))
    ) is None
    assert ctx.run(ctx.scalar(sqlalchemy.select(Chat).where(Chat.id == private_chat.id))) is None

    unblock_response = client.delete(f"/users/me/blocks/id/{block_id}")
    assert unblock_response.status_code == 204
    assert ctx.run(ctx.get_user_block(users["ivan"].id, users["maria"].id)) is None


def test_user_routes_reject_unauthorized_and_invalid_actions(client, ctx):
    # Проверяет отказоустойчивость пользовательских маршрутов на неавторизованные запросы и заведомо неверные действия.
    users = ctx.seed_users()

    assert client.get("/users/me").status_code == 401

    ctx.authorize(client, users["ivan"])
    duplicate_private = ctx.run(
        ctx.create_chat(
        chat_kind=ChatKind.PRIVATE,
        owner_user_id=None,
        name=None,
        members=[(users["ivan"], ChatRole.USER), (users["maria"], ChatRole.USER)],
        )
    )
    assert duplicate_private is not None

    duplicate_private_response = client.post("/chats/private", json={"id": users["maria"].id})
    assert duplicate_private_response.status_code == 400

    self_block_response = client.post("/users/me/blocks", json={"id": users["ivan"].id})
    assert self_block_response.status_code == 400


def test_email_confirmation_rejects_invalid_and_foreign_codes(client, ctx, email_outbox):
    # Проверяет, что подтверждение смены почты отвергает несуществующий код и код, выпущенный для другого пользователя.
    users = ctx.seed_users()

    ctx.authorize(client, users["ivan"])
    assert client.patch("/users/me/email", json={"email_address": "ivan.confirm@example.com"}).status_code == 204
    ivan_code = email_outbox[-1]["code"]

    invalid_code_response = client.patch("/users/me/email/confirm", json={"code": "несуществующий-код"})
    assert invalid_code_response.status_code == 400

    client.cookies.clear()
    ctx.authorize(client, users["maria"])
    foreign_code_response = client.patch("/users/me/email/confirm", json={"code": ivan_code})
    assert foreign_code_response.status_code == 403
