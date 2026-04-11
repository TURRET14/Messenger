import type { UserInList } from "../api/types";

export function formatUserFullName(u: {
  name: string;
  surname: string | null;
  second_name: string | null;
}): string {
  return [u.surname, u.name, u.second_name].filter(Boolean).join(" ");
}

/** Первая буква для аватара-заглушки: из имени, не из username */
export function avatarLetterFromUser(u: {
  name: string;
  surname: string | null;
  second_name: string | null;
}): string {
  const base = u.name?.trim() || formatUserFullName(u).trim() || "?";
  return base[0] ?? "?";
}

export function userListLabel(u: UserInList): string {
  return `${u.username} — ${formatUserFullName(u)}`;
}
