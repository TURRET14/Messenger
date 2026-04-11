import type { UserInList } from "../api/types";

export function formatUserFullName(u: {
  name: string;
  surname: string | null;
  second_name: string | null;
}): string {
  return [u.name, u.surname, u.second_name].filter(Boolean).join(" ");
}

export function userListLabel(u: UserInList): string {
  return `${u.username} — ${formatUserFullName(u)}`;
}
