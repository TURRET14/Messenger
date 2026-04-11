import type { CurrentUser } from "../api/types";
import { MessengerShell } from "../messenger/MessengerShell";

export function MessengerApp({
  currentUser,
  onLogout,
}: {
  currentUser: CurrentUser;
  onLogout: () => void;
}) {
  return <MessengerShell currentUser={currentUser} onLogout={onLogout} />;
}
