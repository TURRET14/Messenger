import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { ApiError, apiFetch, apiJson } from "../api/client";
import type {
  Chat,
  ChatRole,
  CurrentUser,
  Message,
  MessageReadMark,
  UserInList,
} from "../api/types";
import { SERVICE_DISPLAY_NAME } from "../config";
import {
  IconChat,
  IconChevronLeft,
  IconLogout,
  IconMenu,
  IconPaperclip,
  IconPlus,
  IconSearch,
  IconSend,
  IconUser,
  IconX,
} from "../components/Icons";
import { Avatar, chatAvatarUrl, userAvatarUrl } from "../components/ui/Avatar";
import { ModalChrome } from "../components/ui/ModalChrome";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useDialogs } from "../context/DialogsContext";
import { useBackendSocket } from "../hooks/useBackendSocket";
import { ChatInfoPanel, type MembershipRow } from "./ChatInfoPanel";
import { MainAppMenu } from "./MainAppMenu";
import { MessageBubble, PickedFilesStrip } from "./MessageBubble";
import { useMsgWebSocket } from "./useMsgWebSocket";
import { avatarLetterFromUser, userListLabel } from "./userFormat";
import { UserProfileModal } from "./UserProfileModal";

const PAGE = 50;

function chatLabel(c: Chat): string {
  if (c.chat_kind === "PROFILE") return c.name || "Профиль";
  if (c.chat_kind === "PRIVATE") return c.name || "Личный чат";
  return c.name || "Чат";
}

function kindLabel(k: Chat["chat_kind"]): string {
  const m: Record<string, string> = {
    PRIVATE: "Личный",
    GROUP: "Группа",
    CHANNEL: "Канал",
    PROFILE: "Профиль",
  };
  return m[k] ?? k;
}

function mergeByIdAsc(existing: Message[], incoming: Message): Message[] {
  const next = existing.filter((m) => m.id !== incoming.id);
  next.push(incoming);
  next.sort(
    (a, b) =>
      new Date(a.date_and_time_sent).getTime() -
      new Date(b.date_and_time_sent).getTime(),
  );
  return next;
}

async function fetchMyRole(chatId: number, userId: number): Promise<ChatRole | null> {
  let off = 0;
  for (;;) {
    const batch = await apiJson<MembershipRow[]>(
      `/chats/id/${chatId}/memberships?offset_multiplier=${off}`,
    );
    const mine = batch.find((r) => r.chat_user_id === userId);
    if (mine) return mine.chat_role;
    if (batch.length < PAGE) return null;
    off += 1;
  }
}

export function MessengerShell({
  currentUser: initialUser,
  onLogout,
}: {
  currentUser: CurrentUser;
  onLogout: () => void;
}) {
  const { alert, confirm } = useDialogs();
  const [currentUser, setCurrentUser] = useState(initialUser);
  useEffect(() => setCurrentUser(initialUser), [initialUser]);

  const [wide, setWide] = useState(true);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 900px)");
    const fn = () => setWide(mq.matches);
    setWide(mq.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);

  const [chats, setChats] = useState<Chat[]>([]);
  const chatPageRef = useRef(0);
  const [chatsDone, setChatsDone] = useState(false);
  const [loadingChats, setLoadingChats] = useState(false);
  const chatLoadRef = useRef(false);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedChatData, setSelectedChatData] = useState<Chat | null>(null);
  const [myRole, setMyRole] = useState<ChatRole | null>(null);

  const [commentRoot, setCommentRoot] = useState<Message | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const msgPageRef = useRef(0);
  const [msgDone, setMsgDone] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState(false);

  const [draft, setDraft] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const [editing, setEditing] = useState<Message | null>(null);

  const [replyCache, setReplyCache] = useState<Record<number, Message>>({});
  const [userNames, setUserNames] = useState<Record<number, string>>({});
  const userNamesRef = useRef(userNames);
  userNamesRef.current = userNames;
  const nameInflightRef = useRef(new Set<number>());

  const [composeOpen, setComposeOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileUserId, setProfileUserId] = useState<number | null>(null);
  const [infoOpen, setInfoOpen] = useState(false);

  const [composeTab, setComposeTab] = useState<"private" | "group" | "channel">("private");
  const [usernameQuery, setUsernameQuery] = useState("");
  const [searchHits, setSearchHits] = useState<UserInList[]>([]);
  const [groupName, setGroupName] = useState("");

  const [hdrSearch, setHdrSearch] = useState("");
  const [searchHitsChat, setSearchHitsChat] = useState<Message[]>([]);
  const [searchMode, setSearchMode] = useState(false);
  const searchModeRef = useRef(false);
  useEffect(() => {
    searchModeRef.current = searchMode;
  }, [searchMode]);
  const searchChatPageRef = useRef(0);
  const [searchChatDone, setSearchChatDone] = useState(false);
  const [loadingSearchChat, setLoadingSearchChat] = useState(false);

  const [assetEpoch, setAssetEpoch] = useState(0);
  const bumpAssets = useCallback(() => setAssetEpoch((x) => x + 1), []);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [privatePeerByChat, setPrivatePeerByChat] = useState<Record<number, number>>({});

  const readMarkedRef = useRef(new Set<number>());

  const ensureName = useCallback(async (uid: number) => {
    if (userNamesRef.current[uid]) return;
    if (nameInflightRef.current.has(uid)) return;
    nameInflightRef.current.add(uid);
    try {
      const u = await apiJson<UserInList>(`/users/id/${uid}`);
      setUserNames((p) => (p[uid] ? p : { ...p, [uid]: userListLabel(u) }));
    } catch {
      setUserNames((p) => (p[uid] ? p : { ...p, [uid]: `#${uid}` }));
    } finally {
      nameInflightRef.current.delete(uid);
    }
  }, []);

  const refreshChats = useCallback(async () => {
    if (chatLoadRef.current) return;
    chatLoadRef.current = true;
    setLoadingChats(true);
    try {
      const batch = await apiJson<Chat[]>(`/chats?offset_multiplier=0`);
      chatPageRef.current = 0;
      setChats(batch);
      setChatsDone(batch.length < PAGE);
      for (const c of batch) {
        const lm = c.last_message;
        if (lm?.sender_user_id != null) void ensureName(lm.sender_user_id);
      }
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Чаты не загружены");
    } finally {
      setLoadingChats(false);
      chatLoadRef.current = false;
    }
  }, [alert, ensureName]);

  const loadMoreChats = async () => {
    if (loadingChats || chatsDone) return;
    setLoadingChats(true);
    try {
      const mult = chatPageRef.current + 1;
      const batch = await apiJson<Chat[]>(`/chats?offset_multiplier=${mult}`);
      chatPageRef.current = mult;
      setChats((prev) => {
        const ids = new Set(prev.map((x) => x.id));
        return [...prev, ...batch.filter((x) => !ids.has(x.id))];
      });
      if (batch.length < PAGE) setChatsDone(true);
      for (const c of batch) {
        const lm = c.last_message;
        if (lm?.sender_user_id != null) void ensureName(lm.sender_user_id);
      }
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    } finally {
      setLoadingChats(false);
    }
  };

  useEffect(() => {
    void refreshChats();
  }, []);

  const selectedChat = useMemo(() => {
    const fromList = chats.find((c) => c.id === selectedId) ?? null;
    if (fromList) return fromList;
    return selectedChatData && selectedChatData.id === selectedId ? selectedChatData : null;
  }, [chats, selectedId, selectedChatData]);

  const sortedChats = useMemo(() => {
    const ts = (c: Chat) =>
      c.last_message?.date_and_time_sent
        ? new Date(c.last_message.date_and_time_sent).getTime()
        : new Date(c.date_and_time_created).getTime();
    return [...chats].sort((a, b) => ts(b) - ts(a));
  }, [chats]);

  const openChatById = useCallback(
    async (chatId: number, options?: { ephemeral?: boolean }) => {
      try {
        const fresh = await apiJson<Chat>(`/chats/id/${chatId}`);
        if (!options?.ephemeral) {
          setChats((prev) => {
            const rest = prev.filter((c) => c.id !== chatId);
            return [...rest, fresh];
          });
        }
        setSelectedChatData(fresh);
        setSelectedId(chatId);
        setCommentRoot(null);
        setProfileUserId(null);
      } catch (e) {
        void alert(e instanceof ApiError ? e.message : "Чат не открыт");
      }
    },
    [alert],
  );

  const ensurePrivatePeer = useCallback(
    async (chatId: number) => {
      if (privatePeerByChat[chatId]) return privatePeerByChat[chatId];
      const mem = await apiJson<MembershipRow[]>(
        `/chats/id/${chatId}/memberships?offset_multiplier=0`,
      );
      const peer = mem.find((m) => m.chat_user_id !== currentUser.id)?.chat_user_id;
      if (peer) {
        setPrivatePeerByChat((p) => ({ ...p, [chatId]: peer }));
        return peer;
      }
      return null;
    },
    [privatePeerByChat, currentUser.id],
  );

  useEffect(() => {
    setSearchMode(false);
    setSearchHitsChat([]);
    searchChatPageRef.current = 0;
    setSearchChatDone(false);
  }, [selectedId, commentRoot?.id]);

  useEffect(() => {
    if (!selectedId) setSelectedChatData(null);
  }, [selectedId]);

  useEffect(() => {
    for (const c of chats) {
      if (c.chat_kind === "PRIVATE") void ensurePrivatePeer(c.id);
    }
  }, [chats, ensurePrivatePeer]);

  useEffect(() => {
    if (!selectedId) {
      setMyRole(null);
      return;
    }
    void (async () => {
      try {
        const fresh = await apiJson<Chat>(`/chats/id/${selectedId}`);
        setSelectedChatData((prev) => (prev?.id === fresh.id ? { ...prev, ...fresh } : prev));
        setChats((prev) =>
          prev.map((c) =>
            c.id === selectedId
              ? {
                  ...c,
                  ...fresh,
                  last_message: fresh.last_message ?? c.last_message,
                }
              : c,
          ),
        );
        const role = await fetchMyRole(selectedId, currentUser.id);
        setMyRole(role);
      } catch {
        setMyRole(null);
      }
    })();
  }, [selectedId, currentUser.id]);

  const loadMessages = useCallback(
    async (reset: boolean) => {
      if (!selectedId) return;
      setLoadingMsg(true);
      try {
        const mult = reset ? 0 : msgPageRef.current + 1;
        let batch: Message[];
        if (commentRoot) {
          batch = await apiJson<Message[]>(
            `/chats/id/${selectedId}/messages/id/${commentRoot.id}/comments?offset_multiplier=${mult}`,
          );
        } else {
          batch = await apiJson<Message[]>(
            `/chats/id/${selectedId}/messages?offset_multiplier=${mult}`,
          );
        }
        const reversed = [...batch].reverse();
        if (reset) {
          msgPageRef.current = 0;
          setMessages(reversed);
          setMsgDone(batch.length < PAGE);
        } else {
          msgPageRef.current = mult;
          setMessages((prev) => [...reversed, ...prev]);
          if (batch.length < PAGE) setMsgDone(true);
        }
        for (const m of batch) {
          if (m.sender_user_id) void ensureName(m.sender_user_id);
          if (m.reply_message_id) {
            const rid = m.reply_message_id;
            void (async () => {
              try {
                const rm = await apiJson<Message>(
                  `/chats/id/${selectedId}/messages/id/${rid}`,
                );
                setReplyCache((p) => (p[rm.id] ? p : { ...p, [rm.id]: rm }));
                if (rm.sender_user_id) void ensureName(rm.sender_user_id);
              } catch {
                /* skip */
              }
            })();
          }
        }
      } catch (e) {
        void alert(e instanceof ApiError ? e.message : "Сообщения не загружены");
      } finally {
        setLoadingMsg(false);
      }
    },
    [selectedId, commentRoot, alert, ensureName],
  );

  useEffect(() => {
    if (!selectedId) {
      setMessages([]);
      return;
    }
    msgPageRef.current = 0;
    setMsgDone(false);
    void loadMessages(true);
  }, [selectedId, commentRoot?.id, loadMessages]);

  const reloadMsgs = () => {
    if (selectedId) void loadMessages(true);
  };

  useBackendSocket("/chats/post", true, refreshChats);
  useBackendSocket("/chats/put", true, refreshChats);
  useBackendSocket("/chats/delete", true, refreshChats);
  useBackendSocket("/chats/messages/last", true, refreshChats);

  const parentKey = commentRoot?.id ?? null;
  const onWsMsg = useCallback(
    (ev: MessageEvent) => {
      if (!selectedId || searchModeRef.current) return;
      try {
        const data = JSON.parse(ev.data as string) as Message;
        const p = data.parent_message_id ?? null;
        if (data.chat_id !== selectedId || p !== parentKey) return;
        setMessages((prev) => mergeByIdAsc(prev, data));
        if (data.sender_user_id) void ensureName(data.sender_user_id);
      } catch {
        reloadMsgs();
      }
    },
    [selectedId, parentKey, ensureName],
  );

  const onWsDel = useCallback(
    (ev: MessageEvent) => {
      if (!selectedId || searchModeRef.current) return;
      try {
        const data = JSON.parse(ev.data as string) as Message;
        const p = data.parent_message_id ?? null;
        if (data.chat_id !== selectedId || p !== parentKey) return;
        setMessages((prev) => prev.filter((x) => x.id !== data.id));
      } catch {
        reloadMsgs();
      }
    },
    [selectedId, parentKey],
  );

  const onWsRead = useCallback(
    (ev: MessageEvent) => {
      if (!selectedId || searchModeRef.current) return;
      try {
        const data = JSON.parse(ev.data as string) as MessageReadMark;
        if (data.chat_id !== selectedId) return;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === data.message_id ? { ...m, is_read: true } : m,
          ),
        );
      } catch {
        /* ignore */
      }
    },
    [selectedId],
  );

  const readWsEnabled =
    !searchMode &&
    !!selectedChat &&
    (selectedChat.chat_kind === "PRIVATE" ||
      selectedChat.chat_kind === "GROUP");

  useMsgWebSocket(selectedId, parentKey, "/messages/post", onWsMsg, true);
  useMsgWebSocket(selectedId, parentKey, "/messages/put", onWsMsg, true);
  useMsgWebSocket(selectedId, parentKey, "/messages/delete", onWsDel, true);
  useMsgWebSocket(selectedId, null, "/messages/read", onWsRead, readWsEnabled);

  const chatAvatarSrc = (c: Chat): string | null => {
    if (!c.has_avatar) return null;
    if (c.chat_kind === "PROFILE" && c.owner_user_id != null) {
      return userAvatarUrl(c.owner_user_id, assetEpoch);
    }
    if (c.chat_kind === "PRIVATE") {
      const peer = privatePeerByChat[c.id];
      return peer ? userAvatarUrl(peer, assetEpoch) : null;
    }
    return chatAvatarUrl(c.id, assetEpoch);
  };

  const isOwner = selectedChat?.owner_user_id === currentUser.id;
  const isAdmin = myRole === "ADMIN" || isOwner;

  const canPostRoot =
    !!selectedChat &&
    (selectedChat.chat_kind === "GROUP" ||
      selectedChat.chat_kind === "PRIVATE" ||
      (selectedChat.chat_kind === "CHANNEL" && isAdmin) ||
      (selectedChat.chat_kind === "PROFILE" && isOwner));

  const canPostHere = commentRoot ? true : canPostRoot;

  const canDeleteMessage = (m: Message) => {
    if (!selectedChat) return false;
    if (m.sender_user_id === currentUser.id) return true;
    if (
      (selectedChat.chat_kind === "CHANNEL" ||
        selectedChat.chat_kind === "PROFILE") &&
      isOwner
    )
      return true;
    return false;
  };

  const canCommentBtn =
    selectedChat &&
    (selectedChat.chat_kind === "CHANNEL" ||
      selectedChat.chat_kind === "PROFILE") &&
    !commentRoot;

  useEffect(() => {
    if (searchMode) return;
    if (!selectedChat || !selectedId) return;
    if (
      selectedChat.chat_kind !== "GROUP" &&
      selectedChat.chat_kind !== "PRIVATE"
    )
      return;
    for (const m of messages) {
      if (
        m.sender_user_id &&
        m.sender_user_id !== currentUser.id &&
        m.is_read !== true &&
        !readMarkedRef.current.has(m.id)
      ) {
        readMarkedRef.current.add(m.id);
        void apiFetch(`/chats/id/${selectedId}/messages/id/${m.id}/read`, {
          method: "POST",
        }).catch(() => readMarkedRef.current.delete(m.id));
      }
    }
  }, [messages, selectedChat, selectedId, currentUser.id, searchMode]);

  const displayName = (uid: number | null) => {
    if (uid == null) return "Система";
    if (uid === currentUser.id) return "Вы";
    return userNames[uid] ?? `…${uid}`;
  };

  const handleSend = async () => {
    if (!selectedId) return;
    const text = draft.trim();
    if (!text && files.length === 0) {
      void alert("Введите текст или прикрепите файл");
      return;
    }
    const fd = new FormData();
    fd.append("message_text", text);
    if (replyTo) fd.append("reply_message_id", String(replyTo.id));
    if (commentRoot) fd.append("parent_message_id", String(commentRoot.id));
    for (const f of files) fd.append("file_attachments_list", f, f.name);
    try {
      await apiFetch(`/chats/id/${selectedId}/messages`, {
        method: "POST",
        body: fd,
      });
      setDraft("");
      setFiles([]);
      setReplyTo(null);
      reloadMsgs();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не отправлено");
    }
  };

  const handleDelete = async (m: Message) => {
    if (!selectedId) return;
    if (!(await confirm({ message: "Удалить сообщение?", danger: true })))
      return;
    try {
      await apiFetch(
        `/chats/id/${selectedId}/messages/id/${m.id}`,
        { method: "DELETE" },
      );
      setMessages((prev) => prev.filter((x) => x.id !== m.id));
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалено");
    }
  };

  const handleSaveEdit = async () => {
    if (!selectedId || !editing) return;
    try {
      await apiFetch(
        `/chats/id/${selectedId}/messages/id/${editing.id}`,
        {
          method: "PUT",
          body: JSON.stringify({ message_text: draft }),
        },
      );
      setEditing(null);
      setDraft("");
      reloadMsgs();
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не сохранено");
    }
  };

  const runHdrSearch = async () => {
    if (!selectedId) return;
    const q = hdrSearch.trim();
    if (!q) {
      setSearchMode(false);
      setSearchHitsChat([]);
      searchChatPageRef.current = 0;
      setSearchChatDone(false);
      void loadMessages(true);
      return;
    }
    setLoadingSearchChat(true);
    try {
      const enc = encodeURIComponent(q);
      const path = commentRoot
        ? `/chats/id/${selectedId}/messages/id/${commentRoot.id}/comments/search?message_text=${enc}&offset_multiplier=0`
        : `/chats/id/${selectedId}/messages/search?message_text=${enc}&offset_multiplier=0`;
      const batch = await apiJson<Message[]>(path);
      const reversed = [...batch].reverse();
      searchChatPageRef.current = 0;
      setSearchHitsChat(reversed);
      setSearchChatDone(batch.length < PAGE);
      setSearchMode(true);
      for (const m of batch) {
        if (m.sender_user_id) void ensureName(m.sender_user_id);
      }
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Поиск не выполнен");
    } finally {
      setLoadingSearchChat(false);
    }
  };

  const loadMoreSearchChat = async () => {
    if (!selectedId || !searchMode || loadingSearchChat || searchChatDone) return;
    const q = hdrSearch.trim();
    if (!q) return;
    setLoadingSearchChat(true);
    try {
      const mult = searchChatPageRef.current + 1;
      const enc = encodeURIComponent(q);
      const path = commentRoot
        ? `/chats/id/${selectedId}/messages/id/${commentRoot.id}/comments/search?message_text=${enc}&offset_multiplier=${mult}`
        : `/chats/id/${selectedId}/messages/search?message_text=${enc}&offset_multiplier=${mult}`;
      const batch = await apiJson<Message[]>(path);
      searchChatPageRef.current = mult;
      const reversed = [...batch].reverse();
      setSearchHitsChat((prev) => {
        const ids = new Set(prev.map((x) => x.id));
        const add = reversed.filter((x) => !ids.has(x.id));
        return [...add, ...prev];
      });
      if (batch.length < PAGE) setSearchChatDone(true);
      for (const m of batch) {
        if (m.sender_user_id) void ensureName(m.sender_user_id);
      }
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Поиск не выполнен");
    } finally {
      setLoadingSearchChat(false);
    }
  };

  const searchUsersCompose = async () => {
    const q = usernameQuery.trim();
    if (!q) {
      setSearchHits([]);
      return;
    }
    try {
      const hits = await apiJson<UserInList[]>(
        `/users/search/by-username?username=${encodeURIComponent(q)}&offset_multiplier=0`,
      );
      setSearchHits(hits);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Поиск не выполнен");
    }
  };

  const openOrCreatePrivateChat = async (userId: number) => {
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
  };

  const createPrivate = async (userId: number) => {
    try {
      const id = await openOrCreatePrivateChat(userId);
      setComposeOpen(false);
      await refreshChats();
      await openChatById(id);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не создан чат");
    }
  };

  const createGroupOrChannel = async (kind: "group" | "channel") => {
    const name = groupName.trim();
    if (!name) {
      void alert("Укажите название");
      return;
    }
    try {
      const path = kind === "group" ? "/chats/group" : "/chats/channels";
      const res = await apiJson<{ id: number }>(path, {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      setComposeOpen(false);
      setGroupName("");
      await refreshChats();
      await openChatById(res.id);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не создано");
    }
  };

  const shell: CSSProperties = {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    overflow: "hidden",
  };

  const topBar: CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 12px",
    borderBottom: "1px solid var(--border)",
    background: "var(--bg-elevated)",
    flexShrink: 0,
    flexWrap: "wrap",
  };

  const row: CSSProperties = {
    display: "flex",
    flex: 1,
    minHeight: 0,
    minWidth: 0,
  };

  const showChatList = wide || !selectedId;
  const showThread = wide || !!selectedId;

  const sidebar: CSSProperties = {
    width: wide ? 300 : "100%",
    maxWidth: "100%",
    borderRight: wide ? "1px solid var(--border)" : "none",
    display: showChatList ? "flex" : "none",
    flexDirection: "column",
    background: "var(--bg-muted)",
    minHeight: 0,
  };

  const thread: CSSProperties = {
    flex: 1,
    display: showThread ? "flex" : "none",
    flexDirection: "column",
    minWidth: 0,
    background: "var(--bg)",
    minHeight: 0,
  };

  return (
    <div style={shell}>
      <header style={topBar}>
        {!wide && selectedId ? (
          <button
            type="button"
            className="ui-btn ui-btn--ghost"
            aria-label="Назад к списку"
            onClick={() => {
              setSelectedId(null);
              setSelectedChatData(null);
            }}
          >
            <IconChevronLeft />
          </button>
        ) : null}
        <IconChat size={22} title="" />
        <strong style={{ flex: 1, fontSize: "1.02rem", minWidth: 120 }}>
          {SERVICE_DISPLAY_NAME}
        </strong>
        <span
          style={{
            color: "var(--text-muted)",
            fontSize: "0.85rem",
            maxWidth: 140,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          <IconUser size={16} /> {currentUser.username}
        </span>
        <button
          type="button"
          className="ui-btn ui-btn--ghost"
          onClick={() => setMenuOpen(true)}
          aria-label="Меню"
        >
          <IconMenu />
        </button>
        <ThemeSwitcher />
        <button type="button" className="ui-btn ui-btn--ghost" onClick={onLogout}>
          <IconLogout size={18} /> {wide ? "Выйти" : ""}
        </button>
      </header>

      <div style={row}>
        <aside style={sidebar}>
          <div style={{ padding: 10, display: "flex", gap: 8 }}>
            <button
              type="button"
              className="ui-btn ui-btn--primary"
              style={{ flex: 1 }}
              onClick={() => setComposeOpen(true)}
            >
              <IconPlus size={18} /> Новый
            </button>
          </div>
          <div
            style={{ flex: 1, overflowY: "auto", padding: 8 }}
            onScroll={(e) => {
              const el = e.currentTarget;
              if (el.scrollTop + el.clientHeight >= el.scrollHeight - 32)
                void loadMoreChats();
            }}
          >
            {loadingChats && chats.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>Загрузка…</p>
            ) : null}
            {sortedChats.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => {
                  setSelectedId(c.id);
                  setSelectedChatData(c);
                  setCommentRoot(null);
                  setEditing(null);
                  setReplyTo(null);
                  setDraft("");
                  setFiles([]);
                  setSearchMode(false);
                  setSearchHitsChat([]);
                  searchChatPageRef.current = 0;
                  setSearchChatDone(false);
                }}
                style={{
                  display: "flex",
                  gap: 10,
                  width: "100%",
                  textAlign: "left",
                  padding: 10,
                  marginBottom: 8,
                  borderRadius: 12,
                  border:
                    selectedId === c.id
                      ? "2px solid var(--accent)"
                      : "1px solid var(--border)",
                  background:
                    selectedId === c.id ? "var(--bg-elevated)" : "var(--bg)",
                  cursor: "pointer",
                  color: "inherit",
                  alignItems: "center",
                }}
              >
                <Avatar src={chatAvatarSrc(c)} label={chatLabel(c)} size={48} />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700 }}>{chatLabel(c)}</div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                    {kindLabel(c.chat_kind)}
                  </div>
                  {c.last_message ? (
                    <div
                      style={{
                        fontSize: "0.8rem",
                        color: "var(--text-muted)",
                        marginTop: 6,
                        minWidth: 0,
                      }}
                    >
                      {c.last_message.sender_user_id != null ? (
                        <div
                          style={{
                            fontWeight: 600,
                            marginBottom: 2,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {displayName(c.last_message.sender_user_id)}
                        </div>
                      ) : null}
                      <div
                        style={{
                          overflow: "hidden",
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                          wordBreak: "break-word",
                        }}
                      >
                        {(c.last_message.message_text ?? "").trim() ||
                          "Вложение"}
                      </div>
                    </div>
                  ) : null}
                </div>
              </button>
            ))}
          </div>
        </aside>

        <section style={thread}>
          {!selectedChat ? (
            <div
              style={{
                flex: 1,
                display: "grid",
                placeItems: "center",
                color: "var(--text-muted)",
              }}
            >
              Выберите чат
            </div>
          ) : (
            <>
              <div
                style={{
                  padding: "10px 12px",
                  borderBottom: "1px solid var(--border)",
                  background: "var(--bg-elevated)",
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 10,
                  alignItems: "center",
                  width: "100%",
                  boxSizing: "border-box",
                }}
              >
                {!wide && selectedChat.chat_kind !== "PROFILE" ? (
                  <button
                    type="button"
                    className="ui-btn ui-btn--ghost"
                    onClick={() => setInfoOpen(true)}
                  >
                    Инфо
                  </button>
                ) : null}
                <Avatar src={chatAvatarSrc(selectedChat)} label={chatLabel(selectedChat)} size={44} />
                <div
                  style={{
                    flex: "0 1 auto",
                    minWidth: 0,
                    maxWidth: "min(240px, 38vw)",
                  }}
                >
                  <div style={{ fontWeight: 800 }}>{chatLabel(selectedChat)}</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {kindLabel(selectedChat.chat_kind)}
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    flex: "1 1 160px",
                    minWidth: 0,
                    alignItems: "center",
                  }}
                >
                  <input
                    className="ui-input"
                    placeholder="Поиск в чате…"
                    value={hdrSearch}
                    onChange={(e) => setHdrSearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void runHdrSearch();
                    }}
                    style={{ flex: 1, minWidth: 0, width: "100%" }}
                  />
                  <button
                    type="button"
                    className="ui-btn ui-btn--primary"
                    style={{ flexShrink: 0 }}
                    onClick={() => void runHdrSearch()}
                    aria-label="Искать в чате"
                  >
                    <IconSearch size={18} />
                  </button>
                </div>
              </div>

              {commentRoot ? (
                <div
                  style={{
                    padding: "8px 12px",
                    borderBottom: "1px solid var(--border)",
                    background: "var(--bg-muted)",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <button
                    type="button"
                    className="ui-btn ui-btn--ghost"
                    onClick={() => setCommentRoot(null)}
                  >
                    <IconChevronLeft /> К корню чата
                  </button>
                </div>
              ) : null}

              {commentRoot ? (
                <div style={{ padding: 12, borderBottom: "1px solid var(--border)" }}>
                  <MessageBubble
                    m={commentRoot}
                    chatId={selectedChat.id}
                    currentUserId={currentUser.id}
                    displaySender={displayName(commentRoot.sender_user_id)}
                    replySnippet={null}
                    replySenderLabel={null}
                    interactive={false}
                    avatarEpoch={assetEpoch}
                  />
                </div>
              ) : null}

              {searchMode ? (
                <div
                  style={{
                    padding: "8px 12px",
                    borderBottom: "1px solid var(--border)",
                    background: "var(--bg-muted)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 8,
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                    Режим поиска: показаны только совпадения
                  </span>
                  <button
                    type="button"
                    className="ui-btn ui-btn--ghost"
                    onClick={() => {
                      setSearchMode(false);
                      setSearchHitsChat([]);
                      searchChatPageRef.current = 0;
                      setSearchChatDone(false);
                      void loadMessages(true);
                    }}
                  >
                    Сбросить
                  </button>
                </div>
              ) : null}

              <div
                style={{
                  flex: 1,
                  overflowY: "auto",
                  padding: 12,
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                }}
                onScroll={(e) => {
                  const el = e.currentTarget;
                  if (el.scrollTop < 60 && selectedChat) {
                    if (searchMode) {
                      if (!loadingSearchChat && !searchChatDone)
                        void loadMoreSearchChat();
                    } else if (!loadingMsg && !msgDone) {
                      void loadMessages(false);
                    }
                  }
                }}
              >
                {searchMode && loadingSearchChat && searchHitsChat.length === 0 ? (
                  <span style={{ color: "var(--text-muted)" }}>Поиск…</span>
                ) : null}
                {!searchMode && loadingMsg && messages.length === 0 ? (
                  <span style={{ color: "var(--text-muted)" }}>Загрузка…</span>
                ) : null}
                {(searchMode ? searchHitsChat : messages).map((m) => {
                  const rm = m.reply_message_id
                    ? replyCache[m.reply_message_id]
                    : undefined;
                  return (
                    <MessageBubble
                      key={m.id}
                      m={m}
                      chatId={selectedChat.id}
                      currentUserId={currentUser.id}
                      displaySender={displayName(m.sender_user_id)}
                      replySnippet={rm?.message_text ?? null}
                      replySenderLabel={
                        rm ? displayName(rm.sender_user_id) : null
                      }
                      onReply={() => {
                        setReplyTo(m);
                        setEditing(null);
                      }}
                      onEdit={
                        m.sender_user_id === currentUser.id
                          ? () => {
                              setEditing(m);
                              setDraft(m.message_text ?? "");
                              setReplyTo(null);
                              setFiles([]);
                            }
                          : undefined
                      }
                      onDelete={
                        canDeleteMessage(m)
                          ? () => void handleDelete(m)
                          : undefined
                      }
                      onOpenComments={
                        canCommentBtn && !m.parent_message_id
                          ? () => setCommentRoot(m)
                          : undefined
                      }
                      canOpenComments={!!canCommentBtn && !m.parent_message_id}
                      showReadReceipt={
                        m.sender_user_id === currentUser.id &&
                        !commentRoot &&
                        (selectedChat.chat_kind === "GROUP" ||
                          selectedChat.chat_kind === "PRIVATE")
                      }
                      readLabel={
                        m.is_read === true
                          ? "Прочитано"
                          : m.is_read === false
                            ? "Доставлено"
                            : ""
                      }
                      avatarEpoch={assetEpoch}
                    />
                  );
                })}
              </div>

              <div
                style={{
                  padding: 12,
                  borderTop: "1px solid var(--border)",
                  background: "var(--bg-elevated)",
                }}
              >
                {canPostHere ? (
                  <>
                    {replyTo ? (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 8,
                          marginBottom: 8,
                          fontSize: "0.85rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        <div style={{ flex: 1 }}>
                          <strong>
                            {displayName(replyTo.sender_user_id)}
                          </strong>
                          : {(replyTo.message_text ?? "").slice(0, 100)}
                        </div>
                        <button
                          type="button"
                          aria-label="Отменить ответ"
                          onClick={() => setReplyTo(null)}
                          style={{
                            border: "none",
                            background: "var(--bg-muted)",
                            borderRadius: "50%",
                            width: 32,
                            height: 32,
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          <IconX size={18} />
                        </button>
                      </div>
                    ) : null}
                    {editing ? (
                      <div style={{ marginBottom: 8, fontSize: "0.85rem" }}>
                        Редактирование{" "}
                        <button
                          type="button"
                          className="ui-btn ui-btn--ghost"
                          onClick={() => {
                            setEditing(null);
                            setDraft("");
                          }}
                        >
                          Отмена
                        </button>
                      </div>
                    ) : null}
                    <PickedFilesStrip
                      files={files}
                      onRemove={(i) => {
                        setFiles((prev) => prev.filter((_, j) => j !== i));
                        if (fileInputRef.current) fileInputRef.current.value = "";
                      }}
                    />
                    <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                      {!editing ? (
                        <label
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            width: 44,
                            height: 44,
                            borderRadius: "50%",
                            border: "1px solid var(--border)",
                            cursor: "pointer",
                            background: "var(--bg)",
                          }}
                        >
                          <IconPaperclip />
                          <input
                            ref={fileInputRef}
                            type="file"
                            multiple
                            className="sr-only"
                            onClick={(e) => {
                              (e.currentTarget as HTMLInputElement).value = "";
                            }}
                            onChange={(e) => {
                              const fl = e.target.files;
                              if (fl?.length)
                                setFiles((prev) => [...prev, ...Array.from(fl)]);
                              e.target.value = "";
                            }}
                          />
                        </label>
                      ) : null}
                      <textarea
                        className="ui-textarea"
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        placeholder="Сообщение…"
                        rows={2}
                        style={{ flex: 1, minHeight: 48 }}
                      />
                      <button
                        type="button"
                        className="ui-btn ui-btn--primary"
                        style={{ borderRadius: "50%", width: 48, height: 48, padding: 0 }}
                        onClick={() =>
                          editing ? void handleSaveEdit() : void handleSend()
                        }
                      >
                        <IconSend />
                      </button>
                    </div>
                  </>
                ) : (
                  <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.9rem" }}>
                    У вас нет прав писать в корне этого чата.
                  </p>
                )}
              </div>
            </>
          )}
        </section>

        {wide && selectedChat && selectedChat.chat_kind !== "PROFILE" ? (
          <div style={{ display: "flex", minHeight: 0 }}>
            <ChatInfoPanel
              chat={selectedChat}
              currentUserId={currentUser.id}
              onClose={() => {}}
              onRefreshChats={async () => {
                await refreshChats();
                bumpAssets();
              }}
              onOpenProfile={(id) => setProfileUserId(id)}
              assetEpoch={assetEpoch}
            />
          </div>
        ) : null}
      </div>

      {composeOpen ? (
        <ModalChrome title="Новый чат" onClose={() => setComposeOpen(false)} narrow>
          <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
            {(
              [
                ["private", "Личный"],
                ["group", "Группа"],
                ["channel", "Канал"],
              ] as const
            ).map(([k, lab]) => (
              <button
                key={k}
                type="button"
                className={composeTab === k ? "ui-btn ui-btn--primary" : "ui-btn ui-btn--ghost"}
                onClick={() => setComposeTab(k)}
              >
                {lab}
              </button>
            ))}
          </div>
          {composeTab === "private" ? (
            <>
              <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                <label style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4 }}>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Username</span>
                  <input
                    className="ui-input"
                    value={usernameQuery}
                    onChange={(e) => setUsernameQuery(e.target.value)}
                  />
                </label>
                <button
                  type="button"
                  className="ui-btn ui-btn--primary"
                  onClick={() => void searchUsersCompose()}
                >
                  <IconSearch />
                </button>
              </div>
              {searchHits.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  className="ui-btn ui-btn--ghost"
                  style={{
                    width: "100%",
                    marginTop: 8,
                    justifyContent: "flex-start",
                  }}
                  onClick={() => void createPrivate(u.id)}
                >
                  <Avatar
                    src={userAvatarUrl(u.id, assetEpoch)}
                    label={avatarLetterFromUser(u)}
                    size={36}
                  />
                  <span style={{ marginLeft: 8 }}>{userListLabel(u)}</span>
                </button>
              ))}
            </>
          ) : (
            <>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Название</span>
                <input
                  className="ui-input"
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="ui-btn ui-btn--primary"
                style={{ width: "100%" }}
                onClick={() =>
                  void createGroupOrChannel(composeTab === "group" ? "group" : "channel")
                }
              >
                Создать
              </button>
            </>
          )}
        </ModalChrome>
      ) : null}

      {menuOpen ? (
        <MainAppMenu
          currentUser={currentUser}
          assetEpoch={assetEpoch}
          onClose={() => setMenuOpen(false)}
          onOpenProfile={(id) => setProfileUserId(id)}
          onOpenChat={(id, options) => {
            setMenuOpen(false);
            void openChatById(id, options);
          }}
          onRefreshUser={async () => {
            try {
              const me = await apiJson<CurrentUser>("/users/me");
              setCurrentUser(me);
              bumpAssets();
            } catch {
              /* ignore */
            }
          }}
          onMediaInvalidate={bumpAssets}
        />
      ) : null}

      {profileUserId != null ? (
        <UserProfileModal
          userId={profileUserId}
          currentUser={currentUser}
          assetEpoch={assetEpoch}
          onClose={() => setProfileUserId(null)}
          onOpenChat={(id, options) => {
            void openChatById(id, options);
          }}
        />
      ) : null}

      {!wide && infoOpen && selectedChat && selectedChat.chat_kind !== "PROFILE" ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 150,
            background: "var(--bg)",
            display: "flex",
            flexDirection: "column",
            height: "100dvh",
            width: "100%",
            overflow: "hidden",
          }}
        >
          <div style={{ padding: 8, flexShrink: 0 }}>
            <button
              type="button"
              className="ui-btn ui-btn--ghost"
              onClick={() => setInfoOpen(false)}
            >
              <IconX /> Закрыть панель
            </button>
          </div>
          <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
            <ChatInfoPanel
              variant="sheet"
              chat={selectedChat}
              currentUserId={currentUser.id}
              onClose={() => setInfoOpen(false)}
              onRefreshChats={async () => {
                await refreshChats();
                bumpAssets();
                setInfoOpen(false);
              }}
              onOpenProfile={(id) => {
                setInfoOpen(false);
                setProfileUserId(id);
              }}
              assetEpoch={assetEpoch}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
