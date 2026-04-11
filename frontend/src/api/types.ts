export type ChatKind = "PRIVATE" | "GROUP" | "CHANNEL" | "PROFILE";

export interface ChatLastMessage {
  message_text: string | null;
  sender_user_id: number | null;
  date_and_time_sent: string | null;
}

export interface Chat {
  id: number;
  chat_kind: ChatKind;
  name: string;
  owner_user_id: number | null;
  date_and_time_created: string;
  has_avatar?: boolean;
  last_message?: ChatLastMessage | null;
}

export interface UserInList {
  id: number;
  username: string;
  name: string;
  surname: string | null;
  second_name: string | null;
}

export interface FriendUser extends UserInList {
  friendship_id: number;
  date_and_time_added: string;
}

export interface UserPublic extends UserInList {
  date_of_birth: string | null;
  gender: "MALE" | "FEMALE" | null;
  phone_number: string | null;
  about: string | null;
  date_and_time_registered: string;
}

export interface CurrentUser extends UserPublic {
  email_address: string;
}

export interface Message {
  id: number;
  chat_id: number;
  sender_user_id: number | null;
  date_and_time_sent: string;
  date_and_time_edited: string | null;
  message_text: string | null;
  reply_message_id: number | null;
  parent_message_id: number | null;
  is_read: boolean | null;
}

export interface MessageAttachmentMeta {
  id: number;
  message_id: number;
  chat_id: number;
  file_extension: string;
}

export interface ApiErrorBody {
  error_code?: string;
  error_message?: string;
}

export type ChatRole = "USER" | "ADMIN" | "OWNER";

export interface FriendRequest {
  id: number;
  sender_user_id: number;
  receiver_user_id: number;
  date_and_time_sent: string;
}

export interface UserBlockRow {
  id: number;
  user_id: number;
  blocked_user_id: number;
  date_and_time_blocked: string;
}
