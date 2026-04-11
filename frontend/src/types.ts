export type ThemeMode = 'system' | 'light' | 'dark';

export type Gender = 'MALE' | 'FEMALE';
export type ChatKind = 'PRIVATE' | 'GROUP' | 'CHANNEL' | 'PROFILE';
export type ChatRole = 'USER' | 'ADMIN' | 'OWNER';

export interface ApiErrorPayload {
  error_code?: string;
  error_message?: string;
  error_status_code?: number;
}

export interface FieldValidationError {
  loc: Array<string | number>;
  msg: string;
  type: string;
}

export interface ApiValidationError {
  detail: FieldValidationError[];
}

export interface IdResponse {
  id: number;
}

export interface UserListItem {
  id: number;
  username: string;
  name: string;
  surname: string | null;
  second_name: string | null;
}

export interface FriendUserListItem extends UserListItem {
  friendship_id: number;
  date_and_time_added: string;
}

export interface FriendRequest {
  id: number;
  sender_user_id: number;
  receiver_user_id: number;
  date_and_time_sent: string;
}

export interface UserProfile extends UserListItem {
  date_of_birth: string | null;
  gender: Gender | null;
  phone_number: string | null;
  about: string | null;
  date_and_time_registered: string;
}

export interface CurrentUserProfile extends UserProfile {
  email_address: string;
}

export interface UserSession {
  session_id: string;
  user_id: number;
  user_agent: string;
  creation_datetime: number;
  expiration_datetime: number;
}

export interface UserBlock {
  id: number;
  user_id: number;
  blocked_user_id: number;
  date_and_time_blocked: string;
}

export interface Chat {
  id: number;
  chat_kind: ChatKind;
  name: string;
  owner_user_id: number | null;
  date_and_time_created: string;
}

export interface ChatMembership {
  id: number;
  chat_id: number;
  chat_user_id: number;
  date_and_time_added: string;
  chat_role: ChatRole;
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

export interface LastMessageResponse {
  message: Message | null;
}

export interface MessageAttachment {
  id: number;
  message_id: number;
  chat_id: number;
  file_name: string;
  kind: 'image' | 'video' | 'audio' | 'file';
}

export interface MessageReadMark {
  id: number;
  chat_id: number;
  message_id: number;
  date_and_time_received: string;
  reader_user_id: number;
}

export interface PendingAttachment {
  id: string;
  file: File;
  previewUrl: string | null;
  kind: 'image' | 'video' | 'audio' | 'file';
  progress?: number;
}

export interface ErrorDialogState {
  open: boolean;
  title: string;
  code: string;
  message: string;
  status: number;
}

export interface ConfirmationDialogState {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  danger?: boolean;
  onConfirm: (() => void | Promise<void>) | null;
}

export type ModalState =
  | { type: 'none' }
  | { type: 'profile'; userId: number; editable: boolean }
  | { type: 'friends' }
  | { type: 'users' }
  | { type: 'received-requests' }
  | { type: 'sent-requests' }
  | { type: 'blocks' }
  | { type: 'create-chat' }
  | { type: 'edit-profile' }
  | { type: 'edit-email' }
  | { type: 'confirm-email' }
  | { type: 'edit-login' }
  | { type: 'edit-password' }
  | { type: 'sessions' }
  | { type: 'add-member'; chatId: number }
  | { type: 'edit-chat-name'; chatId: number; initialName: string }
  | { type: 'delete-user'; login: string };
