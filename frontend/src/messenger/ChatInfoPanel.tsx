import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, apiFetch, apiJson } from "../api/client";
import type { Chat, ChatRole, UserInList } from "../api/types";
import { Avatar, chatAvatarUrl, userAvatarUrl } from "../components/ui/Avatar";
import { useDialogs } from "../context/DialogsContext";
import { useBackendSocket } from "../hooks/useBackendSocket";
import { avatarLetterFromUser, userListLabel } from "./userFormat";

const PAGE = 50;

export interface MembershipRow {
  id: number;
  chat_id: number;
  chat_user_id: number;
  date_and_time_added: string;
  chat_role: ChatRole;
}

export function ChatInfoPanel({
  chat,
  currentUserId,
  onClose,
  onRefreshChats,
  onOpenProfile,
  variant = "sidebar",
  assetEpoch = 0,
}: {
  chat: Chat;
  currentUserId: number;
  onClose: () => void;
  onRefreshChats: () => Promise<void>;
  onOpenProfile: (userId: number) => void;
  variant?: "sidebar" | "sheet";
  assetEpoch?: number;
}) {
  const { alert, confirm } = useDialogs();
  const [members, setMembers] = useState<MembershipRow[]>([]);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [userMap, setUserMap] = useState<Record<number, UserInList>>({});
  const listRef = useRef<HTMLDivElement>(null);
  const memberPageRef = useRef(0);
  const loadingRef = useRef(false);

  const [nameEdit, setNameEdit] = useState(chat.name);
  const [friends, setFriends] = useState<UserInList[]>([]);
  const [fOff, setFOff] = useState(0);
  const [fDone, setFDone] = useState(false);
  const [privatePeerId, setPrivatePeerId] = useState<number | null>(null);

  const myMembership = members.find((m) => m.chat_user_id === currentUserId);
  const role = myMembership?.chat_role;
  const isOwner = chat.owner_user_id === currentUserId;
  const isAdmin = role === "ADMIN" || isOwner;
  const isGroupOrChannel =
    chat.chat_kind === "GROUP" || chat.chat_kind === "CHANNEL";
  const isPrivate = chat.chat_kind === "PRIVATE";
  const isProfile = chat.chat_kind === "PROFILE";

  const loadMembers = useCallback(
    async (reset: boolean) => {
      if (loadingRef.current && !reset) return;
      loadingRef.current = true;
      setLoading(true);
      try {
        const mult = reset ? 0 : memberPageRef.current + 1;
        const batch = await apiJson<MembershipRow[]>(
          `/chats/id/${chat.id}/memberships?offset_multiplier=${mult}`,
        );
        if (reset) {
          memberPageRef.current = 0;
          setMembers(batch);
          setDone(batch.length < PAGE);
        } else {
          memberPageRef.current = mult;
          setMembers((prev) => {
            const ids = new Set(prev.map((x) => x.id));
            const add = batch.filter((x) => !ids.has(x.id));
            return [...prev, ...add];
          });
          if (batch.length < PAGE) setDone(true);
        }
        for (const row of batch) {
          const uid = row.chat_user_id;
          void apiJson<UserInList>(`/users/id/${uid}`)
            .then((u) => setUserMap((p) => (p[uid] ? p : { ...p, [uid]: u })))
            .catch(() => {});
        }
      } catch (e) {
        void alert(e instanceof ApiError ? e.message : "Участники не загружены");
      } finally {
        loadingRef.current = false;
        setLoading(false);
      }
    },
    [chat.id, alert],
  );

  useEffect(() => {
    setMembers([]);
    memberPageRef.current = 0;
    setDone(false);
    setNameEdit(chat.name);
    void loadMembers(true);
  }, [chat.id, loadMembers]);

  const loadFriends = useCallback(
    async (reset: boolean) => {
      const mult = reset ? 0 : fOff + 1;
      try {
        const batch = await apiJson<(UserInList & { date_and_time_added?: string })[]>(
          `/users/me/friends?offset_multiplier=${reset ? 0 : mult}`,
        );
        if (reset) {
          setFriends(batch);
          setFOff(0);
          setFDone(batch.length < PAGE);
        } else {
          setFriends((prev) => {
            const ids = new Set(prev.map((x) => x.id));
            return [...prev, ...batch.filter((x) => !ids.has(x.id))];
          });
          setFOff(mult);
          if (batch.length < PAGE) setFDone(true);
        }
      } catch {
        /* ignore */
      }
    },
    [fOff],
  );

  useEffect(() => {
    if (isGroupOrChannel) void loadFriends(true);
  }, [isGroupOrChannel, chat.id]);

  useEffect(() => {
    if (chat.chat_kind !== "PRIVATE") {
      setPrivatePeerId(null);
      return;
    }
    void (async () => {
      try {
        const mem = await apiJson<MembershipRow[]>(
          `/chats/id/${chat.id}/memberships?offset_multiplier=0`,
        );
        const peer = mem.find((m) => m.chat_user_id !== currentUserId)?.chat_user_id ?? null;
        setPrivatePeerId(peer);
      } catch {
        setPrivatePeerId(null);
      }
    })();
  }, [chat.id, chat.chat_kind, currentUserId]);

  const canRemoveMember = (target: MembershipRow) => {
    if (!isGroupOrChannel || !isAdmin) return false;
    if (target.chat_user_id === currentUserId) return false;
    if (target.chat_role === "OWNER") return false;
    if (isOwner) return true;
    if (role === "ADMIN") return target.chat_role === "USER";
    return false;
  };

  const canPromoteToAdmin = (target: MembershipRow) => {
    if (!isGroupOrChannel || !isOwner) return false;
    if (target.chat_user_id === currentUserId) return false;
    return target.chat_role === "USER";
  };

  const canDemoteAdmin = (target: MembershipRow) => {
    if (!isGroupOrChannel || !isOwner) return false;
    if (target.chat_user_id === currentUserId) return false;
    return target.chat_role === "ADMIN";
  };

  const handleLeave = async () => {
    if (
      !(await confirm({
        message: "Покинуть этот чат?",
        danger: true,
        confirmLabel: "Выйти",
      }))
    )
      return;
    try {
      await apiFetch(`/chats/id/${chat.id}/users/me`, { method: "DELETE" });
      await onRefreshChats();
      onClose();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не вышли");
    }
  };

  const handleDeleteChat = async () => {
    if (
      !(await confirm({
        message: "Удалить чат для всех? Это действие необратимо.",
        danger: true,
        confirmLabel: "Удалить",
      }))
    )
      return;
    try {
      await apiFetch(`/chats/id/${chat.id}`, { method: "DELETE" });
      await onRefreshChats();
      onClose();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалено");
    }
  };

  const saveName = async () => {
    const n = nameEdit.trim();
    if (!n) {
      void alert("Название не может быть пустым");
      return;
    }
    try {
      await apiFetch(`/chats/id/${chat.id}/name`, {
        method: "PATCH",
        body: JSON.stringify({ name: n }),
      });
      await onRefreshChats();
      void alert("Название обновлено");
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не сохранено");
    }
  };

  const uploadAvatar = async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    try {
      await apiFetch(`/chats/id/${chat.id}/avatar`, {
        method: "PUT",
        body: fd,
      });
      await onRefreshChats();
      void alert("Фото чата обновлено");
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не загружено");
    }
  };

  const addMember = async (userId: number) => {
    try {
      await apiFetch(`/chats/id/${chat.id}/users`, {
        method: "POST",
        body: JSON.stringify({ id: userId }),
      });
      await loadMembers(true);
      await onRefreshChats();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не добавлен");
    }
  };

  const removeMember = async (m: MembershipRow) => {
    if (
      !(await confirm({
        message: "Удалить участника из чата?",
        danger: true,
      }))
    )
      return;
    try {
      await apiFetch(
        `/chats/id/${chat.id}/users/id/${m.chat_user_id}`,
        { method: "DELETE" },
      );
      await loadMembers(true);
      await onRefreshChats();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалён");
    }
  };

  const makeAdmin = async (userId: number) => {
    try {
      await apiFetch(`/chats/id/${chat.id}/admins`, {
        method: "POST",
        body: JSON.stringify({ id: userId }),
      });
      await loadMembers(true);
      await onRefreshChats();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалось назначить");
    }
  };

  const dropAdmin = async (userId: number) => {
    try {
      await apiFetch(`/chats/id/${chat.id}/admins/id/${userId}`, {
        method: "DELETE",
      });
      await loadMembers(true);
      await onRefreshChats();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалось снять роль");
    }
  };

  useBackendSocket(`/chats/${chat.id}/memberships/post`, true, () => {
    void loadMembers(true);
  });
  useBackendSocket(`/chats/${chat.id}/memberships/put`, true, () => {
    void loadMembers(true);
  });
  useBackendSocket(`/chats/${chat.id}/memberships/delete`, true, () => {
    void loadMembers(true);
  });

  const chatTitle = chat.name || "Чат";
  const chatAvatarSrc =
    chat.chat_kind === "PROFILE" && chat.owner_user_id != null
      ? userAvatarUrl(chat.owner_user_id, assetEpoch)
      : chat.chat_kind === "PRIVATE" && privatePeerId != null
        ? userAvatarUrl(privatePeerId, assetEpoch)
        : chat.has_avatar
          ? chatAvatarUrl(chat.id, assetEpoch)
          : null;

  const shell =
    variant === "sheet"
      ? {
          width: "100%" as const,
          minWidth: 0,
          borderLeft: "none",
          flex: 1,
          minHeight: 0,
          maxHeight: "100%",
        }
      : {
          width: 300,
          minWidth: 260,
          borderLeft: "1px solid var(--border)",
          flex: undefined as undefined,
          minHeight: undefined as undefined,
          maxHeight: "100%" as const,
        };

  return (
    <div
      style={{
        ...shell,
        display: "flex",
        flexDirection: "column",
        background: "var(--bg-muted)",
      }}
    >
      <div style={{ padding: 12, borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <Avatar src={chatAvatarSrc} label={chatTitle} size={72} />
          <div style={{ textAlign: "center", fontWeight: 700 }}>{chatTitle}</div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            {chat.chat_kind}
          </div>
        </div>
      </div>

      {isGroupOrChannel ? (
        <div style={{ padding: 12, borderBottom: "1px solid var(--border)" }}>
          <label className="sr-only" htmlFor="cn">Название</label>
          <input
            id="cn"
            className="ui-input"
            value={nameEdit}
            onChange={(e) => setNameEdit(e.target.value)}
            style={{ marginBottom: 8 }}
          />
          <button
            type="button"
            className="ui-btn ui-btn--primary"
            style={{ width: "100%", marginBottom: 8 }}
            onClick={() => void saveName()}
          >
            Сохранить название
          </button>
          <label className="ui-btn ui-btn--ghost" style={{ width: "100%", cursor: "pointer" }}>
            Сменить фото
            <input
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = "";
                if (f) void uploadAvatar(f);
              }}
            />
          </label>
        </div>
      ) : null}

      {isGroupOrChannel && isAdmin ? (
        <div style={{ padding: 12, borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Друзья</div>
          <div style={{ maxHeight: 160, overflowY: "auto" }}>
            {friends.map((f) => {
              const already = members.some((m) => m.chat_user_id === f.id);
              return (
                <div
                  key={f.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 6,
                  }}
                >
                  <Avatar
                    src={userAvatarUrl(f.id, assetEpoch)}
                    label={avatarLetterFromUser(f)}
                    size={32}
                  />
                  <div style={{ flex: 1, minWidth: 0, fontSize: "0.85rem" }}>
                    {userListLabel(f)}
                  </div>
                  <button
                    type="button"
                    className="ui-btn ui-btn--ghost"
                    disabled={already}
                    onClick={() => void addMember(f.id)}
                  >
                    {already ? "В чате" : "Добавить"}
                  </button>
                </div>
              );
            })}
            {!fDone ? (
              <button
                type="button"
                className="ui-btn ui-btn--ghost"
                style={{ width: "100%" }}
                onClick={() => void loadFriends(false)}
              >
                Ещё друзья…
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      <div
        ref={listRef}
        style={{ flex: 1, overflowY: "auto", padding: 12 }}
        onScroll={(e) => {
          const el = e.currentTarget;
          if (el.scrollTop + el.clientHeight >= el.scrollHeight - 24 && !done && !loading) {
            void loadMembers(false);
          }
        }}
      >
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Участники</div>
        {members.map((m) => {
          const u = userMap[m.chat_user_id];
          const label = u
            ? userListLabel(u)
            : `Пользователь #${m.chat_user_id}`;
          return (
            <div
              key={m.id}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "stretch",
                gap: 8,
                marginBottom: 10,
                padding: 8,
                borderRadius: 10,
                border: "1px solid var(--border)",
                background: "var(--bg)",
              }}
            >
              <button
                type="button"
                onClick={() => onOpenProfile(m.chat_user_id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  flex: 1,
                  minWidth: 0,
                  border: "none",
                  background: "none",
                  padding: 0,
                  cursor: "pointer",
                  textAlign: "left",
                  color: "inherit",
                }}
              >
                <Avatar
                  src={userAvatarUrl(m.chat_user_id, assetEpoch)}
                  label={u ? avatarLetterFromUser(u) : `#${m.chat_user_id}`}
                  size={36}
                />
                <div>
                  <div style={{ fontSize: "0.9rem" }}>{label}</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {m.chat_role}
                  </div>
                </div>
              </button>
              {canRemoveMember(m) || canPromoteToAdmin(m) || canDemoteAdmin(m) ? (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
                  {canPromoteToAdmin(m) ? (
                    <button
                      type="button"
                      className="ui-btn ui-btn--ghost"
                      onClick={() => void makeAdmin(m.chat_user_id)}
                    >
                      + Админ
                    </button>
                  ) : null}
                  {canDemoteAdmin(m) ? (
                    <button
                      type="button"
                      className="ui-btn ui-btn--ghost"
                      onClick={() => void dropAdmin(m.chat_user_id)}
                    >
                      Снять админа
                    </button>
                  ) : null}
                  {canRemoveMember(m) ? (
                    <button
                      type="button"
                      className="ui-btn ui-btn--ghost"
                      onClick={() => void removeMember(m)}
                    >
                      Удалить
                    </button>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      <div style={{ padding: 12, borderTop: "1px solid var(--border)" }}>
        {!isOwner && (isPrivate || isGroupOrChannel || isProfile) ? (
          <button
            type="button"
            className="ui-btn ui-btn--danger"
            style={{ width: "100%", marginBottom: 8 }}
            onClick={() => void handleLeave()}
          >
            Покинуть чат
          </button>
        ) : null}
        {isGroupOrChannel && isOwner ? (
          <button
            type="button"
            className="ui-btn ui-btn--danger"
            style={{ width: "100%" }}
            onClick={() => void handleDeleteChat()}
          >
            Удалить чат
          </button>
        ) : null}
      </div>
    </div>
  );
}
