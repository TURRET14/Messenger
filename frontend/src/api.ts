import { API_BASE_URL } from './config';
import type {
  ApiErrorPayload,
  ApiValidationError,
  Chat,
  ChatMembership,
  CurrentUserProfile,
  FriendRequest,
  FriendUserListItem,
  IdResponse,
  LastMessageResponse,
  Message,
  MessageAttachment,
  UserBlock,
  UserListItem,
  UserProfile,
  UserSession,
} from './types';

export class ApiError extends Error {
  status: number;
  code: string;
  payload: unknown;

  constructor(status: number, code: string, message: string, payload: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.payload = payload;
  }
}

function buildUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

function normalizeApiError(status: number, payload: unknown): ApiError {
  const defaultMessage = 'Произошла ошибка при обращении к серверу.';

  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const validation = payload as ApiValidationError;
    if (Array.isArray(validation.detail)) {
      const first = validation.detail[0];
      return new ApiError(status, 'VALIDATION_ERROR', first?.msg ?? defaultMessage, payload);
    }
  }

  if (payload && typeof payload === 'object' && 'error_message' in payload) {
    const apiPayload = payload as ApiErrorPayload;
    return new ApiError(
      status,
      apiPayload.error_code ?? 'API_ERROR',
      apiPayload.error_message ?? defaultMessage,
      payload,
    );
  }

  return new ApiError(status, 'UNKNOWN_ERROR', defaultMessage, payload);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildUrl(path), {
    credentials: 'include',
    headers: {
      ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  const contentType = response.headers.get('content-type') ?? '';
  const hasJson = contentType.includes('application/json');
  const payload = hasJson ? await response.json() : null;

  if (!response.ok) {
    throw normalizeApiError(response.status, payload);
  }

  return payload as T;
}

type UploadOptions = {
  method?: 'POST' | 'PUT' | 'PATCH';
  onProgress?: (progress: number) => void;
};

async function upload<T>(path: string, formData: FormData, options?: UploadOptions): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(options?.method ?? 'POST', buildUrl(path), true);
    xhr.withCredentials = true;

    xhr.upload.onprogress = (event) => {
      if (!options?.onProgress || !event.lengthComputable) {
        return;
      }

      options.onProgress(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onerror = () => {
      reject(new ApiError(0, 'NETWORK_ERROR', 'Не удалось выполнить загрузку файла.', null));
    };

    xhr.onload = () => {
      const contentType = xhr.getResponseHeader('content-type') ?? '';
      const payload = contentType.includes('application/json') && xhr.responseText ? JSON.parse(xhr.responseText) : null;

      if (xhr.status < 200 || xhr.status >= 300) {
        reject(normalizeApiError(xhr.status, payload));
        return;
      }

      resolve(payload as T);
    };

    xhr.send(formData);
  });
}

export const api = {
  buildUrl,
  async getCurrentUser() {
    return request<CurrentUserProfile>('/users/me');
  },
  async getCurrentUserLogin() {
    return request<{ login: string }>('/users/me/login');
  },
  async login(data: { login: string; password: string }) {
    await request<null>('/login', { method: 'POST', body: JSON.stringify(data) });
  },
  async register(data: {
    username: string;
    name: string;
    surname: string | null;
    second_name: string | null;
    email_address: string;
    login: string;
    password: string;
  }) {
    await request<null>('/users/register', { method: 'POST', body: JSON.stringify(data) });
  },
  async confirmRegistration(code: string) {
    return request<IdResponse>('/users', { method: 'POST', body: JSON.stringify({ code }) });
  },
  async getSessions() {
    return request<UserSession[]>('/users/me/sessions');
  },
  async deleteSession(sessionId: string) {
    await request<null>('/users/me/sessions', { method: 'DELETE', body: JSON.stringify({ session_id: sessionId }) });
  },
  async deleteAllSessions() {
    await request<null>('/users/me/sessions/all', { method: 'DELETE' });
  },
  async getUser(userId: number) {
    return request<UserProfile>(`/users/id/${userId}`);
  },
  async updateProfile(data: Record<string, unknown>) {
    await request<null>('/users/me', { method: 'PATCH', body: JSON.stringify(data) });
  },
  async updateEmail(email_address: string) {
    await request<null>('/users/me/email', { method: 'PATCH', body: JSON.stringify({ email_address }) });
  },
  async confirmEmail(code: string) {
    await request<null>('/users/me/email/confirm', { method: 'PATCH', body: JSON.stringify({ code }) });
  },
  async updateLogin(login: string) {
    await request<null>('/users/me/login', { method: 'PUT', body: JSON.stringify({ login }) });
  },
  async updatePassword(old_password: string, new_password: string) {
    await request<null>('/users/me/password', {
      method: 'PUT',
      body: JSON.stringify({ old_password, new_password }),
    });
  },
  async updateAvatar(file: File, onProgress?: (progress: number) => void) {
    const formData = new FormData();
    formData.append('file', file);
    await upload<null>('/users/me/avatar', formData, { method: 'PUT', onProgress });
  },
  async deleteAvatar() {
    await request<null>('/users/me/avatar', { method: 'DELETE' });
  },
  async deleteUser() {
    await request<null>('/users/me', { method: 'DELETE' });
  },
  async getUsers(offset: number) {
    return request<UserListItem[]>(`/users?offset_multiplier=${offset}`);
  },
  async searchUsersByUsername(offset: number, username: string) {
    return request<UserListItem[]>(
      `/users/search/by-username?offset_multiplier=${offset}&username=${encodeURIComponent(username)}`,
    );
  },
  async searchUsersByNames(offset: number, params: { name?: string; surname?: string; second_name?: string }) {
    const search = new URLSearchParams({ offset_multiplier: String(offset) });
    if (params.name) search.set('name', params.name);
    if (params.surname) search.set('surname', params.surname);
    if (params.second_name) search.set('second_name', params.second_name);
    return request<UserListItem[]>(`/users/search/by-names?${search.toString()}`);
  },
  async getFriends(offset: number) {
    return request<FriendUserListItem[]>(`/users/me/friends?offset_multiplier=${offset}`);
  },
  async searchFriendsByUsername(offset: number, username: string) {
    return request<FriendUserListItem[]>(
      `/users/me/friends/search/by-username?offset_multiplier=${offset}&username=${encodeURIComponent(username)}`,
    );
  },
  async searchFriendsByNames(offset: number, params: { name?: string; surname?: string; second_name?: string }) {
    const search = new URLSearchParams({ offset_multiplier: String(offset) });
    if (params.name) search.set('name', params.name);
    if (params.surname) search.set('surname', params.surname);
    if (params.second_name) search.set('second_name', params.second_name);
    return request<FriendUserListItem[]>(`/users/me/friends/search/by-names?${search.toString()}`);
  },
  async getSentFriendRequests(offset: number) {
    return request<FriendRequest[]>(`/users/me/friends/requests/sent?offset_multiplier=${offset}`);
  },
  async getReceivedFriendRequests(offset: number) {
    return request<FriendRequest[]>(`/users/me/friends/requests/received?offset_multiplier=${offset}`);
  },
  async sendFriendRequest(userId: number) {
    return request<IdResponse>('/users/me/friends/requests/send', { method: 'POST', body: JSON.stringify({ id: userId }) });
  },
  async acceptFriendRequest(requestId: number) {
    return request<IdResponse>(`/users/me/friends/requests/received/id/${requestId}`, { method: 'PUT' });
  },
  async declineFriendRequest(requestId: number) {
    await request<null>(`/users/me/friends/requests/received/id/${requestId}`, { method: 'DELETE' });
  },
  async deleteSentFriendRequest(requestId: number) {
    await request<null>(`/users/me/friends/requests/sent/id/${requestId}`, { method: 'DELETE' });
  },
  async deleteFriendship(friendshipId: number) {
    await request<null>(`/users/me/friends/${friendshipId}`, { method: 'DELETE' });
  },
  async blockUser(userId: number) {
    return request<IdResponse>('/users/me/blocks', { method: 'POST', body: JSON.stringify({ id: userId }) });
  },
  async unblockUser(blockId: number) {
    await request<null>(`/users/me/blocks/id/${blockId}`, { method: 'DELETE' });
  },
  async getBlocks() {
    return request<UserBlock[]>('/users/me/blocks');
  },
  async getChats(offset: number) {
    return request<Chat[]>(`/chats?offset_multiplier=${offset}`);
  },
  async getChat(chatId: number) {
    return request<Chat>(`/chats/id/${chatId}`);
  },
  async getChatMemberships(chatId: number, offset: number) {
    return request<ChatMembership[]>(`/chats/id/${chatId}/memberships?offset_multiplier=${offset}`);
  },
  async getChatMembership(chatId: number, membershipId: number) {
    return request<ChatMembership>(`/chats/id/${chatId}/memberships/id/${membershipId}`);
  },
  async createPrivateChat(userId: number) {
    return request<IdResponse>('/chats/private', { method: 'POST', body: JSON.stringify({ id: userId }) });
  },
  async createGroupChat(name: string) {
    return request<IdResponse>('/chats/group', { method: 'POST', body: JSON.stringify({ name }) });
  },
  async createChannel(name: string) {
    return request<IdResponse>('/chats/channels', { method: 'POST', body: JSON.stringify({ name }) });
  },
  async updateChatAvatar(chatId: number, file: File, onProgress?: (progress: number) => void) {
    const formData = new FormData();
    formData.append('file', file);
    await upload<null>(`/chats/id/${chatId}/avatar`, formData, { method: 'PUT', onProgress });
  },
  async deleteChatAvatar(chatId: number) {
    await request<null>(`/chats/id/${chatId}/avatar`, { method: 'DELETE' });
  },
  async updateChatName(chatId: number, name: string) {
    await request<null>(`/chats/id/${chatId}/name`, { method: 'PATCH', body: JSON.stringify({ name }) });
  },
  async updateChatOwner(chatId: number, userId: number) {
    await request<null>(`/chats/id/${chatId}/owner`, { method: 'PATCH', body: JSON.stringify({ id: userId }) });
  },
  async addChatAdmin(chatId: number, userId: number) {
    await request<null>(`/chats/id/${chatId}/admins`, { method: 'POST', body: JSON.stringify({ id: userId }) });
  },
  async deleteChatAdmin(chatId: number, userId: number) {
    await request<null>(`/chats/id/${chatId}/admins/id/${userId}`, { method: 'DELETE' });
  },
  async addChatUser(chatId: number, userId: number) {
    return request<IdResponse>(`/chats/id/${chatId}/users`, { method: 'POST', body: JSON.stringify({ id: userId }) });
  },
  async deleteChatUser(chatId: number, userId: number) {
    await request<null>(`/chats/id/${chatId}/users/id/${userId}`, { method: 'DELETE' });
  },
  async leaveChat(chatId: number) {
    await request<null>(`/chats/id/${chatId}/users/me`, { method: 'DELETE' });
  },
  async deleteChat(chatId: number) {
    await request<null>(`/chats/id/${chatId}`, { method: 'DELETE' });
  },
  async getProfileChat(userId: number) {
    return request<Chat>(`/users/id/${userId}/profile`);
  },
  async getMessages(chatId: number, offset: number) {
    return request<Message[]>(`/chats/id/${chatId}/messages?offset_multiplier=${offset}`);
  },
  async getComments(chatId: number, messageId: number, offset: number) {
    return request<Message[]>(`/chats/id/${chatId}/messages/id/${messageId}/comments?offset_multiplier=${offset}`);
  },
  async getMessage(chatId: number, messageId: number) {
    return request<Message>(`/chats/id/${chatId}/messages/id/${messageId}`);
  },
  async postMessage(
    chatId: number,
    payload: { messageText: string; replyMessageId?: number | null; parentMessageId?: number | null; files: File[] },
    onProgress?: (progress: number) => void,
  ) {
    const formData = new FormData();
    formData.append('message_text', payload.messageText);
    if (payload.replyMessageId) {
      formData.append('reply_message_id', String(payload.replyMessageId));
    }
    if (payload.parentMessageId) {
      formData.append('parent_message_id', String(payload.parentMessageId));
    }
    for (const file of payload.files) {
      formData.append('file_attachments_list', file);
    }
    return upload<IdResponse>(`/chats/id/${chatId}/messages`, formData, { method: 'POST', onProgress });
  },
  async deleteMessage(chatId: number, messageId: number) {
    await request<null>(`/chats/id/${chatId}/messages/id/${messageId}`, { method: 'DELETE' });
  },
  async updateMessage(chatId: number, messageId: number, messageText: string) {
    await request<null>(`/chats/id/${chatId}/messages/id/${messageId}`, {
      method: 'PUT',
      body: JSON.stringify({ message_text: messageText }),
    });
  },
  async searchMessages(chatId: number, offset: number, messageText: string) {
    return request<Message[]>(
      `/chats/id/${chatId}/messages/search?offset_multiplier=${offset}&message_text=${encodeURIComponent(messageText)}`,
    );
  },
  async searchComments(chatId: number, rootMessageId: number, offset: number, messageText: string) {
    return request<Message[]>(
      `/chats/id/${chatId}/messages/id/${rootMessageId}/comments/search?offset_multiplier=${offset}&message_text=${encodeURIComponent(messageText)}`,
    );
  },
  async markMessageAsRead(chatId: number, messageId: number) {
    return request<IdResponse>(`/chats/id/${chatId}/messages/id/${messageId}/read`, { method: 'POST' });
  },
  async getLastMessage(chatId: number) {
    return request<LastMessageResponse>(`/chats/id/${chatId}/messages/last`);
  },
  async getMessageAttachments(chatId: number, messageId: number) {
    return request<MessageAttachment[]>(`/chats/id/${chatId}/messages/id/${messageId}/attachments`);
  },
};
