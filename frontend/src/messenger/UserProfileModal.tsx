import { useEffect, useState } from "react";
import { ApiError, apiFetch, apiJson } from "../api/client";
import type { Chat, CurrentUser, FriendUser, UserBlockRow, UserPublic } from "../api/types";
import { IconUser } from "../components/Icons";
import { Avatar, userAvatarUrl } from "../components/ui/Avatar";
import { ModalChrome } from "../components/ui/ModalChrome";
import { useDialogs } from "../context/DialogsContext";
import {
  avatarLetterFromUser,
  formatUserFullName,
  userListLabel,
} from "./userFormat";

const PAGE = 50;

async function openOrCreatePrivateChat(userId: number): Promise<number> {
  try {
    const res = await apiJson<{ id: number }>(`/chats/private`, {
      method: "POST",
      body: JSON.stringify({ id: userId }),
    });
    return res.id;
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) {
      const body = e.body as { error_code?: string } | undefined;
      if (body?.error_code === "PRIVATE_CHAT_ALREADY_EXISTS_ERROR") {
        const ex = await apiJson<{ id: number }>(
          `/chats/private/with-user/${userId}`,
        );
        return ex.id;
      }
    }
    throw e;
  }
}

export function UserProfileModal({
  userId,
  currentUser,
  onClose,
  onOpenChat,
  assetEpoch = 0,
}: {
  userId: number;
  currentUser: CurrentUser;
  onClose: () => void;
  onOpenChat: (chatId: number, options?: { ephemeral?: boolean }) => void;
  assetEpoch?: number;
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
      const id = await openOrCreatePrivateChat(userId);
      onOpenChat(id);
      onClose();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалось открыть чат");
    }
  };

  const openProfileChat = async () => {
    try {
      const chat = await apiJson<Chat>(`/users/id/${userId}/profile`);
      onOpenChat(chat.id, { ephemeral: true });
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

  const genderLabel =
    u.gender === "MALE" ? "Мужской" : u.gender === "FEMALE" ? "Женский" : "—";

  const readOnlyRows: { label: string; value: string }[] = [
    { label: "Имя пользователя", value: `@${u.username}` },
    { label: "ФИО", value: formatUserFullName(u) || "—" },
    {
      label: "Дата рождения",
      value: u.date_of_birth?.slice(0, 10) ?? "—",
    },
    { label: "Пол", value: genderLabel },
    { label: "Телефон", value: u.phone_number ?? "—" },
    { label: "О себе", value: u.about?.trim() ? u.about : "—" },
    {
      label: "Дата регистрации",
      value: new Date(u.date_and_time_registered).toLocaleString(),
    },
  ];

  return (
    <ModalChrome title={isSelf ? "Мой профиль" : "Профиль"} onClose={onClose} narrow>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
        <Avatar
          src={userAvatarUrl(u.id, assetEpoch)}
          label={avatarLetterFromUser(u)}
          size={88}
        />
        <div style={{ fontWeight: 700 }}>{userListLabel(u)}</div>
      </div>

      <div
        style={{
          marginTop: 16,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          fontSize: "0.9rem",
        }}
      >
        {readOnlyRows.map((row) => (
          <div key={row.label}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              {row.label}
            </div>
            <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {row.value}
            </div>
          </div>
        ))}
        {"email_address" in u ? (
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Электронная почта
            </div>
            <div>{u.email_address}</div>
          </div>
        ) : null}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 16 }}>
        <button type="button" className="ui-btn ui-btn--primary" onClick={() => void openProfileChat()}>
          <IconUser size={18} /> Лента профиля
        </button>

        {!isSelf ? (
          <>
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
          </>
        ) : (
          <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Редактирование данных и смена фото — в меню «Профиль».
          </p>
        )}
      </div>
    </ModalChrome>
  );
}
