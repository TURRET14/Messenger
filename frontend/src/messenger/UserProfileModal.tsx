import { useEffect, useState, type ReactNode } from "react";
import { ApiError, apiFetch, apiJson } from "../api/client";
import type {
  Chat,
  CurrentUser,
  FriendUser,
  UserBlockRow,
  UserPublic,
} from "../api/types";
import {
  IconAtSign,
  IconBan,
  IconCalendar,
  IconChat,
  IconInfo,
  IconMessageCircle,
  IconPhone,
  IconUser,
  IconUserCheck,
  IconUserPlus,
  IconUserX,
} from "../components/Icons";
import { Avatar, userAvatarUrl } from "../components/ui/Avatar";
import { ModalChrome } from "../components/ui/ModalChrome";
import { useDialogs } from "../context/DialogsContext";
import {
  avatarLetterFromUser,
  formatUserFullName,
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
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            padding: 24,
            color: "var(--text-muted)",
          }}
        >
          <span className="ui-spinner" aria-hidden="true" /> Загружаем профиль…
        </div>
      </ModalChrome>
    );
  }

  const genderLabel =
    u.gender === "MALE" ? "Мужской" : u.gender === "FEMALE" ? "Женский" : "—";

  return (
    <ModalChrome title={isSelf ? "Мой профиль" : "Профиль"} onClose={onClose} narrow>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 10,
          padding: "4px 0 16px",
        }}
      >
        <Avatar
          src={userAvatarUrl(u.id, assetEpoch)}
          label={avatarLetterFromUser(u)}
          size={104}
        />
        <div
          style={{
            fontWeight: 700,
            fontSize: "1.1rem",
            textAlign: "center",
            wordBreak: "break-word",
          }}
        >
          {formatUserFullName(u) || u.username}
        </div>
        <div
          className="ui-chip"
          style={{ display: "inline-flex", gap: 6 }}
        >
          <IconAtSign size={12} />
          {u.username}
        </div>
      </div>

      {/* Основной набор действий — карточки */}
      <div className="profile-action-grid" style={{ marginBottom: 16 }}>
        {!isSelf ? (
          <>
            {friendship ? (
              <button
                type="button"
                className="profile-action-card"
                onClick={() => void openPrivate()}
              >
                <span className="icon-wrap">
                  <IconMessageCircle size={18} />
                </span>
                Личный чат
              </button>
            ) : (
              <button
                type="button"
                className="profile-action-card"
                onClick={() => void sendFriendRequest()}
              >
                <span className="icon-wrap">
                  <IconUserPlus size={18} />
                </span>
                В друзья
              </button>
            )}
            <button
              type="button"
              className="profile-action-card"
              onClick={() => void openProfileChat()}
            >
              <span className="icon-wrap">
                <IconChat size={18} />
              </span>
              Лента
            </button>
            {blockRow ? (
              <button
                type="button"
                className="profile-action-card"
                onClick={() => void unblockUser()}
              >
                <span className="icon-wrap">
                  <IconUserCheck size={18} />
                </span>
                Разблокировать
              </button>
            ) : (
              <button
                type="button"
                className="profile-action-card profile-action-card--danger"
                onClick={() => void blockUser()}
              >
                <span className="icon-wrap">
                  <IconBan size={18} />
                </span>
                Заблокировать
              </button>
            )}
          </>
        ) : (
          <button
            type="button"
            className="profile-action-card"
            onClick={() => void openProfileChat()}
          >
            <span className="icon-wrap">
              <IconChat size={18} />
            </span>
            Моя лента
          </button>
        )}
      </div>

      {/* Информация */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <ProfileInfoRow
          icon={<IconUser size={16} />}
          label="ФИО"
          value={formatUserFullName(u) || "—"}
        />
        <ProfileInfoRow
          icon={<IconCalendar size={16} />}
          label="Дата рождения"
          value={u.date_of_birth?.slice(0, 10) ?? "—"}
        />
        <ProfileInfoRow
          icon={<IconUser size={16} />}
          label="Пол"
          value={genderLabel}
        />
        <ProfileInfoRow
          icon={<IconPhone size={16} />}
          label="Телефон"
          value={u.phone_number ?? "—"}
        />
        <ProfileInfoRow
          icon={<IconInfo size={16} />}
          label="О себе"
          value={u.about?.trim() || "—"}
          multiline
        />
        <ProfileInfoRow
          icon={<IconCalendar size={16} />}
          label="Дата регистрации"
          value={new Date(u.date_and_time_registered).toLocaleString()}
        />
        {"email_address" in u ? (
          <ProfileInfoRow
            icon={<IconAtSign size={16} />}
            label="Электронная почта"
            value={u.email_address}
          />
        ) : null}
      </div>

      {/* Дополнительные действия для друзей */}
      {!isSelf && friendship ? (
        <>
          <hr className="ui-divider" style={{ margin: "16px 0 12px" }} />
          <button
            type="button"
            className="ui-btn ui-btn--block"
            onClick={() => void removeFriend()}
            style={{ color: "var(--danger)", borderColor: "var(--danger)" }}
          >
            <IconUserX size={16} />
            Удалить из друзей
          </button>
        </>
      ) : null}

      {isSelf ? (
        <p
          style={{
            margin: "16px 0 0",
            fontSize: "0.85rem",
            color: "var(--text-muted)",
            padding: "10px 12px",
            background: "var(--bg-muted)",
            borderRadius: 10,
            border: "1.5px solid var(--border)",
          }}
        >
          Редактирование данных и смена фото — в разделе «Профиль» главного меню.
        </p>
      ) : null}
    </ModalChrome>
  );
}

function ProfileInfoRow({
  icon,
  label,
  value,
  multiline,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  multiline?: boolean;
}) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
      <span
        style={{
          width: 32,
          height: 32,
          borderRadius: 10,
          background: "var(--bg-muted)",
          color: "var(--text-muted)",
          display: "grid",
          placeItems: "center",
          flexShrink: 0,
        }}
      >
        {icon}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            marginBottom: 2,
          }}
        >
          {label}
        </div>
        <div
          style={{
            fontSize: "0.92rem",
            whiteSpace: multiline ? "pre-wrap" : "normal",
            wordBreak: "break-word",
          }}
        >
          {value}
        </div>
      </div>
    </div>
  );
}
