import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { ApiError, apiFetch, apiJson } from "../api/client";
import { fetchUsers, primeUser } from "../api/userCache";
import type {
  Chat,
  CurrentUser,
  FriendRequest,
  FriendUser,
  UserBlockRow,
  UserInList,
} from "../api/types";
import {
  IconArrowUp,
  IconAtSign,
  IconBan,
  IconCamera,
  IconChat,
  IconCheck,
  IconChevronRight,
  IconInbox,
  IconKey,
  IconMail,
  IconSearch,
  IconShield,
  IconTrash,
  IconUser,
  IconUserCheck,
  IconUserPlus,
  IconUsers,
  IconUserX,
  IconX,
} from "../components/Icons";
import { Avatar, userAvatarUrl } from "../components/ui/Avatar";
import { ModalChrome } from "../components/ui/ModalChrome";
import { ValidationError } from "../components/ui/ValidationError";
import { useDialogs } from "../context/DialogsContext";
import {
  validateCode,
  validateEmailAddress,
  validateImageFile,
  validateLogin,
  validateNamesSearch,
  validatePassword,
  validateProfileForm,
  validateUsernameSearch,
} from "../validation";
import { avatarLetterFromUser, userListLabel } from "./userFormat";
import { formatDateTime } from "../dateFormat";

const PAGE = 50;

type Section =
  | "profile"
  | "security"
  | "users"
  | "friends"
  | "in"
  | "out"
  | "blocks";

const NAV_ITEMS: { id: Section; label: string; icon: ReactNode }[] = [
  { id: "profile", label: "Профиль", icon: <IconUser size={18} /> },
  { id: "security", label: "Безопасность", icon: <IconShield size={18} /> },
  { id: "users", label: "Пользователи", icon: <IconUsers size={18} /> },
  { id: "friends", label: "Друзья", icon: <IconUserCheck size={18} /> },
  { id: "in", label: "Заявки", icon: <IconInbox size={18} /> },
  { id: "out", label: "Исходящие", icon: <IconArrowUp size={18} /> },
  { id: "blocks", label: "Блокировки", icon: <IconBan size={18} /> },
];

export function MainAppMenu({
  currentUser,
  onClose,
  onOpenProfile,
  onRefreshUser,
  onMediaInvalidate,
  onUserDeleted,
  assetEpoch = 0,
  onOpenChat,
}: {
  currentUser: CurrentUser;
  onClose: () => void;
  onOpenProfile: (userId: number) => void;
  onRefreshUser: () => Promise<void>;
  onMediaInvalidate?: () => void;
  onUserDeleted?: () => void;
  assetEpoch?: number;
  onOpenChat?: (chatId: number, options?: { ephemeral?: boolean }) => void;
}) {
  const { alert, confirm } = useDialogs();
  const [section, setSection] = useState<Section>("profile");
  const [wide, setWide] = useState(true);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 760px)");
    const fn = () => setWide(mq.matches);
    setWide(mq.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);

  /* ============= state: profile ============= */

  const [u, setU] = useState<CurrentUser>(currentUser);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSaving, setProfileSaving] = useState(false);

  useEffect(() => {
    setU(currentUser);
  }, [currentUser]);

  /* ============= state: security ============= */

  const [currentLogin, setCurrentLogin] = useState("");
  const [loginDialogOpen, setLoginDialogOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await apiJson<{ login: string }>("/users/me/login");
        if (!cancelled) setCurrentLogin(data.login);
      } catch {
        if (!cancelled) setCurrentLogin("");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [currentUser.id]);

  /* ============= state: users / friends ============= */

  const [users, setUsers] = useState<UserInList[]>([]);
  const [uDone, setUDone] = useState(false);
  const [uSearch, setUSearch] = useState({
    mode: "all" as "all" | "username" | "names",
    q: "",
    n: "",
    s: "",
    o: "",
  });
  const [usersSearchError, setUsersSearchError] = useState<string | null>(null);

  const [friends, setFriends] = useState<FriendUser[]>([]);
  const [fDone, setFDone] = useState(false);
  const [fSearch, setFSearch] = useState({
    mode: "all" as "all" | "username" | "names",
    q: "",
    n: "",
    s: "",
    o: "",
  });
  const [friendsSearchError, setFriendsSearchError] = useState<string | null>(null);

  const [incoming, setIncoming] = useState<FriendRequest[]>([]);
  const [iDone, setIDone] = useState(false);
  const iPageRef = useRef(0);

  const [outgoing, setOutgoing] = useState<FriendRequest[]>([]);
  const [oDone, setODone] = useState(false);
  const oPageRef = useRef(0);

  const [blocks, setBlocks] = useState<UserBlockRow[]>([]);
  const [bDone, setBDone] = useState(false);
  const bPageRef = useRef(0);
  const [blockUsers, setBlockUsers] = useState<Record<number, UserInList>>({});
  const [incomingUsers, setIncomingUsers] = useState<Record<number, UserInList>>({});
  const [outgoingUsers, setOutgoingUsers] = useState<Record<number, UserInList>>({});

  const loadingRef = useRef(false);
  const uPageRef = useRef(0);
  const fPageRef = useRef(0);

  /* ============= profile actions ============= */

  const saveProfile = async () => {
    const profilePayload = {
      ...u,
      username: (u.username ?? "").trim(),
      name: (u.name ?? "").trim(),
      surname: u.surname?.trim() || null,
      second_name: u.second_name?.trim() || null,
      email_address: (u.email_address ?? "").trim(),
      phone_number: u.phone_number?.trim() || null,
      about: u.about || null,
    };

    const validationError = validateProfileForm(profilePayload);
    if (validationError) {
      setProfileError(validationError);
      void alert(validationError, "Ошибка валидации");
      return;
    }

    setProfileError(null);
    setProfileSaving(true);
    try {
      await apiFetch("/users/me", {
        method: "PATCH",
        body: JSON.stringify({
          username: profilePayload.username,
          name: profilePayload.name,
          surname: profilePayload.surname,
          second_name: profilePayload.second_name,
          date_of_birth: profilePayload.date_of_birth || null,
          gender: profilePayload.gender,
          email_address: profilePayload.email_address,
          phone_number: profilePayload.phone_number,
          about: profilePayload.about,
        }),
      });
      await onRefreshUser();
      void alert("Профиль сохранён");
    } catch (e) {
      const message =
        e instanceof ApiError ? e.message : "Не удалось сохранить профиль";
      setProfileError(message);
      void alert(message, "Ошибка сохранения");
    } finally {
      setProfileSaving(false);
    }
  };

  const uploadAvatar = async (file: File) => {
    const validationError = validateImageFile(file, "Фото профиля");
    if (validationError) {
      setProfileError(validationError);
      void alert(validationError, "Ошибка валидации");
      return;
    }

    setProfileError(null);
    const fd = new FormData();
    fd.append("file", file);
    try {
      await apiFetch("/users/me/avatar", { method: "PUT", body: fd });
      await onRefreshUser();
      onMediaInvalidate?.();
      void alert("Фото обновлено");
    } catch (e) {
      const message =
        e instanceof ApiError ? e.message : "Не удалось загрузить фото";
      setProfileError(message);
      void alert(message, "Ошибка загрузки");
    }
  };

  const deleteCurrentUser = async () => {
    if (
      !(await confirm({
        message: "Удалить текущего пользователя? Это действие необратимо.",
        danger: true,
        confirmLabel: "Удалить пользователя",
      }))
    ) {
      return;
    }
    try {
      await apiFetch("/users/me", { method: "DELETE" });
      onUserDeleted?.();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалось удалить пользователя");
    }
  };

  /* ============= users / friends list loaders ============= */

  const loadUsers = useCallback(
    async (reset: boolean, overrideSearch?: typeof uSearch) => {
      if (loadingRef.current && !reset) return;
      const search = overrideSearch ?? uSearch;
      const searchError =
        search.mode === "username"
          ? validateUsernameSearch(search.q)
          : search.mode === "names"
            ? validateNamesSearch({
                name: search.n,
                surname: search.s,
                secondName: search.o,
              })
            : null;
      if (reset && searchError) {
        setUsersSearchError(searchError);
        return;
      }
      setUsersSearchError(null);
      loadingRef.current = true;
      try {
        const mult = reset ? 0 : uPageRef.current + 1;
        let batch: UserInList[] = [];
        if (search.mode === "all") {
          batch = await apiJson<UserInList[]>(
            `/users?offset_multiplier=${mult}`,
          );
        } else if (search.mode === "username") {
          const q = search.q.trim();
          batch = await apiJson<UserInList[]>(
            `/users/search/by-username?username=${encodeURIComponent(q)}&offset_multiplier=${mult}`,
          );
        } else {
          const n = search.n.trim();
          const s = search.s.trim();
          const o = search.o.trim();
          const p = new URLSearchParams();
          p.set("offset_multiplier", String(mult));
          if (n) p.set("name", n);
          if (s) p.set("surname", s);
          if (o) p.set("second_name", o);
          batch = await apiJson<UserInList[]>(
            `/users/search/by-names?${p.toString()}`,
          );
        }
        // Кешируем найденных пользователей для других экранов (профиль и т.п.).
        batch.forEach(primeUser);
        if (reset) {
          uPageRef.current = 0;
          setUsers(batch);
          setUDone(batch.length < PAGE);
        } else {
          uPageRef.current = mult;
          setUsers((prev) => {
            const ids = new Set(prev.map((x) => x.id));
            return [...prev, ...batch.filter((x) => !ids.has(x.id))];
          });
          if (batch.length < PAGE) setUDone(true);
        }
      } catch (e) {
        void alert(e instanceof ApiError ? e.message : "Список не загружен");
      } finally {
        loadingRef.current = false;
      }
    },
    [uSearch, alert],
  );

  const loadFriends = useCallback(
    async (reset: boolean, overrideSearch?: typeof fSearch) => {
      if (loadingRef.current && !reset) return;
      const search = overrideSearch ?? fSearch;
      const searchError =
        search.mode === "username"
          ? validateUsernameSearch(search.q)
          : search.mode === "names"
            ? validateNamesSearch({
                name: search.n,
                surname: search.s,
                secondName: search.o,
              })
            : null;
      if (reset && searchError) {
        setFriendsSearchError(searchError);
        return;
      }
      setFriendsSearchError(null);
      loadingRef.current = true;
      try {
        const mult = reset ? 0 : fPageRef.current + 1;
        let batch: FriendUser[] = [];
        if (search.mode === "all") {
          batch = await apiJson<FriendUser[]>(
            `/users/me/friends?offset_multiplier=${mult}`,
          );
        } else if (search.mode === "username") {
          const q = search.q.trim();
          batch = await apiJson<FriendUser[]>(
            `/users/me/friends/search/by-username?username=${encodeURIComponent(q)}&offset_multiplier=${mult}`,
          );
        } else {
          const n = search.n.trim();
          const s = search.s.trim();
          const o = search.o.trim();
          const p = new URLSearchParams();
          p.set("offset_multiplier", String(mult));
          if (n) p.set("name", n);
          if (s) p.set("surname", s);
          if (o) p.set("second_name", o);
          batch = await apiJson<FriendUser[]>(
            `/users/me/friends/search/by-names?${p.toString()}`,
          );
        }
        // Кешируем найденных друзей для других экранов.
        batch.forEach(primeUser);
        if (reset) {
          fPageRef.current = 0;
          setFriends(batch);
          setFDone(batch.length < PAGE);
        } else {
          fPageRef.current = mult;
          setFriends((prev) => {
            const ids = new Set(prev.map((x) => x.id));
            return [...prev, ...batch.filter((x) => !ids.has(x.id))];
          });
          if (batch.length < PAGE) setFDone(true);
        }
      } catch (e) {
        void alert(e instanceof ApiError ? e.message : "Друзья не загружены");
      } finally {
        loadingRef.current = false;
      }
    },
    [fSearch, alert],
  );

  const loadIncoming = async (reset: boolean) => {
    const mult = reset ? 0 : iPageRef.current + 1;
    try {
      const batch = await apiJson<FriendRequest[]>(
        `/users/me/friends/requests/received?offset_multiplier=${mult}`,
      );
      if (reset) {
        iPageRef.current = 0;
        setIncoming(batch);
        setIncomingUsers({});
        setIDone(batch.length < PAGE);
      } else {
        iPageRef.current = mult;
        setIncoming((prev) => {
          const ids = new Set(prev.map((x) => x.id));
          return [...prev, ...batch.filter((x) => !ids.has(x.id))];
        });
        if (batch.length < PAGE) setIDone(true);
      }
      // Bulk-загрузка отправителей одним POST /users/by-ids вместо N запросов.
      const senderIds = batch.map((r) => r.sender_user_id);
      void fetchUsers(senderIds).then((map) => {
        if (map.size === 0) return;
        setIncomingUsers((prev) => {
          const next = { ...prev };
          for (const [uid, usr] of map) {
            if (!next[uid]) next[uid] = usr;
          }
          return next;
        });
      });
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const loadOutgoing = async (reset: boolean) => {
    const mult = reset ? 0 : oPageRef.current + 1;
    try {
      const batch = await apiJson<FriendRequest[]>(
        `/users/me/friends/requests/sent?offset_multiplier=${mult}`,
      );
      if (reset) {
        oPageRef.current = 0;
        setOutgoing(batch);
        setOutgoingUsers({});
        setODone(batch.length < PAGE);
      } else {
        oPageRef.current = mult;
        setOutgoing((prev) => {
          const ids = new Set(prev.map((x) => x.id));
          return [...prev, ...batch.filter((x) => !ids.has(x.id))];
        });
        if (batch.length < PAGE) setODone(true);
      }
      // Bulk-загрузка получателей одним запросом.
      const receiverIds = batch.map((r) => r.receiver_user_id);
      void fetchUsers(receiverIds).then((map) => {
        if (map.size === 0) return;
        setOutgoingUsers((prev) => {
          const next = { ...prev };
          for (const [uid, usr] of map) {
            if (!next[uid]) next[uid] = usr;
          }
          return next;
        });
      });
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const loadBlocks = async (reset: boolean) => {
    const mult = reset ? 0 : bPageRef.current + 1;
    try {
      const batch = await apiJson<UserBlockRow[]>(
        `/users/me/blocks?offset_multiplier=${mult}`,
      );
      if (reset) {
        bPageRef.current = 0;
        setBlocks(batch);
        setBDone(batch.length < PAGE);
      } else {
        bPageRef.current = mult;
        setBlocks((prev) => {
          const ids = new Set(prev.map((x) => x.id));
          return [...prev, ...batch.filter((x) => !ids.has(x.id))];
        });
        if (batch.length < PAGE) setBDone(true);
      }
      // Bulk-загрузка заблокированных одним запросом.
      const needIds = batch
        .map((b) => b.blocked_user_id)
        .filter((uid) => !blockUsers[uid]);
      void fetchUsers(needIds).then((map) => {
        if (map.size === 0) return;
        setBlockUsers((prev) => {
          const next = { ...prev };
          for (const [uid, usr] of map) {
            if (!next[uid]) next[uid] = usr;
          }
          return next;
        });
      });
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  /* ============= section auto-load ============= */

  useEffect(() => {
    if (section !== "users") return;
    const resetSearch = { mode: "all" as const, q: "", n: "", s: "", o: "" };
    setUSearch(resetSearch);
    setUsers([]);
    setUDone(false);
    uPageRef.current = 0;
    void loadUsers(true, resetSearch);
  }, [section]);

  useEffect(() => {
    if (section !== "friends") return;
    const resetSearch = { mode: "all" as const, q: "", n: "", s: "", o: "" };
    setFSearch(resetSearch);
    setFriends([]);
    setFDone(false);
    fPageRef.current = 0;
    void loadFriends(true, resetSearch);
  }, [section]);

  useEffect(() => {
    if (section === "in") void loadIncoming(true);
  }, [section]);

  useEffect(() => {
    if (section === "out") void loadOutgoing(true);
  }, [section]);

  useEffect(() => {
    if (section === "blocks") void loadBlocks(true);
  }, [section]);

  /* ============= friend / block actions ============= */

  const acceptReq = async (id: number) => {
    try {
      await apiFetch(`/users/me/friends/requests/received/id/${id}`, {
        method: "PUT",
      });
      void loadIncoming(true);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const declineReq = async (id: number) => {
    if (
      !(await confirm({
        message: "Отклонить заявку в друзья?",
        confirmLabel: "Отклонить",
      }))
    ) {
      return;
    }
    try {
      await apiFetch(`/users/me/friends/requests/received/id/${id}`, {
        method: "DELETE",
      });
      // Оптимистично убираем из списка, не дёргая lazy-load заново.
      setIncoming((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const cancelSent = async (id: number) => {
    if (
      !(await confirm({
        message: "Отозвать отправленную заявку в друзья?",
        confirmLabel: "Отозвать",
      }))
    ) {
      return;
    }
    try {
      await apiFetch(`/users/me/friends/requests/sent/id/${id}`, {
        method: "DELETE",
      });
      setOutgoing((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const removeFriend = async (fid: number) => {
    if (
      !(await confirm({
        message: "Удалить пользователя из друзей?",
        danger: true,
        confirmLabel: "Удалить",
      }))
    ) {
      return;
    }
    try {
      await apiFetch(`/users/me/friends/${fid}`, { method: "DELETE" });
      // Оптимистично удаляем из локального списка, чтобы не передёргивать
      // активный поиск (он мог требовать заполнения полей).
      setFriends((prev) => prev.filter((f) => f.friendship_id !== fid));
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const unblock = async (blockId: number) => {
    if (
      !(await confirm({
        message: "Разблокировать пользователя?",
        confirmLabel: "Разблокировать",
      }))
    ) {
      return;
    }
    try {
      await apiFetch(`/users/me/blocks/id/${blockId}`, { method: "DELETE" });
      // Оптимистично убираем блокировку из локального списка.
      setBlocks((prev) => prev.filter((b) => b.id !== blockId));
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  /* ============= UI ============= */

  const navStyles: CSSProperties = wide
    ? {
        width: 230,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        gap: 4,
        paddingRight: 12,
        borderRight: "1.5px solid var(--border)",
      }
    : {
        display: "flex",
        gap: 6,
        overflowX: "auto",
        paddingBottom: 10,
        marginBottom: 8,
        borderBottom: "1.5px solid var(--border)",
      };

  const renderNav = () => (
    <nav style={navStyles} aria-label="Разделы меню">
      {NAV_ITEMS.map((item) => {
        const active = section === item.id;
        const baseStyle: CSSProperties = wide
          ? {
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 12px",
              borderRadius: 10,
              border: "none",
              background: active ? "var(--accent-soft)" : "transparent",
              color: active ? "var(--accent)" : "var(--text)",
              fontWeight: active ? 700 : 500,
              cursor: "pointer",
              textAlign: "left",
              transition: "background-color 120ms ease, color 120ms ease",
            }
          : {
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 14px",
              borderRadius: 999,
              border: active
                ? "1.5px solid var(--accent)"
                : "1.5px solid var(--border)",
              background: active ? "var(--accent-soft)" : "var(--bg-subtle)",
              color: active ? "var(--accent)" : "var(--text)",
              fontWeight: active ? 700 : 500,
              cursor: "pointer",
              flexShrink: 0,
              fontSize: "0.85rem",
              whiteSpace: "nowrap",
            };
        return (
          <button
            key={item.id}
            type="button"
            style={baseStyle}
            onClick={() => setSection(item.id)}
            aria-current={active ? "page" : undefined}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );

  return (
    <>
      <ModalChrome title="Меню" onClose={onClose}>
        <div
          style={
            wide
              ? {
                  display: "flex",
                  gap: 18,
                  alignItems: "stretch",
                  minHeight: 480,
                }
              : { display: "flex", flexDirection: "column" }
          }
        >
          {renderNav()}
          <div
            style={{ flex: 1, minWidth: 0, paddingLeft: wide ? 6 : 0 }}
            key={section}
            className="anim-fade-in"
          >
            {section === "profile" ? (
              <ProfileSection
                u={u}
                setU={setU}
                error={profileError}
                setError={setProfileError}
                saving={profileSaving}
                onSave={() => void saveProfile()}
                onUploadAvatar={(file) => void uploadAvatar(file)}
                onDelete={() => void deleteCurrentUser()}
                onOpenSelfChat={
                  onOpenChat
                    ? () =>
                        void (async () => {
                          try {
                            const chat = await apiJson<Chat>(
                              `/users/id/${u.id}/profile`,
                            );
                            onOpenChat(chat.id, { ephemeral: true });
                            onClose();
                          } catch (e) {
                            void alert(
                              e instanceof ApiError
                                ? e.message
                                : "Не удалось открыть",
                            );
                          }
                        })()
                    : undefined
                }
                assetEpoch={assetEpoch}
              />
            ) : null}
            {section === "security" ? (
              <SecuritySection
                currentLogin={currentLogin}
                emailAddress={u.email_address}
                onChangeLogin={() => setLoginDialogOpen(true)}
                onChangePassword={() => setPasswordDialogOpen(true)}
                onChangeEmail={() => setEmailDialogOpen(true)}
              />
            ) : null}
            {section === "users" ? (
              <UsersListSection
                items={users}
                done={uDone}
                search={uSearch}
                setSearch={setUSearch}
                searchError={usersSearchError}
                onClearSearchError={() => setUsersSearchError(null)}
                onSearch={() => void loadUsers(true)}
                onMore={() => void loadUsers(false)}
                onOpenProfile={onOpenProfile}
                assetEpoch={assetEpoch}
              />
            ) : null}
            {section === "friends" ? (
              <FriendsListSection
                items={friends}
                done={fDone}
                search={fSearch}
                setSearch={setFSearch}
                searchError={friendsSearchError}
                onClearSearchError={() => setFriendsSearchError(null)}
                onSearch={() => void loadFriends(true)}
                onMore={() => void loadFriends(false)}
                onOpenProfile={onOpenProfile}
                onRemoveFriend={(id) => void removeFriend(id)}
                assetEpoch={assetEpoch}
              />
            ) : null}
            {section === "in" ? (
              <IncomingSection
                items={incoming}
                done={iDone}
                onMore={() => void loadIncoming(false)}
                onAccept={(id) => void acceptReq(id)}
                onDecline={(id) => void declineReq(id)}
                onOpenProfile={onOpenProfile}
                userMap={incomingUsers}
                assetEpoch={assetEpoch}
              />
            ) : null}
            {section === "out" ? (
              <OutgoingSection
                items={outgoing}
                done={oDone}
                onMore={() => void loadOutgoing(false)}
                onCancel={(id) => void cancelSent(id)}
                onOpenProfile={onOpenProfile}
                userMap={outgoingUsers}
                assetEpoch={assetEpoch}
              />
            ) : null}
            {section === "blocks" ? (
              <BlocksSection
                items={blocks}
                done={bDone}
                onMore={() => void loadBlocks(false)}
                onUnblock={(id) => void unblock(id)}
                onOpenProfile={onOpenProfile}
                userMap={blockUsers}
                assetEpoch={assetEpoch}
              />
            ) : null}
          </div>
        </div>
      </ModalChrome>

      {loginDialogOpen ? (
        <ChangeLoginDialog
          currentLogin={currentLogin}
          onClose={() => setLoginDialogOpen(false)}
          onSuccess={(newLogin) => {
            setCurrentLogin(newLogin);
            setLoginDialogOpen(false);
          }}
        />
      ) : null}

      {passwordDialogOpen ? (
        <ChangePasswordDialog
          userId={u.id}
          onClose={() => setPasswordDialogOpen(false)}
        />
      ) : null}

      {emailDialogOpen ? (
        <ChangeEmailDialog
          userId={u.id}
          currentEmail={u.email_address}
          onClose={() => setEmailDialogOpen(false)}
          onSuccess={async () => {
            await onRefreshUser();
            setEmailDialogOpen(false);
          }}
        />
      ) : null}
    </>
  );
}

/* =============================================================
   Profile section
   ============================================================= */

function ProfileSection({
  u,
  setU,
  error,
  setError,
  saving,
  onSave,
  onUploadAvatar,
  onDelete,
  onOpenSelfChat,
  assetEpoch,
}: {
  u: CurrentUser;
  setU: (u: CurrentUser) => void;
  error: string | null;
  setError: (s: string | null) => void;
  saving: boolean;
  onSave: () => void;
  onUploadAvatar: (file: File) => void;
  onDelete: () => void;
  onOpenSelfChat?: () => void;
  assetEpoch: number;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          padding: "8px 4px",
        }}
      >
        {/* Аватар с camera-overlay — единый элемент управления фото,
            аналогично интерфейсу смены аватара чата в ChatInfoPanel. */}
        <div style={{ position: "relative", flexShrink: 0 }}>
          <Avatar
            src={userAvatarUrl(u.id, assetEpoch)}
            label={u.name || u.username}
            size={120}
          />
          <label
            title="Сменить фото"
            aria-label="Сменить фото"
            style={{
              position: "absolute",
              bottom: -2,
              right: -2,
              width: 38,
              height: 38,
              borderRadius: "50%",
              background: "var(--accent)",
              color: "var(--on-accent)",
              display: "grid",
              placeItems: "center",
              cursor: "pointer",
              border: "2.5px solid var(--bg-elevated)",
              transition: "background-color 120ms ease, transform 80ms ease",
            }}
            onMouseDown={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "scale(0.92)";
            }}
            onMouseUp={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "";
            }}
          >
            <IconCamera size={18} />
            <input
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = "";
                if (f) onUploadAvatar(f);
              }}
            />
          </label>
        </div>

        {/* Справа от аватара — единственное основное действие.
            Если открытие ленты не передано, блок справа просто отсутствует. */}
        {onOpenSelfChat ? (
          <div style={{ flex: 1, minWidth: 0 }}>
            <button
              type="button"
              className="profile-action-card"
              onClick={onOpenSelfChat}
              style={{ width: "100%" }}
            >
              <span className="icon-wrap">
                <IconChat size={18} />
              </span>
              Моя лента профиля
            </button>
          </div>
        ) : null}
      </div>

      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "1fr 1fr" }}>
        {(
          [
            ["username", "Имя пользователя"],
            ["name", "Имя"],
            ["surname", "Фамилия"],
            ["second_name", "Отчество"],
          ] as const
        ).map(([key, label]) => {
          const isReq = key === "username" || key === "name";
          return (
            <label key={key} className="ui-field" style={{ minWidth: 0 }}>
              <span className="ui-field-label">{label}</span>
              <input
                className="ui-input"
                value={(u[key] as string) ?? ""}
                onChange={(e) => {
                  setU({
                    ...u,
                    [key]: isReq ? e.target.value : e.target.value || null,
                  });
                  setError(null);
                }}
                maxLength={100}
              />
            </label>
          );
        })}
      </div>

      <label className="ui-field">
        <span className="ui-field-label">Телефон</span>
        <input
          className="ui-input"
          value={u.phone_number ?? ""}
          onChange={(e) => {
            setU({ ...u, phone_number: e.target.value || null });
            setError(null);
          }}
          placeholder="+7..."
          maxLength={100}
        />
      </label>

      <label className="ui-field">
        <span className="ui-field-label">О себе</span>
        <textarea
          className="ui-textarea"
          value={u.about ?? ""}
          onChange={(e) => {
            setU({ ...u, about: e.target.value || null });
            setError(null);
          }}
          rows={3}
          maxLength={5000}
        />
      </label>

      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "1fr 1fr" }}>
        <label className="ui-field">
          <span className="ui-field-label">Дата рождения</span>
          <input
            className="ui-input"
            type="date"
            value={u.date_of_birth?.slice(0, 10) ?? ""}
            onChange={(e) => {
              setU({ ...u, date_of_birth: e.target.value || null });
              setError(null);
            }}
          />
        </label>
        <label className="ui-field">
          <span className="ui-field-label">Пол</span>
          <select
            className="ui-select"
            value={u.gender ?? ""}
            onChange={(e) => {
              setU({
                ...u,
                gender: (e.target.value || null) as CurrentUser["gender"],
              });
              setError(null);
            }}
          >
            <option value="">Не указан</option>
            <option value="MALE">Мужской</option>
            <option value="FEMALE">Женский</option>
          </select>
        </label>
      </div>

      <div className="ui-card ui-card--muted" style={{ padding: 12 }}>
        <div className="ui-field-label" style={{ marginBottom: 4 }}>
          Дата регистрации
        </div>
        <div>{formatDateTime(u.date_and_time_registered)}</div>
      </div>

      <ValidationError message={error} />

      <button
        type="button"
        className="ui-btn ui-btn--primary ui-btn--block"
        disabled={saving}
        onClick={onSave}
      >
        {saving ? <span className="ui-spinner" aria-hidden="true" /> : <IconCheck size={18} />}
        {saving ? "Сохраняем…" : "Сохранить профиль"}
      </button>

      <hr className="ui-divider" />

      <button
        type="button"
        className="ui-btn ui-btn--danger ui-btn--block"
        onClick={onDelete}
      >
        <IconTrash size={18} />
        Удалить аккаунт
      </button>
    </div>
  );
}

/* =============================================================
   Security section
   ============================================================= */

function SecuritySection({
  currentLogin,
  emailAddress,
  onChangeLogin,
  onChangePassword,
  onChangeEmail,
}: {
  currentLogin: string;
  emailAddress: string;
  onChangeLogin: () => void;
  onChangePassword: () => void;
  onChangeEmail: () => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <SecurityCard
        icon={<IconAtSign size={22} />}
        title="Логин"
        description={currentLogin || "Загрузка…"}
        actionLabel="Сменить"
        onAction={onChangeLogin}
      />
      <SecurityCard
        icon={<IconKey size={22} />}
        title="Пароль"
        description="Используется для входа в аккаунт"
        actionLabel="Сменить"
        onAction={onChangePassword}
      />
      <SecurityCard
        icon={<IconMail size={22} />}
        title="Электронная почта"
        description={emailAddress}
        actionLabel="Сменить"
        onAction={onChangeEmail}
      />
      <p
        style={{
          margin: 0,
          padding: "10px 12px",
          fontSize: "0.85rem",
          color: "var(--text-muted)",
          background: "var(--bg-muted)",
          borderRadius: 10,
        }}
      >
        Изменения каждого параметра подтверждаются вводом текущего пароля или
        кода из письма. Это защищает аккаунт от несанкционированного доступа.
      </p>
    </div>
  );
}

function SecurityCard({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
}) {
  return (
    <div
      className="ui-card"
      style={{
        padding: 14,
        display: "flex",
        alignItems: "center",
        gap: 14,
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 12,
          background: "var(--accent-soft)",
          color: "var(--accent)",
          display: "grid",
          placeItems: "center",
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700 }}>{title}</div>
        <div
          style={{
            fontSize: "0.85rem",
            color: "var(--text-muted)",
            wordBreak: "break-word",
          }}
        >
          {description}
        </div>
      </div>
      <button
        type="button"
        className="ui-btn ui-btn--soft"
        onClick={onAction}
        style={{ flexShrink: 0 }}
      >
        {actionLabel}
        <IconChevronRight size={16} />
      </button>
    </div>
  );
}

/* =============================================================
   Change-login dialog
   ============================================================= */

function ChangeLoginDialog({
  currentLogin,
  onClose,
  onSuccess,
}: {
  currentLogin: string;
  onClose: () => void;
  onSuccess: (newLogin: string) => void;
}) {
  const { alert } = useDialogs();
  const [value, setValue] = useState(currentLogin);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    const e = validateLogin(value, "Новый логин");
    if (e) {
      setError(e);
      return;
    }
    if (value.trim() === currentLogin) {
      setError("Новый логин совпадает с текущим.");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await apiFetch("/users/me/login", {
        method: "PUT",
        body: JSON.stringify({ login: value.trim() }),
      });
      void alert("Логин обновлён");
      onSuccess(value.trim());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось сохранить");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalChrome title="Сменить логин" onClose={onClose} narrow>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="ui-card ui-card--muted" style={{ padding: 12 }}>
          <div className="ui-field-label" style={{ marginBottom: 4 }}>
            Текущий логин
          </div>
          <div style={{ wordBreak: "break-word" }}>{currentLogin || "—"}</div>
        </div>
        <label className="ui-field">
          <span className="ui-field-label">Новый логин</span>
          <input
            className="ui-input"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setError(null);
            }}
            maxLength={100}
            autoFocus
          />
        </label>
        <ValidationError message={error} />
        <div className="ui-modal-actions">
          <button type="button" className="ui-btn" onClick={onClose}>
            <IconX size={16} />
            Отмена
          </button>
          <button
            type="button"
            className="ui-btn ui-btn--primary"
            disabled={saving}
            onClick={() => void submit()}
          >
            {saving ? <span className="ui-spinner" aria-hidden="true" /> : <IconCheck size={16} />}
            {saving ? "Сохраняем…" : "Сменить логин"}
          </button>
        </div>
      </div>
    </ModalChrome>
  );
}

/* =============================================================
   Change-password dialog
   ============================================================= */

function ChangePasswordDialog({
  userId,
  onClose,
}: {
  userId: number;
  onClose: () => void;
}) {
  const { alert } = useDialogs();
  const [oldP, setOldP] = useState("");
  const [newP, setNewP] = useState("");
  const [repP, setRepP] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    const e1 = validatePassword(oldP, "Текущий пароль");
    const e2 = validatePassword(newP, "Новый пароль");
    const e3 = validatePassword(repP, "Повтор пароля");
    const e = e1 ?? e2 ?? e3;
    if (e) {
      setError(e);
      return;
    }
    if (newP !== repP) {
      setError("Новый пароль и повтор пароля не совпадают.");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await apiFetch("/users/me/password", {
        method: "PUT",
        body: JSON.stringify({ old_password: oldP, new_password: newP }),
      });
      void alert("Пароль обновлён");
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось сохранить");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalChrome title="Сменить пароль" onClose={onClose} narrow>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <label className="ui-field">
          <span className="ui-field-label">Текущий пароль</span>
          <input
            className="ui-input"
            type="password"
            name={`change-pwd-old-${userId}`}
            value={oldP}
            onChange={(e) => {
              setOldP(e.target.value);
              setError(null);
            }}
            autoComplete="new-password"
            maxLength={100}
            autoFocus
          />
        </label>
        <label className="ui-field">
          <span className="ui-field-label">Новый пароль</span>
          <input
            className="ui-input"
            type="password"
            name={`change-pwd-new-${userId}`}
            value={newP}
            onChange={(e) => {
              setNewP(e.target.value);
              setError(null);
            }}
            autoComplete="new-password"
            placeholder="Минимум 5 символов"
            maxLength={100}
          />
        </label>
        <label className="ui-field">
          <span className="ui-field-label">Повтор нового пароля</span>
          <input
            className="ui-input"
            type="password"
            name={`change-pwd-rep-${userId}`}
            value={repP}
            onChange={(e) => {
              setRepP(e.target.value);
              setError(null);
            }}
            autoComplete="new-password"
            maxLength={100}
          />
        </label>
        <ValidationError message={error} />
        <div className="ui-modal-actions">
          <button type="button" className="ui-btn" onClick={onClose}>
            <IconX size={16} />
            Отмена
          </button>
          <button
            type="button"
            className="ui-btn ui-btn--primary"
            disabled={saving}
            onClick={() => void submit()}
          >
            {saving ? <span className="ui-spinner" aria-hidden="true" /> : <IconCheck size={16} />}
            {saving ? "Сохраняем…" : "Сменить пароль"}
          </button>
        </div>
      </div>
    </ModalChrome>
  );
}

/* =============================================================
   Change-email dialog (with two steps)
   ============================================================= */

function ChangeEmailDialog({
  userId,
  currentEmail,
  onClose,
  onSuccess,
}: {
  userId: number;
  currentEmail: string;
  onClose: () => void;
  onSuccess: () => void | Promise<void>;
}) {
  const { alert } = useDialogs();
  const [step, setStep] = useState<"request" | "confirm">("request");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const requestCode = async () => {
    const e1 = validateEmailAddress(email, "Новая почта");
    if (e1) {
      setError(e1);
      return;
    }
    const e2 = validatePassword(password, "Пароль");
    if (e2) {
      setError(e2);
      return;
    }
    if (email.trim() === currentEmail) {
      setError("Новая почта совпадает с текущей.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await apiFetch("/users/me/email", {
        method: "PATCH",
        body: JSON.stringify({
          email_address: email.trim(),
          password,
        }),
      });
      setStep("confirm");
      void alert("Код отправлен на новую почту");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось отправить");
    } finally {
      setBusy(false);
    }
  };

  const confirmCode = async () => {
    const e = validateCode(code, "Код");
    if (e) {
      setError(e);
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await apiFetch("/users/me/email/confirm", {
        method: "PATCH",
        body: JSON.stringify({ code: code.trim() }),
      });
      void alert("Почта обновлена");
      await onSuccess();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Неверный код");
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModalChrome
      title={step === "request" ? "Сменить почту" : "Подтверждение почты"}
      onClose={onClose}
      narrow
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {step === "request" ? (
          <>
            <div className="ui-card ui-card--muted" style={{ padding: 12 }}>
              <div className="ui-field-label" style={{ marginBottom: 4 }}>
                Текущая электронная почта
              </div>
              <div style={{ wordBreak: "break-word" }}>{currentEmail}</div>
            </div>
            <label className="ui-field">
              <span className="ui-field-label">Новая почта</span>
              <input
                className="ui-input"
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setError(null);
                }}
                autoComplete="off"
                maxLength={254}
                autoFocus
              />
            </label>
            <label className="ui-field">
              <span className="ui-field-label">Пароль от аккаунта</span>
              <input
                className="ui-input"
                type="password"
                name={`change-email-password-${userId}`}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError(null);
                }}
                autoComplete="new-password"
                maxLength={100}
              />
            </label>
            <ValidationError message={error} />
            <div className="ui-modal-actions">
              <button type="button" className="ui-btn" onClick={onClose}>
                <IconX size={16} />
                Отмена
              </button>
              <button
                type="button"
                className="ui-btn ui-btn--primary"
                disabled={busy}
                onClick={() => void requestCode()}
              >
                {busy ? <span className="ui-spinner" aria-hidden="true" /> : null}
                {busy ? "Отправляем…" : "Отправить код"}
              </button>
            </div>
          </>
        ) : (
          <>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.92rem" }}>
              Мы отправили 6-значный код на <strong>{email}</strong>. Введите его
              ниже, чтобы завершить смену почты.
            </p>
            <label className="ui-field">
              <span className="ui-field-label">Код из письма</span>
              <input
                className="ui-input"
                value={code}
                onChange={(e) => {
                  setCode(e.target.value);
                  setError(null);
                }}
                maxLength={6}
                autoComplete="one-time-code"
                inputMode="numeric"
                autoFocus
                placeholder="6 цифр"
              />
            </label>
            <ValidationError message={error} />
            <div className="ui-modal-actions">
              <button
                type="button"
                className="ui-btn"
                onClick={() => setStep("request")}
              >
                Назад
              </button>
              <button
                type="button"
                className="ui-btn ui-btn--primary"
                disabled={busy}
                onClick={() => void confirmCode()}
              >
                {busy ? <span className="ui-spinner" aria-hidden="true" /> : <IconCheck size={16} />}
                {busy ? "Сохраняем…" : "Подтвердить"}
              </button>
            </div>
          </>
        )}
      </div>
    </ModalChrome>
  );
}

/* =============================================================
   Search panels (used inside Users / Friends)
   ============================================================= */

function SearchPanel<
  T extends { mode: "all" | "username" | "names"; q: string; n: string; s: string; o: string },
>({
  search,
  setSearch,
  searchError,
  onClearSearchError,
  onSearch,
}: {
  search: T;
  setSearch: (s: T) => void;
  searchError: string | null;
  onClearSearchError: () => void;
  onSearch: () => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 10 }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {(
          [
            ["all", "Все"],
            ["username", "По username"],
            ["names", "По ФИО"],
          ] as const
        ).map(([mode, label]) => {
          const active = search.mode === mode;
          return (
            <button
              key={mode}
              type="button"
              className={
                active
                  ? "ui-btn ui-btn--tab ui-btn--sm is-active"
                  : "ui-btn ui-btn--tab ui-btn--sm"
              }
              onClick={() => {
                setSearch({ ...search, mode });
                onClearSearchError();
              }}
            >
              {label}
            </button>
          );
        })}
      </div>
      {search.mode === "username" ? (
        <label className="ui-field">
          <span className="ui-field-label">Имя пользователя</span>
          <input
            className="ui-input"
            value={search.q}
            onChange={(e) => {
              setSearch({ ...search, q: e.target.value });
              onClearSearchError();
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                (e.currentTarget as HTMLInputElement).blur();
                onSearch();
              }
            }}
            enterKeyHint="search"
            type="search"
            maxLength={100}
            placeholder="Введите username"
          />
        </label>
      ) : null}
      {search.mode === "names" ? (
        <div style={{ display: "grid", gap: 8, gridTemplateColumns: "1fr 1fr 1fr" }}>
          {(
            [
              ["n", "Имя"],
              ["s", "Фамилия"],
              ["o", "Отчество"],
            ] as const
          ).map(([key, lab]) => (
            <label key={key} className="ui-field">
              <span className="ui-field-label">{lab}</span>
              <input
                className="ui-input"
                value={search[key]}
                onChange={(e) => {
                  setSearch({ ...search, [key]: e.target.value });
                  onClearSearchError();
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    (e.currentTarget as HTMLInputElement).blur();
                    onSearch();
                  }
                }}
                enterKeyHint="search"
                type="search"
                maxLength={100}
              />
            </label>
          ))}
        </div>
      ) : null}
      <ValidationError message={searchError} />
      <button
        type="button"
        className="ui-btn ui-btn--primary ui-btn--block"
        onClick={onSearch}
      >
        <IconSearch size={16} />
        Показать
      </button>
    </div>
  );
}

/* =============================================================
   Users list section
   ============================================================= */

function UsersListSection({
  items,
  done,
  search,
  setSearch,
  searchError,
  onClearSearchError,
  onSearch,
  onMore,
  onOpenProfile,
  assetEpoch,
}: {
  items: UserInList[];
  done: boolean;
  search: { mode: "all" | "username" | "names"; q: string; n: string; s: string; o: string };
  setSearch: (s: typeof search) => void;
  searchError: string | null;
  onClearSearchError: () => void;
  onSearch: () => void;
  onMore: () => void;
  onOpenProfile: (uid: number) => void;
  assetEpoch: number;
}) {
  return (
    <div>
      <SearchPanel
        search={search}
        setSearch={setSearch}
        searchError={searchError}
        onClearSearchError={onClearSearchError}
        onSearch={onSearch}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          maxHeight: 480,
          overflowY: "auto",
          paddingRight: 4,
        }}
      >
        {items.map((row) => (
          <button
            key={row.id}
            type="button"
            className="ui-row ui-row--button"
            onClick={() => onOpenProfile(row.id)}
          >
            <Avatar
              src={userAvatarUrl(row.id, assetEpoch)}
              label={avatarLetterFromUser(row)}
              size={42}
            />
            <span style={{ minWidth: 0, fontSize: "0.92rem", overflow: "hidden", textOverflow: "ellipsis" }}>
              {userListLabel(row)}
            </span>
          </button>
        ))}
        {items.length === 0 ? (
          <EmptyHint text="Список пуст" />
        ) : null}
      </div>
      {!done ? (
        <button type="button" className="ui-btn ui-btn--ghost ui-btn--block" style={{ marginTop: 8 }} onClick={onMore}>
          Загрузить ещё
        </button>
      ) : null}
    </div>
  );
}

/* =============================================================
   Friends list section
   ============================================================= */

function FriendsListSection({
  items,
  done,
  search,
  setSearch,
  searchError,
  onClearSearchError,
  onSearch,
  onMore,
  onOpenProfile,
  onRemoveFriend,
  assetEpoch,
}: {
  items: FriendUser[];
  done: boolean;
  search: { mode: "all" | "username" | "names"; q: string; n: string; s: string; o: string };
  setSearch: (s: typeof search) => void;
  searchError: string | null;
  onClearSearchError: () => void;
  onSearch: () => void;
  onMore: () => void;
  onOpenProfile: (uid: number) => void;
  onRemoveFriend: (friendshipId: number) => void;
  assetEpoch: number;
}) {
  return (
    <div>
      <SearchPanel
        search={search}
        setSearch={setSearch}
        searchError={searchError}
        onClearSearchError={onClearSearchError}
        onSearch={onSearch}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          maxHeight: 480,
          overflowY: "auto",
          paddingRight: 4,
        }}
      >
        {items.map((row) => (
          <div key={row.id} className="ui-row" style={{ gap: 10 }}>
            <button
              type="button"
              onClick={() => onOpenProfile(row.id)}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                gap: 10,
                border: "none",
                background: "none",
                padding: 0,
                minWidth: 0,
                cursor: "pointer",
                color: "inherit",
                textAlign: "left",
              }}
            >
              <Avatar
                src={userAvatarUrl(row.id, assetEpoch)}
                label={avatarLetterFromUser(row)}
                size={42}
              />
              <span style={{ fontSize: "0.92rem", overflow: "hidden", textOverflow: "ellipsis" }}>
                {userListLabel(row)}
              </span>
            </button>
            <button
              type="button"
              className="ui-icon-btn ui-icon-btn--danger"
              title="Удалить из друзей"
              aria-label="Удалить из друзей"
              onClick={() => onRemoveFriend(row.friendship_id)}
            >
              <IconUserX size={18} />
            </button>
          </div>
        ))}
        {items.length === 0 ? <EmptyHint text="Список пуст" /> : null}
      </div>
      {!done ? (
        <button
          type="button"
          className="ui-btn ui-btn--ghost ui-btn--block"
          style={{ marginTop: 8 }}
          onClick={onMore}
        >
          Загрузить ещё
        </button>
      ) : null}
    </div>
  );
}

/* =============================================================
   Incoming requests section
   ============================================================= */

function IncomingSection({
  items,
  done,
  onMore,
  onAccept,
  onDecline,
  onOpenProfile,
  userMap,
  assetEpoch,
}: {
  items: FriendRequest[];
  done: boolean;
  onMore: () => void;
  onAccept: (id: number) => void;
  onDecline: (id: number) => void;
  onOpenProfile: (uid: number) => void;
  userMap: Record<number, UserInList>;
  assetEpoch: number;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 540, overflowY: "auto", paddingRight: 4 }}>
      {items.map((r) => {
        const u = userMap[r.sender_user_id];
        return (
          <div key={r.id} className="ui-row" style={{ gap: 10, flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={() => onOpenProfile(r.sender_user_id)}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                gap: 10,
                border: "none",
                background: "none",
                padding: 0,
                minWidth: 160,
                cursor: "pointer",
                color: "inherit",
                textAlign: "left",
              }}
            >
              <Avatar
                src={userAvatarUrl(r.sender_user_id, assetEpoch)}
                label={u ? avatarLetterFromUser(u) : "?"}
                size={42}
              />
              <span style={{ fontSize: "0.92rem", overflow: "hidden", textOverflow: "ellipsis" }}>
                {u ? userListLabel(u) : `Пользователь #${r.sender_user_id}`}
              </span>
            </button>
            <button type="button" className="ui-btn ui-btn--primary ui-btn--sm" onClick={() => onAccept(r.id)}>
              <IconCheck size={16} /> Принять
            </button>
            <button type="button" className="ui-btn ui-btn--ghost ui-btn--sm" onClick={() => onDecline(r.id)}>
              <IconX size={16} /> Отклонить
            </button>
          </div>
        );
      })}
      {items.length === 0 ? <EmptyHint text="Заявок пока нет" /> : null}
      {!done ? (
        <button type="button" className="ui-btn ui-btn--ghost ui-btn--block" style={{ marginTop: 8 }} onClick={onMore}>
          Загрузить ещё
        </button>
      ) : null}
    </div>
  );
}

/* =============================================================
   Outgoing requests section
   ============================================================= */

function OutgoingSection({
  items,
  done,
  onMore,
  onCancel,
  onOpenProfile,
  userMap,
  assetEpoch,
}: {
  items: FriendRequest[];
  done: boolean;
  onMore: () => void;
  onCancel: (id: number) => void;
  onOpenProfile: (uid: number) => void;
  userMap: Record<number, UserInList>;
  assetEpoch: number;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 540, overflowY: "auto", paddingRight: 4 }}>
      {items.map((r) => {
        const u = userMap[r.receiver_user_id];
        return (
          <div key={r.id} className="ui-row" style={{ gap: 10 }}>
            <button
              type="button"
              onClick={() => onOpenProfile(r.receiver_user_id)}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                gap: 10,
                border: "none",
                background: "none",
                padding: 0,
                minWidth: 0,
                cursor: "pointer",
                color: "inherit",
                textAlign: "left",
              }}
            >
              <Avatar
                src={userAvatarUrl(r.receiver_user_id, assetEpoch)}
                label={u ? avatarLetterFromUser(u) : "?"}
                size={42}
              />
              <span style={{ fontSize: "0.92rem", overflow: "hidden", textOverflow: "ellipsis" }}>
                {u ? userListLabel(u) : `Пользователь #${r.receiver_user_id}`}
              </span>
            </button>
            <button
              type="button"
              className="ui-icon-btn ui-icon-btn--danger"
              title="Отозвать заявку"
              aria-label="Отозвать заявку"
              onClick={() => onCancel(r.id)}
            >
              <IconTrash size={18} />
            </button>
          </div>
        );
      })}
      {items.length === 0 ? <EmptyHint text="Исходящих заявок нет" /> : null}
      {!done ? (
        <button type="button" className="ui-btn ui-btn--ghost ui-btn--block" style={{ marginTop: 8 }} onClick={onMore}>
          Загрузить ещё
        </button>
      ) : null}
    </div>
  );
}

/* =============================================================
   Blocks section
   ============================================================= */

function BlocksSection({
  items,
  done,
  onMore,
  onUnblock,
  onOpenProfile,
  userMap,
  assetEpoch,
}: {
  items: UserBlockRow[];
  done: boolean;
  onMore: () => void;
  onUnblock: (blockId: number) => void;
  onOpenProfile: (uid: number) => void;
  userMap: Record<number, UserInList>;
  assetEpoch: number;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 540, overflowY: "auto", paddingRight: 4 }}>
      {items.map((b) => {
        const u = userMap[b.blocked_user_id];
        return (
          <div key={b.id} className="ui-row" style={{ gap: 10 }}>
            <button
              type="button"
              onClick={() => onOpenProfile(b.blocked_user_id)}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                gap: 10,
                border: "none",
                background: "none",
                padding: 0,
                minWidth: 0,
                cursor: "pointer",
                color: "inherit",
                textAlign: "left",
              }}
            >
              <Avatar
                src={userAvatarUrl(b.blocked_user_id, assetEpoch)}
                label={u ? avatarLetterFromUser(u) : `#${b.blocked_user_id}`}
                size={42}
              />
              <span style={{ fontSize: "0.92rem", overflow: "hidden", textOverflow: "ellipsis" }}>
                {u ? userListLabel(u) : `Пользователь #${b.blocked_user_id}`}
              </span>
            </button>
            <button
              type="button"
              className="ui-btn ui-btn--soft ui-btn--sm"
              onClick={() => onUnblock(b.id)}
            >
              <IconUserPlus size={16} /> Разблокировать
            </button>
          </div>
        );
      })}
      {items.length === 0 ? <EmptyHint text="Заблокированных пользователей нет" /> : null}
      {!done ? (
        <button type="button" className="ui-btn ui-btn--ghost ui-btn--block" style={{ marginTop: 8 }} onClick={onMore}>
          Загрузить ещё
        </button>
      ) : null}
    </div>
  );
}

/* =============================================================
   Helpers
   ============================================================= */

function EmptyHint({ text }: { text: string }) {
  return (
    <div
      style={{
        padding: "24px 12px",
        color: "var(--text-muted)",
        textAlign: "center",
        fontSize: "0.9rem",
      }}
    >
      {text}
    </div>
  );
}
