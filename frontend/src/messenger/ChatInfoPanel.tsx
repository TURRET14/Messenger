import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  apiFetch,
  apiJson,
  apiUpload,
  type UploadProgress,
} from "../api/client";
import { fetchUser, fetchUsers, peekUser, primeUser } from "../api/userCache";
import type { Chat, ChatRole, UserInList } from "../api/types";
import { Avatar, chatAvatarUrl, userAvatarUrl } from "../components/ui/Avatar";
import {
  ActionMenu,
  type ActionMenuItem,
} from "../components/ui/ActionMenu";
import { ModalChrome } from "../components/ui/ModalChrome";
import { ValidationError } from "../components/ui/ValidationError";
import {
  IconCamera,
  IconCheck,
  IconCrown,
  IconLogout,
  IconShieldCheck,
  IconTrash,
  IconUser,
  IconUserPlus,
  IconUserX,
  IconX,
} from "../components/Icons";
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

function roleIcon(role: ChatRole) {
  if (role === "OWNER") return <IconCrown size={12} />;
  if (role === "ADMIN") return <IconShieldCheck size={12} />;
  return <IconUser size={12} />;
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
  const [savingName, setSavingName] = useState(false);
  const [avatarUploadProgress, setAvatarUploadProgress] = useState<UploadProgress | null>(null);
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
        // Bulk-загрузка пользователей-участников одним запросом.
        const uids = batch.map((row) => row.chat_user_id);
        void fetchUsers(uids).then((map) => {
          if (map.size === 0) return;
          setUserMap((prev) => {
            const next = { ...prev };
            for (const [uid, u] of map) {
              if (!next[uid]) next[uid] = u;
            }
            return next;
          });
        });
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
        // Bulk-загрузка пользователей-участников одним запросом.
        const uids = batch.map((row) => row.chat_user_id);
        void fetchUsers(uids).then((map) => {
          if (map.size === 0) return;
          setUserMap((prev) => {
            const next = { ...prev };
            for (const [uid, u] of map) {
              if (!next[uid]) next[uid] = u;
            }
            return next;
          });
        });
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

  // Если внутри ОДНОГО и того же чата сменился владелец (например, через WebSocket
  // /chats/put после передачи владения другим пользователем), бэкенд не присылает
  // /memberships/put для затронутых участников — обновляем список вручную.
  const prevChatStateRef = useRef<{ id: number; ownerUserId: number | null }>({
    id: chat.id,
    ownerUserId: chat.owner_user_id,
  });
  useEffect(() => {
    const prev = prevChatStateRef.current;
    if (prev.id === chat.id && prev.ownerUserId !== chat.owner_user_id) {
      loadingRef.current = false;
      void refreshMembers();
    }
    prevChatStateRef.current = { id: chat.id, ownerUserId: chat.owner_user_id };
  }, [chat.id, chat.owner_user_id, refreshMembers]);

  const loadFriends = useCallback(
    async (reset: boolean) => {
      const mult = reset ? 0 : fOff + 1;
      try {
        const batch = await apiJson<(UserInList & { date_and_time_added?: string })[]>(
          `/users/me/friends?offset_multiplier=${reset ? 0 : mult}`,
        );
        // Кешируем для ensureName и других экранов.
        batch.forEach(primeUser);
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

  // При открытии модалки «Добавить участников» обновляем список друзей,
  // чтобы недавно принятые/отправленные дружбы сразу отображались.
  useEffect(() => {
    if (addMembersOpen && isGroupOrChannel) {
      setFriends([]);
      setFOff(0);
      setFDone(false);
      void loadFriends(true);
    }
  }, [addMembersOpen, isGroupOrChannel]);

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
        const peer =
          mem.find((m) => m.chat_user_id !== currentUserId)?.chat_user_id ??
          null;
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

  const canTransferOwnership = (target: MembershipRow) => {
    if (!isGroupOrChannel || !isOwner) return false;
    if (target.chat_user_id === currentUserId) return false;
    // Бэкенд требует, чтобы новый владелец уже состоял в чате (любая роль).
    return true;
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
    setSavingName(true);
    try {
      await apiFetch(`/chats/id/${chat.id}/name`, {
        method: "PATCH",
        body: JSON.stringify({ name: n }),
      });
      await onRefreshChats();
      void alert("Название обновлено");
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не сохранено");
    } finally {
      setSavingName(false);
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
    setAvatarUploadProgress({ loaded: 0, total: file.size });
    try {
      await apiUpload(`/chats/id/${chat.id}/avatar`, fd, {
        method: "PUT",
        onProgress: (p) => setAvatarUploadProgress(p),
      });
      await onRefreshChats();
      void alert("Фото чата обновлено");
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      void alert(e instanceof ApiError ? e.message : "Не загружено");
    } finally {
      setAvatarUploadProgress(null);
    }
  };

  const resetAvatar = async () => {
    if (
      !(await confirm({
        message: "Сбросить фото чата?",
        danger: true,
        confirmLabel: "Сбросить",
      }))
    ) {
      return;
    }
    setChatProfileError(null);
    try {
      await apiFetch(`/chats/id/${chat.id}/avatar`, { method: "DELETE" });
      await onRefreshChats();
    } catch (e) {
      const message =
        e instanceof ApiError ? e.message : "Не удалось сбросить фото";
      setChatProfileError(message);
      void alert(message, "Ошибка");
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
    if (
      !(await confirm({
        message: "Назначить пользователя администратором чата?",
        confirmLabel: "Назначить",
      }))
    ) {
      return;
    }
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
    if (
      !(await confirm({
        message: "Снять роль администратора у пользователя?",
        confirmLabel: "Снять",
      }))
    ) {
      return;
    }
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

  const transferOwnership = async (target: MembershipRow) => {
    const targetUser = userMap[target.chat_user_id];
    const targetLabel = targetUser
      ? userListLabel(targetUser)
      : `Пользователь #${target.chat_user_id}`;
    if (
      !(await confirm({
        message:
          `Передать владение чатом пользователю ${targetLabel}? ` +
          "Вы перестанете быть владельцем и станете обычным участником.",
        danger: true,
        confirmLabel: "Передать",
      }))
    ) {
      return;
    }
    try {
      await apiFetch(`/chats/id/${chat.id}/owner`, {
        method: "PATCH",
        body: JSON.stringify({ id: target.chat_user_id }),
      });
      // Оптимистично обновляем роли в локальном списке: новый владелец → OWNER,
      // старый (текущий пользователь) → USER. refreshMembers() ниже подтвердит
      // изменение, но UI обновится мгновенно даже если refresh будет отложен.
      setMembers((prev) =>
        prev.map((m) => {
          if (m.chat_user_id === target.chat_user_id) {
            return { ...m, chat_role: "OWNER" };
          }
          if (m.chat_user_id === currentUserId) {
            return { ...m, chat_role: "USER" };
          }
          return m;
        }),
      );
      await onRefreshChats();
      // Снимаем lock от прошлых загрузок и запрашиваем актуальные данные.
      loadingRef.current = false;
      await refreshMembers();
      void alert("Владелец чата изменён");
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалось передать владение");
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

  // Для PRIVATE/PROFILE буква-заглушка должна совпадать с username
  // собеседника/владельца, а не с первой буквой ФИО из chat.name.
  const headerUserId =
    chat.chat_kind === "PROFILE"
      ? chat.owner_user_id
      : chat.chat_kind === "PRIVATE"
        ? privatePeerId
        : null;
  const [headerUserLetter, setHeaderUserLetter] = useState<string | undefined>(
    () => {
      if (headerUserId == null) return undefined;
      const cached = peekUser(headerUserId);
      return cached?.username.trim()[0];
    },
  );
  useEffect(() => {
    if (headerUserId == null) {
      setHeaderUserLetter(undefined);
      return;
    }
    const cached = peekUser(headerUserId);
    if (cached) {
      setHeaderUserLetter(cached.username.trim()[0]);
      return;
    }
    let cancelled = false;
    void fetchUser(headerUserId).then((u) => {
      if (!cancelled && u) setHeaderUserLetter(u.username.trim()[0]);
    });
    return () => {
      cancelled = true;
    };
  }, [headerUserId]);

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
          width: 320,
          minWidth: 280,
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
        background: "var(--bg-elevated)",
      }}
    >
      {/* Единая прокручиваемая область: hero, форма редактирования, кнопка
          добавления и список участников. Так на маленьких экранах, когда
          верхняя часть занимает много места, можно проскроллить всё целиком —
          вместо застревания в крошечной зоне списка участников. */}
      <div
        ref={listRef}
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
        }}
        onScroll={(e) => {
          const el = e.currentTarget;
          if (
            el.scrollTop + el.clientHeight >= el.scrollHeight - 24 &&
            !done &&
            !loading
          ) {
            void loadMembers(false);
          }
        }}
      >
      <div
        style={{
          padding: "16px 14px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div style={{ position: "relative" }}>
            <Avatar
              src={chatAvatarSrc}
              label={chatTitle}
              letter={headerUserLetter}
              size={88}
            />
            {canEditChatProfile ? (
              <label
                title={
                  avatarUploadProgress
                    ? "Идёт загрузка…"
                    : "Сменить фото чата"
                }
                aria-label={
                  avatarUploadProgress
                    ? "Идёт загрузка фото"
                    : "Сменить фото чата"
                }
                style={{
                  position: "absolute",
                  bottom: -2,
                  right: -2,
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: "var(--accent)",
                  color: "var(--on-accent)",
                  display: "grid",
                  placeItems: "center",
                  cursor: avatarUploadProgress ? "wait" : "pointer",
                  border: "2px solid var(--bg-elevated)",
                  transition: "background-color 120ms ease, transform 80ms ease",
                  pointerEvents: avatarUploadProgress ? "none" : "auto",
                  opacity: avatarUploadProgress ? 0.85 : 1,
                }}
                onMouseDown={(e) => {
                  (e.currentTarget as HTMLElement).style.transform = "scale(0.9)";
                }}
                onMouseUp={(e) => {
                  (e.currentTarget as HTMLElement).style.transform = "";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.transform = "";
                }}
              >
                {avatarUploadProgress ? (
                  <span className="ui-spinner" aria-hidden="true" />
                ) : (
                  <IconCamera size={16} />
                )}
                <input
                  type="file"
                  accept="image/*"
                  className="sr-only"
                  disabled={!!avatarUploadProgress}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    e.target.value = "";
                    if (f) void uploadAvatar(f);
                  }}
                />
              </label>
            ) : null}
            {canEditChatProfile && chat.has_avatar && !avatarUploadProgress ? (
              <button
                type="button"
                onClick={() => void resetAvatar()}
                title="Сбросить фото"
                aria-label="Сбросить фото"
                style={{
                  position: "absolute",
                  bottom: -2,
                  left: -2,
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: "var(--danger)",
                  color: "var(--on-danger)",
                  display: "grid",
                  placeItems: "center",
                  cursor: "pointer",
                  border: "2px solid var(--bg-elevated)",
                  padding: 0,
                }}
              >
                <IconTrash size={16} />
              </button>
            ) : null}
          </div>
          <div
            style={{
              textAlign: "center",
              fontWeight: 700,
              wordBreak: "break-word",
              fontSize: "1.05rem",
            }}
          >
            {chatTitle}
          </div>
          <div
            className="ui-chip"
            style={{ background: "var(--bg-muted)" }}
          >
            {chatKindLabel(chat.chat_kind)}
          </div>
        </div>
      </div>

      {canEditChatProfile ? (
        <div
          className="ui-card"
          style={{
            margin: 12,
            padding: 12,
            background: "var(--bg-subtle)",
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          <div
            style={{
              fontSize: "0.85rem",
              color: "var(--text-muted)",
              fontWeight: 600,
              marginBottom: 2,
            }}
          >
            Редактирование
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
            <input
              className="ui-input"
              value={nameEdit}
              onChange={(e) => {
                setNameEdit(e.target.value);
                setChatProfileError(null);
              }}
              maxLength={100}
              placeholder="Название чата"
              style={{ flex: 1, minWidth: 0 }}
            />
            <button
              type="button"
              className="ui-btn ui-btn--primary"
              disabled={savingName || nameEdit.trim() === chat.name}
              onClick={() => void saveName()}
              title="Сохранить название"
              aria-label="Сохранить название"
              style={{ flexShrink: 0, padding: "0 14px" }}
            >
              {savingName ? (
                <span className="ui-spinner" aria-hidden="true" />
              ) : (
                <IconCheck size={18} />
              )}
            </button>
          </div>
          <ValidationError message={chatProfileError} />
          {avatarUploadProgress ? (
            <ChatAvatarUploadProgress progress={avatarUploadProgress} />
          ) : null}
          <p
            style={{
              margin: 0,
              fontSize: "0.78rem",
              color: "var(--text-subtle)",
            }}
          >
            Чтобы сменить фото, нажмите на иконку камеры на аватаре.
          </p>
        </div>
      ) : null}

      {canAddMembers ? (
        <div
          style={{
            padding: 12,
            borderBottom: "1px solid var(--border)",
          }}
        >
          <button
            type="button"
            className="ui-btn ui-btn--soft ui-btn--block"
            onClick={() => setAddMembersOpen(true)}
          >
            <IconUserPlus size={16} />
            Добавить участников
          </button>
        </div>
      ) : null}

      <div style={{ padding: 12 }}>
        <div
          style={{
            fontWeight: 600,
            marginBottom: 8,
            fontSize: "0.85rem",
            color: "var(--text-muted)",
          }}
        >
          Участники ({members.length})
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {members.map((m) => {
            const u = userMap[m.chat_user_id];
            const label = u
              ? userListLabel(u)
              : `Пользователь #${m.chat_user_id}`;
            const memberActions: ActionMenuItem[] = [
              {
                label: "Открыть профиль",
                onSelect: () => onOpenProfile(m.chat_user_id),
                icon: <IconUser size={16} />,
              },
              ...(canPromoteToAdmin(m)
                ? [
                    {
                      label: "Назначить администратором",
                      onSelect: () => void makeAdmin(m.chat_user_id),
                      icon: <IconShieldCheck size={16} />,
                    },
                  ]
                : []),
              ...(canDemoteAdmin(m)
                ? [
                    {
                      label: "Снять администратора",
                      onSelect: () => void dropAdmin(m.chat_user_id),
                      icon: <IconShieldCheck size={16} />,
                    },
                  ]
                : []),
              ...(canTransferOwnership(m)
                ? [
                    {
                      label: "Передать владение",
                      onSelect: () => void transferOwnership(m),
                      icon: <IconCrown size={16} />,
                      danger: true,
                    },
                  ]
                : []),
              ...(canRemoveMember(m)
                ? [
                    {
                      label: "Удалить из чата",
                      onSelect: () => void removeMember(m),
                      icon: <IconUserX size={16} />,
                      danger: true,
                    },
                  ]
                : []),
            ];
            const isCurrentUser = m.chat_user_id === currentUserId;
            return (
              <ActionMenu
                key={m.id}
                items={memberActions}
                label="Действия с участником"
              >
                {({ button, onContextMenu }) => (
                  <div
                    onContextMenu={onContextMenu}
                    className={
                      isCurrentUser ? "ui-row ui-row--selected" : "ui-row"
                    }
                    style={{ padding: 8, gap: 10 }}
                  >
                    <button
                      type="button"
                      onClick={() => onOpenProfile(m.chat_user_id)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
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
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div
                          style={{
                            fontSize: "0.9rem",
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            minWidth: 0,
                          }}
                        >
                          <span
                            style={{
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                              minWidth: 0,
                            }}
                          >
                            {label}
                          </span>
                          {isCurrentUser ? (
                            <span
                              className="ui-chip ui-chip--accent"
                              style={{
                                padding: "1px 8px",
                                fontSize: "0.7rem",
                                fontWeight: 700,
                                flexShrink: 0,
                              }}
                            >
                              Вы
                            </span>
                          ) : null}
                        </div>
                        <div
                          style={{
                            fontSize: "0.75rem",
                            color: "var(--text-muted)",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                          }}
                        >
                          {roleIcon(m.chat_role)}
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
          {loading && members.length === 0 ? (
            <div className="ui-loader-center">
              <span className="ui-spinner ui-spinner--xl" aria-hidden="true" />
            </div>
          ) : null}
        </div>
      </div>
      </div>{/* /scroll-контейнер */}

      <div
        style={{
          padding: 12,
          borderTop: "1px solid var(--border)",
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {!isOwner && (isPrivate || isGroupOrChannel || isProfile) ? (
          <button
            type="button"
            className="ui-btn ui-btn--danger ui-btn--block"
            onClick={() => void handleLeave()}
          >
            <IconLogout size={16} />
            Покинуть чат
          </button>
        ) : null}
        {isGroupOrChannel && isOwner ? (
          <button
            type="button"
            className="ui-btn ui-btn--danger ui-btn--block"
            onClick={() => void handleDeleteChat()}
          >
            <IconTrash size={16} />
            Удалить чат
          </button>
        ) : null}
      </div>

      {canAddMembers && addMembersOpen ? (
        <ModalChrome
          title="Добавить участников"
          onClose={() => setAddMembersOpen(false)}
          narrow
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.9rem" }}>
              Выберите друзей, которых нужно добавить в чат.
            </p>
            <div
              style={{
                maxHeight: "55vh",
                overflowY: "auto",
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              {friends.map((f) => {
                const already = members.some((m) => m.chat_user_id === f.id);
                return (
                  <div
                    key={f.id}
                    className="ui-row"
                    style={{ gap: 10, padding: 8 }}
                  >
                    <Avatar
                      src={userAvatarUrl(f.id, assetEpoch)}
                      label={avatarLetterFromUser(f)}
                      size={36}
                    />
                    <div
                      style={{
                        flex: 1,
                        minWidth: 0,
                        fontSize: "0.9rem",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {userListLabel(f)}
                    </div>
                    <button
                      type="button"
                      className={
                        already
                          ? "ui-btn ui-btn--ghost ui-btn--sm"
                          : "ui-btn ui-btn--soft ui-btn--sm"
                      }
                      disabled={already}
                      onClick={() => void addMember(f.id)}
                    >
                      {already ? (
                        <>
                          <IconCheck size={14} />
                          В чате
                        </>
                      ) : (
                        <>
                          <IconUserPlus size={14} />
                          Добавить
                        </>
                      )}
                    </button>
                  </div>
                );
              })}
              {friends.length === 0 && fDone ? (
                <div
                  style={{
                    padding: "16px 8px",
                    color: "var(--text-muted)",
                    fontSize: "0.9rem",
                    textAlign: "center",
                  }}
                >
                  Список друзей пуст.
                </div>
              ) : null}
              {!fDone ? (
                <button
                  type="button"
                  className="ui-btn ui-btn--ghost ui-btn--block"
                  onClick={() => void loadFriends(false)}
                >
                  Ещё друзья…
                </button>
              ) : null}
            </div>
            <div className="ui-modal-actions">
              <button
                type="button"
                className="ui-btn"
                onClick={() => setAddMembersOpen(false)}
              >
                <IconX size={16} />
                Закрыть
              </button>
            </div>
          </div>
        </ModalChrome>
      ) : null}
    </div>
  );
}

/**
 * Прогресс-бар загрузки аватара чата с процентом и абсолютными байтами.
 */
function ChatAvatarUploadProgress({ progress }: { progress: UploadProgress }) {
  const percent =
    progress.total > 0
      ? Math.min(100, Math.round((progress.loaded / progress.total) * 100))
      : 0;
  const isUnknownTotal = progress.total === 0;
  const isFinalizing = !isUnknownTotal && progress.loaded >= progress.total;
  const fmt = (b: number) => {
    if (b < 1024) return `${b} Б`;
    const kb = b / 1024;
    if (kb < 1024) return `${kb.toFixed(0)} КБ`;
    const mb = kb / 1024;
    return `${mb.toFixed(mb < 10 ? 1 : 0)} МБ`;
  };
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        padding: "8px 10px",
        background: "var(--bg-elevated)",
        border: "1.5px solid var(--border)",
        borderRadius: 10,
      }}
      aria-live="polite"
    >
      <div
        style={{
          fontSize: "0.85rem",
          color: "var(--text-muted)",
        }}
      >
        {isFinalizing
          ? "Обработка фото на сервере…"
          : isUnknownTotal
            ? "Загрузка фото…"
            : `Загрузка фото: ${percent}% · ${fmt(progress.loaded)} / ${fmt(progress.total)}`}
      </div>
      <div
        style={{
          width: "100%",
          height: 6,
          background: "var(--bg-subtle)",
          borderRadius: 999,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: isUnknownTotal ? "30%" : `${percent}%`,
            height: "100%",
            background: "var(--accent)",
            borderRadius: 999,
            transition: "width 120ms linear",
          }}
        />
      </div>
    </div>
  );
}
