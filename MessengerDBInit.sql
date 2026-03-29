CREATE TYPE genders_enum AS ENUM ('male', 'female');
CREATE TYPE chat_types_enum AS ENUM ('private', 'group', 'community', 'discussion', 'wall');
CREATE TYPE chat_roles_enum AS ENUM ('owner', 'admin', 'user');

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    surname VARCHAR(100),
    second_name VARCHAR(100),
    date_of_birth DATE,
    gender genders_enum,
    email_address VARCHAR(260) NOT NULL UNIQUE,
    phone_number VARCHAR(50) UNIQUE,
    about VARCHAR(5000),
    avatar_photo_path VARCHAR(250),
    login VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    date_and_time_registered TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_users_username ON users (UPPER(username));
CREATE INDEX idx_users_name ON users (UPPER(name));
CREATE INDEX idx_users_surname ON users (UPPER(surname));
CREATE INDEX idx_users_second_name ON users (UPPER(second_name));
CREATE INDEX idx_users_name_surname_second_name ON users (UPPER(name), UPPER(surname), UPPER(second_name));
CREATE INDEX idx_users_login ON users (login);
CREATE INDEX idx_users_email_address ON users (email_address);
CREATE INDEX idx_users_phone_number ON users (phone_number);

CREATE TABLE friends (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    friend_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    date_and_time_added TIMESTAMPTZ NOT NULL,
    UNIQUE(user_id, friend_user_id),
    CHECK(user_id < friend_user_id)
);

CREATE INDEX idx_friends_user_id ON friends (user_id);
CREATE INDEX idx_friends_friend_user_id ON friends (friend_user_id);
CREATE INDEX idx_friends_user_id_friend_user_id ON friends(user_id, friend_user_id);

CREATE TABLE friend_requests (
    id BIGSERIAL PRIMARY KEY,
    sender_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    receiver_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    date_and_time_sent TIMESTAMPTZ NOT NULL,
    CHECK(sender_user_id != receiver_user_id)
);

CREATE UNIQUE INDEX uq_friend_requests_sender_user_id_receiver_user_id ON friend_requests (least(sender_user_id, receiver_user_id), greatest(sender_user_id, receiver_user_id));

CREATE INDEX idx_friend_requests_sender_user_id ON friend_requests (sender_user_id);
CREATE INDEX idx_friend_requests_receiver_user_id ON friend_requests (receiver_user_id);
CREATE INDEX idx_friend_requests_sender_user_id_receiver_user_id ON friend_requests(sender_user_id, receiver_user_id);

CREATE TABLE chats (
    id BIGSERIAL PRIMARY KEY,
    chat_kind chat_types_enum NOT NULL,
    name VARCHAR(100),
    owner_user_id BIGINT REFERENCES users ON DELETE CASCADE,
    date_and_time_created TIMESTAMPTZ NOT NULL,
    avatar_photo_path VARCHAR(250)
);

CREATE INDEX idx_chats_name ON chats (UPPER(name));
CREATE INDEX idx_chats_chat_kind ON chats(chat_kind);

CREATE TABLE chat_members (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT REFERENCES chats ON DELETE CASCADE NOT NULL,
    chat_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    date_and_time_added TIMESTAMPTZ NOT NULL,
    chat_role chat_roles_enum NOT NULL,
    UNIQUE(chat_id, chat_user_id)
);

CREATE INDEX idx_chat_members_chat_id ON chat_members (chat_id);
CREATE INDEX idx_chat_members_chat_user_id ON chat_members (chat_user_id);
CREATE INDEX idx_chat_members_chat_id_chat_user_id ON chat_members(chat_id, chat_user_id);
CREATE INDEX idx_chat_members_chat_id_date_and_time_added_chat_role ON chat_members(chat_id, date_and_time_added, chat_role);

CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT REFERENCES chats ON DELETE CASCADE NOT NULL,
    sender_user_id BIGINT REFERENCES users ON DELETE SET NULL,
    date_and_time_sent TIMESTAMPTZ NOT NULL,
    date_and_time_edited TIMESTAMPTZ,
    reply_message_id BIGINT REFERENCES messages ON DELETE SET NULL,
    message_text TEXT,
    message_text_tsvector TSVECTOR GENERATED ALWAYS AS (TO_TSVECTOR('russian', message_text)) STORED,
    parent_message_id BIGINT REFERENCES messages ON DELETE CASCADE,
    is_notification BOOLEAN
);

CREATE INDEX idx_messages_chat_id ON messages (chat_id);
CREATE INDEX idx_messages_sender_user_id ON messages (sender_user_id);
CREATE INDEX idx_messages_chat_id_sender_user_id ON messages (chat_id, sender_user_id);
CREATE INDEX idx_messages_chat_id_date_and_time_sent ON messages (chat_id, date_and_time_sent);
CREATE INDEX idx_messages_message_text_tsvector ON messages USING GIN(message_text_tsvector);

CREATE TABLE message_attachments (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT REFERENCES messages ON DELETE CASCADE NOT NULL,
    attachment_file_path VARCHAR(250) NOT NULL UNIQUE
);

CREATE INDEX idx_message_attachments_message_id ON message_attachments (message_id);

CREATE TABLE message_receipts (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT REFERENCES messages ON DELETE CASCADE NOT NULL,
    receiver_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    date_and_time_received TIMESTAMPTZ NOT NULL,
    UNIQUE(message_id, receiver_user_id)
);

CREATE INDEX idx_message_receipts_message_id ON message_receipts (message_id);
CREATE INDEX idx_message_receipts_receiver_user_id ON message_receipts (receiver_user_id);
CREATE INDEX idx_message_receipts_message_id_receiver_user_id ON message_receipts (message_id, receiver_user_id);


CREATE TABLE user_blocks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    blocked_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    date_and_time_blocked TIMESTAMPTZ NOT NULL,
    UNIQUE(user_id, blocked_user_id),
    CHECK (user_id != blocked_user_id)
);

CREATE INDEX idx_user_blocks_user_id ON user_blocks (user_id);
CREATE INDEX idx_user_blocks_blocked_user_id ON user_blocks (blocked_user_id);
CREATE INDEX idx_user_blocks_user_id_blocked_user_id ON user_blocks (user_id, blocked_user_id);