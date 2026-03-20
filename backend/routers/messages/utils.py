import sqlalchemy.orm

from backend.storage import *

async def get_chat_active_user_membership(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> ChatUser:

    membership: ChatUser = db.execute(sqlalchemy.select(ChatUser)
    .where(sqlalchemy.and_(ChatUser.chat_id == selected_chat.id,
    ChatUser.chat_user_id == selected_user.id))).scalars().first()

    return membership


async def is_chat_user_owner(
    selected_chat: Chat,
    selected_user: User) -> bool:

    if selected_chat.owner_user_id != selected_user.id:
        return False
    else:
        return True