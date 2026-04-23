import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, apiFetch, apiJson } from "../api/client";
import type { Chat, ChatRole, UserInList } from "../api/types";
import { Avatar, chatAvatarUrl, userAvatarUrl } from "../components/ui/Avatar";
import { ActionMenu, type ActionMenuItem } from "../components/ui/ActionMenu";
import { ModalChrome } from "../components/ui/ModalChrome";
import { ValidationError } from "../components/ui/ValidationError";
import { useDialogs } from "../context/DialogsContext";
import { useBackendSocket } from "../hooks/useBackendSocket";
import { validateChatName, validateImageFile } from "../validation";
import { chatKindLabel, chatRoleLabel } from "./labels";
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
  privatePeerId: knownPrivatePeerId = null,
  variant = "sidebar",
  assetEpoch = 0,
}: {
  chat: Chat;
  currentUserId: number;
  onClose: () => void;
  onRefreshChats: () => Promise<void>;
  onOpenProfile: (userId: number) => void;
  privatePeerId?: number | null;
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
  const [chatProfileError, setChatProfileError] = useState<string | null>(null);
  const [friends, setFriends] = useState<UserInList[]>([]);
  const [fOff, setFOff] = useState(0);
  const [fDone, setFDone] = useState(false);
  const [addMembersOpen, setAddMembersOpen] = useState(false);
  const [fetchedPrivatePeerId, setFetchedPrivatePeerId] = useState<number | null>(null);

  const myMembership = members.find((m) => m.chat_user_id === currentUserId);
  const role = myMembership?.chat_role;
  const isOwner = chat.owner_user_id === currentUserId;
  const isAdmin = role === "ADMIN" || isOwner;
  const isGroupOrChannel =
    chat.chat_kind === "GROUP" || chat.chat_kind === "CHANNEL";
  const isPrivate = chat.chat_kind === "PRIVATE";
  const isProfile = chat.chat_kind === "PROFILE";
  const canEditChatProfile = isGroupOrChannel && isAdmin;
  const canAddMembers = isGroupOrChannel && myMembership != null;

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

  const refreshMembers = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setLoading(true);
    try {
      const targetPages = memberPageRef.current + 1;
      const merged: MembershipRow[] = [];
      let nextDone = false;
      let lastLoadedPage = 0;

      for (let mult = 0; mult < targetPages; mult += 1) {
        const batch = await apiJson<MembershipRow[]>(
          `/chats/id/${chat.id}/memberships?offset_multiplier=${mult}`,
        );
        lastLoadedPage = mult;
        const ids = new Set(merged.map((item) => item.id));
        merged.push(...batch.filter((item) => !ids.has(item.id)));
        for (const row of batch) {
          const uid = row.chat_user_id;
          void apiJson<UserInList>(`/users/id/${uid}`)
            .then((u) => setUserMap((p) => (p[uid] ? p : { ...p, [uid]: u })))
            .catch(() => {});
        }
        if (batch.length < PAGE) {
          nextDone = true;
          break;
        }
      }

      memberPageRef.current = lastLoadedPage;
      setMembers(merged);
      setDone(nextDone);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Участники не загружены");
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [chat.id, alert]);

  useEffect(() => {
    setMembers([]);
    memberPageRef.current = 0;
    setDone(false);
    setNameEdit(chat.name);
    setChatProfileError(null);
    void refreshMembers();
  }, [chat.id, refreshMembers]);

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
      setFetchedPrivatePeerId(null);
      return;
    }
    if (knownPrivatePeerId != null) {
      setFetchedPrivatePeerId(null);
      return;
    }
    void (async () => {
      try {
        const mem = await apiJson<MembershipRow[]>(
          `/chats/id/${chat.id}/memberships?offset_multiplier=0`,
        );
        const peer = mem.find((m) => m.chat_user_id !== currentUserId)?.chat_user_id ?? null;
        setFetchedPrivatePeerId(peer);
      } catch {
        setFetchedPrivatePeerId(null);
      }
    })();
  }, [chat.id, chat.chat_kind, currentUserId, knownPrivatePeerId]);

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
    const validationError = validateChatName(n);
    if (validationError) {
      setChatProfileError(validationError);
      return;
    }
    setChatProfileError(null);
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
    const validationError = validateImageFile(file, "Фото чата");
    if (validationError) {
      setChatProfileError(validationError);
      return;
    }
    setChatProfileError(null);
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
      await refreshMembers();
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
      await refreshMembers();
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
      await refreshMembers();
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
      await refreshMembers();
      await onRefreshChats();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалось снять роль");
    }
  };

  const membershipSocketEnabled = canAddMembers;

  useBackendSocket(`/chats/${chat.id}/memberships/post`, membershipSocketEnabled, () => {
    void refreshMembers();
  });
  useBackendSocket(`/chats/${chat.id}/memberships/put`, membershipSocketEnabled, () => {
    void refreshMembers();
  });
  useBackendSocket(`/chats/${chat.id}/memberships/delete`, membershipSocketEnabled, () => {
    void refreshMembers();
  });

  const chatTitle = chat.name || "Чат";
  const privatePeerId = knownPrivatePeerId ?? fetchedPrivatePeerId;
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
            {chatKindLabel(chat.chat_kind)}
          </div>
        </div>
      </div>

      {canEditChatProfile ? (
        <div style={{ padding: 12, borderBottom: "1px solid var(--border)" }}>
          <label className="sr-only" htmlFor="cn">Название</label>
          <input
            id="cn"
            className="ui-input"
            value={nameEdit}
            onChange={(e) => {
              setNameEdit(e.target.value);
              setChatProfileError(null);
            }}
            style={{ marginBottom: 8 }}
            maxLength={100}
          />
          <ValidationError message={chatProfileError} />
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

      {canAddMembers ? (
        <div style={{ padding: 12, borderBottom: "1px solid var(--border)" }}>
          <button
            type="button"
            className="ui-btn ui-btn--primary"
            style={{ width: "100%" }}
            onClick={() => setAddMembersOpen(true)}
          >
            Добавить участников
          </button>
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
          const memberActions: ActionMenuItem[] = [
            {
              label: "Открыть профиль",
              onSelect: () => onOpenProfile(m.chat_user_id),
            },
            ...(canPromoteToAdmin(m)
              ? [
                  {
                    label: "Назначить администратором",
                    onSelect: () => void makeAdmin(m.chat_user_id),
                  },
                ]
              : []),
            ...(canDemoteAdmin(m)
              ? [
                  {
                    label: "Снять администратора",
                    onSelect: () => void dropAdmin(m.chat_user_id),
                  },
                ]
              : []),
            ...(canRemoveMember(m)
              ? [
                  {
                    label: "Удалить из чата",
                    onSelect: () => void removeMember(m),
                    danger: true,
                  },
                ]
              : []),
          ];
          return (
            <ActionMenu
              key={m.id}
              items={memberActions}
              label="Действия с участником"
            >
              {({ button, onContextMenu }) => (
                <div
                  onContextMenu={onContextMenu}
                  style={{
                    display: "flex",
                    alignItems: "center",
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
                        {chatRoleLabel(m.chat_role)}
                      </div>
                    </div>
                  </button>
                  {button}
                </div>
              )}
            </ActionMenu>
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

      {canAddMembers && addMembersOpen ? (
        <ModalChrome title="Добавить участников" onClose={() => setAddMembersOpen(false)} narrow>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.9rem" }}>
              Выберите друзей, которых нужно добавить в чат.
            </p>
            <div style={{ maxHeight: "55vh", overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
              {friends.map((f) => {
                const already = members.some((m) => m.chat_user_id === f.id);
                return (
                  <div
                    key={f.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: 8,
                      borderRadius: 10,
                      border: "1px solid var(--border)",
                      background: "var(--bg-muted)",
                    }}
                  >
                    <Avatar
                      src={userAvatarUrl(f.id, assetEpoch)}
                      label={avatarLetterFromUser(f)}
                      size={36}
                    />
                    <div style={{ flex: 1, minWidth: 0, fontSize: "0.9rem" }}>
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
              {friends.length === 0 && fDone ? (
                <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                  Список друзей пуст.
                </div>
              ) : null}
              {!fDone ? (
                <button
                  type="button"
                  className="ui-btn ui-btn--ghost"
                  style={{ width: "100%" }}
                  onClick={() => void loadFriends(false)}
                >
                  Ещё друзья...
                </button>
              ) : null}
            </div>
          </div>
        </ModalChrome>
      ) : null}
    </div>
  );
}
