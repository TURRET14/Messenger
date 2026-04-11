import { useEffect, useState } from "react";
import { ApiError, apiFetch, apiJson } from "../api/client";
import type { Chat, CurrentUser, FriendUser, UserBlockRow, UserPublic } from "../api/types";
import { Avatar, userAvatarUrl } from "../components/ui/Avatar";
import { ModalChrome } from "../components/ui/ModalChrome";
import { useDialogs } from "../context/DialogsContext";
import { formatUserFullName } from "./userFormat";

const PAGE = 50;

export function UserProfileModal({
  userId,
  currentUser,
  onClose,
  onOpenChat,
}: {
  userId: number;
  currentUser: CurrentUser;
  onClose: () => void;
  onOpenChat: (chatId: number) => void;
}) {
  const { alert, confirm } = useDialogs();
  const isSelf = userId === currentUser.id;
  const [u, setU] = useState<UserPublic | CurrentUser | null>(null);
  const [friendship, setFriendship] = useState<FriendUser | null>(null);
  const [blockRow, setBlockRow] = useState<UserBlockRow | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = async () => {
    setLoading(true);
    try {
      const profile = isSelf
        ? await apiJson<CurrentUser>("/users/me")
        : await apiJson<UserPublic>(`/users/id/${userId}`);
      setU(profile);
      if (!isSelf) {
        const uname = encodeURIComponent(profile.username);
        const hits = await apiJson<FriendUser[]>(
          `/users/me/friends/search/by-username?username=${uname}&offset_multiplier=0`,
        );
        setFriendship(hits.find((h) => h.id === userId) ?? null);
        let off = 0;
        let found: UserBlockRow | null = null;
        for (;;) {
          const batch = await apiJson<UserBlockRow[]>(
            `/users/me/blocks?offset_multiplier=${off}`,
          );
          found =
            batch.find((b) => b.blocked_user_id === userId) ?? null;
          if (found || batch.length < PAGE) break;
          off += 1;
        }
        setBlockRow(found);
      }
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Профиль не загружен");
      onClose();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
  }, [userId, isSelf]);

  const sendFriendRequest = async () => {
    try {
      await apiFetch("/users/me/friends/requests/send", {
        method: "POST",
        body: JSON.stringify({ id: userId }),
      });
      void alert("Запрос отправлен");
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не отправлено");
    }
  };

  const removeFriend = async () => {
    if (!friendship) return;
    if (!(await confirm({ message: "Удалить из друзей?", danger: true }))) return;
    try {
      await apiFetch(`/users/me/friends/${friendship.friendship_id}`, {
        method: "DELETE",
      });
      setFriendship(null);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалено");
    }
  };

  const openPrivate = async () => {
    try {
      const res = await apiJson<{ id: number }>("/chats/private", {
        method: "POST",
        body: JSON.stringify({ id: userId }),
      });
      onOpenChat(res.id);
      onClose();
    } catch (e) {
      const err = e instanceof ApiError ? e : null;
      if (err?.body && typeof err.body === "object") {
        const c = (err.body as { error_code?: string }).error_code;
        if (c === "PRIVATE_CHAT_ALREADY_EXISTS_ERROR") {
          void alert("Откройте чат из списка — личный диалог уже есть");
          return;
        }
      }
      void alert(err?.message ?? "Не удалось открыть чат");
    }
  };

  const openProfileChat = async () => {
    try {
      const chat = await apiJson<Chat>(`/users/id/${userId}/profile`);
      onOpenChat(chat.id);
      onClose();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалось открыть профиль");
    }
  };

  const blockUser = async () => {
    if (!(await confirm({ message: "Заблокировать пользователя?", danger: true })))
      return;
    try {
      await apiFetch("/users/me/blocks", {
        method: "POST",
        body: JSON.stringify({ id: userId }),
      });
      await reload();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не заблокировано");
    }
  };

  const unblockUser = async () => {
    if (!blockRow) return;
    try {
      await apiFetch(`/users/me/blocks/id/${blockRow.id}`, {
        method: "DELETE",
      });
      setBlockRow(null);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не разблокировано");
    }
  };

  if (loading || !u) {
    return (
      <ModalChrome title="Профиль" onClose={onClose} narrow>
        <p>Загрузка…</p>
      </ModalChrome>
    );
  }

  return (
    <ModalChrome title={isSelf ? "Мой профиль" : "Профиль"} onClose={onClose} narrow>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
        <Avatar
          src={userAvatarUrl(u.id)}
          label={u.username}
          size={88}
        />
        <div style={{ fontWeight: 700 }}>@{u.username}</div>
        <div style={{ color: "var(--text-muted)", textAlign: "center" }}>
          {formatUserFullName(u)}
        </div>
        {"email_address" in u ? (
          <div style={{ fontSize: "0.9rem" }}>{u.email_address}</div>
        ) : null}
        {u.about ? (
          <p style={{ width: "100%", fontSize: "0.9rem" }}>{u.about}</p>
        ) : null}
      </div>

      {!isSelf ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 16 }}>
          <button type="button" className="ui-btn ui-btn--primary" onClick={() => void openProfileChat()}>
            Лента профиля
          </button>
          {friendship ? (
            <>
              <button type="button" className="ui-btn ui-btn--primary" onClick={() => void openPrivate()}>
                Личный чат
              </button>
              <button type="button" className="ui-btn ui-btn--ghost" onClick={() => void removeFriend()}>
                Удалить из друзей
              </button>
            </>
          ) : (
            <button type="button" className="ui-btn ui-btn--primary" onClick={() => void sendFriendRequest()}>
              Запрос в друзья
            </button>
          )}
          {blockRow ? (
            <button type="button" className="ui-btn ui-btn--ghost" onClick={() => void unblockUser()}>
              Разблокировать
            </button>
          ) : (
            <button type="button" className="ui-btn ui-btn--danger" onClick={() => void blockUser()}>
              Заблокировать
            </button>
          )}
        </div>
      ) : (
        <p style={{ marginTop: 16, fontSize: "0.9rem", color: "var(--text-muted)" }}>
          Редактирование данных — в меню «Профиль».
        </p>
      )}
    </ModalChrome>
  );
}
