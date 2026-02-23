CREATE TYPE genders_type AS ENUM ('Male', 'Female');
CREATE TYPE chat_kinds_type AS ENUM ('Private', 'Group');
CREATE TYPE chat_roles_type AS ENUM ('User', 'Admin', 'Owner');

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    surname VARCHAR(100),
    second_name VARCHAR(100),
    date_of_birth DATE,
    gender genders_type,
    email_address VARCHAR(260) NOT NULL UNIQUE,
    phone_number VARCHAR(50) UNIQUE,
    about VARCHAR(5000),
    avatar_photo_path VARCHAR(250),
    login VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
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

CREATE TABLE user_friends (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    friend_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    date_and_time_added TIMESTAMPTZ NOT NULL,
    UNIQUE(user_id, friend_user_id),
    CHECK(user_id != friend_user_id)
);

CREATE INDEX idx_user_friends_user_id ON user_friends (user_id);
CREATE INDEX idx_user_friends_friend_user_id ON user_friends (friend_user_id);

CREATE TABLE user_friend_requests (
    id BIGSERIAL PRIMARY KEY,
    sender_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    receiver_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    date_and_time_sent TIMESTAMPTZ NOT NULL,
    UNIQUE(sender_user_id, receiver_user_id),
    CHECK(sender_user_id != receiver_user_id)
);

CREATE INDEX idx_user_friend_requests_sender_user_id ON user_friend_requests (sender_user_id);
CREATE INDEX idx_user_friend_requests_receiver_user_id ON user_friend_requests (receiver_user_id);

CREATE TABLE chats (
    id BIGSERIAL PRIMARY KEY,
    chat_kind chat_kinds_type NOT NULL,
    name VARCHAR(100),
    owner_user_id BIGINT REFERENCES users ON DELETE CASCADE,
    date_and_time_created TIMESTAMPTZ NOT NULL,
    avatar_photo_path VARCHAR(250),
    is_read_only BOOLEAN NOT NULL
);

CREATE INDEX idx_chats_name ON chats (UPPER(name));

CREATE TABLE chat_users (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT REFERENCES chats ON DELETE CASCADE NOT NULL,
    chat_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    date_and_time_added TIMESTAMPTZ NOT NULL,
    chat_role chat_roles_type NOT NULL,
    is_active BOOLEAN NOT NULL
    UNIQUE(chat_id, chat_user_id)
);

CREATE INDEX idx_chat_users_chat_id ON chat_users (chat_id);
CREATE INDEX idx_chat_users_user_id ON chat_users (chat_user_id);

CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT REFERENCES chats ON DELETE CASCADE NOT NULL,
    sender_user_id BIGINT REFERENCES users ON DELETE SET NULL,
    date_and_time_sent TIMESTAMPTZ NOT NULL,
    date_and_time_edited TIMESTAMPTZ,
    message_text TEXT,
    message_text_tsvector TSVECTOR GENERATED ALWAYS AS (TO_TSVECTOR('russian', message_text)) STORED
);

CREATE INDEX idx_messages_chat_id ON messages (chat_id);
CREATE INDEX idx_messages_chat_id_date_and_time_sent ON messages (chat_id, date_and_time_sent);
CREATE INDEX idx_messages_message_text_tsvector ON messages USING GIN(message_text_tsvector);

CREATE TABLE file_attachments (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT REFERENCES messages ON DELETE CASCADE NOT NULL,
    attachment_file_path VARCHAR(250) NOT NULL,
    UNIQUE(message_id, attachment_file_path)
);

CREATE INDEX idx_file_attachments_message_id ON file_attachments (message_id);

CREATE TABLE received_messages (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT REFERENCES messages ON DELETE CASCADE NOT NULL,
    receiver_user_id BIGINT REFERENCES users ON DELETE CASCADE NOT NULL,
    date_and_time_received TIMESTAMPTZ NOT NULL,
    UNIQUE(message_id, received_user_id)
);

CREATE INDEX idx_received_messages_message_id ON received_messages (message_id);
CREATE INDEX idx_received_messages_received_user_id ON received_messages (received_user_id);
CREATE INDEX idx_received_messages_message_id_received_user_id ON received_messages (message_id, received_user_id);