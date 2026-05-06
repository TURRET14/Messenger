import type { ChatKind, ChatRole } from "../api/types";

export function chatKindLabel(kind: ChatKind): string {
  const labels: Record<ChatKind, string> = {
    PRIVATE: "Личный чат",
    GROUP: "Группа",
    CHANNEL: "Канал",
    PROFILE: "Профиль",
  };
  return labels[kind];
}

export function chatRoleLabel(role: ChatRole): string {
  const labels: Record<ChatRole, string> = {
    USER: "Пользователь",
    ADMIN: "Администратор",
    OWNER: "Владелец",
  };
  return labels[role];
}
