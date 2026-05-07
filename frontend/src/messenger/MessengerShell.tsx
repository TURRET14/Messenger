import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { ApiError, apiFetch, apiJson, apiUpload, type UploadProgress } from "../api/client";
import type {
  Chat,
  ChatRole,
  CurrentUser,
  Message,
  MessageReadMark,
  UserInList,
} from "../api/types";
import { fetchUser, primeUser } from "../api/userCache";
import { SERVICE_DISPLAY_NAME } from "../config";
import {
  IconChat,
  IconChevronDown,
  IconChevronLeft,
  IconHash,
  IconInfo,
  IconLogout,
  IconMenu,
  IconPaperclip,
  IconPlus,
  IconSearch,
  IconSend,
  IconUser,
  IconUsers,
  IconX,
} from "../components/Icons";
import { Avatar, chatAvatarUrl, userAvatarUrl } from "../components/ui/Avatar";
import { ModalChrome } from "../components/ui/ModalChrome";
import { ValidationError } from "../components/ui/ValidationError";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useDialogs } from "../context/DialogsContext";
import { useBackendSocket } from "../hooks/useBackendSocket";
import {
  validateAttachmentFiles,
  validateChatName,
  validateMessageForSend,
  validateMessageSearch,
  validateUsernameSearch,
} from "../validation";
import { ChatInfoPanel, type MembershipRow } from "./ChatInfoPanel";
import { MainAppMenu } from "./MainAppMenu";
import {
  type AttachmentMeta,
  MessageBubble,
  PickedFilesStrip,
  type PickedFileItem,
} from "./MessageBubble";
import { useMsgWebSocket } from "./useMsgWebSocket";
import { chatKindLabel } from "./labels";
import { avatarLetterFromUser, userListLabel } from "./userFormat";
import { UserProfileModal } from "./UserProfileModal";

const PAGE = 50;

function chatLabel(c: Chat): string {
  if (c.chat_kind === "PROFILE") return c.name || "Профиль";
  if (c.chat_kind === "PRIVATE") return c.name || "Личный чат";
  return c.name || "Чат";
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

async function fetchMyRole(chatId: number): Promise<ChatRole | null> {
  // Один запрос вместо постраничного перебора всех memberships.
  // Бэкенд вернёт 404 (CHAT_MEMBERSHIP_NOT_FOUND_ERROR) если пользователь не участник.
  try {
    const m = await apiJson<MembershipRow>(
      `/chats/id/${chatId}/memberships/me`,
    );
    return m.chat_role;
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
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

  const handleLogout = async () => {
    if (!(await confirm({ message: "Выйти из аккаунта?", confirmLabel: "Выйти" }))) return;
    onLogout();
  };

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
  const refreshChatsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedChatData, setSelectedChatData] = useState<Chat | null>(null);
  const [myRole, setMyRole] = useState<ChatRole | null>(null);

  const [commentRoot, setCommentRoot] = useState<Message | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const msgPageRef = useRef(0);
  const [msgDone, setMsgDone] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState(false);

  const [draft, setDraft] = useState("");
  const [pickedFiles, setPickedFiles] = useState<PickedFileItem[]>([]);
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
  const [newChatError, setNewChatError] = useState<string | null>(null);

  const [hdrSearch, setHdrSearch] = useState("");
  const [searchHitsChat, setSearchHitsChat] = useState<Message[]>([]);
  const [chatSearchError, setChatSearchError] = useState<string | null>(null);
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
  const composeTextareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesScrollRef = useRef<HTMLDivElement>(null);
  const messagesBottomRef = useRef<HTMLDivElement>(null);
  const shouldScrollToBottomRef = useRef(false);
  const prependScrollRestoreRef = useRef<{
    scrollHeight: number;
    scrollTop: number;
  } | null>(null);
  const detachedSelectionRef = useRef(false);
  const readAllInFlightRef = useRef(false);
  const [fileInputKey, setFileInputKey] = useState(0);
  const nextPickedFileIdRef = useRef(1);
  const [privatePeerByChat, setPrivatePeerByChat] = useState<Record<number, number>>({});
  const [composeError, setComposeError] = useState<string | null>(null);
  const [showJumpToBottom, setShowJumpToBottom] = useState(false);

  /** Прогресс отправки вложений (null когда идёт загрузка без вложений или ничего не отправляется). */
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  /** Контроллер для отмены текущей загрузки вложений по кнопке. */
  const uploadAbortRef = useRef<AbortController | null>(null);

  const replyInflightRef = useRef(new Set<number>());

  // Авто-расширение поля ввода сообщения по содержимому до разумного предела
  useLayoutEffect(() => {
    const el = composeTextareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const maxHeight = 240;
    const minHeight = 60;
    const next = Math.min(maxHeight, Math.max(minHeight, el.scrollHeight));
    el.style.height = `${next}px`;
  }, [draft, editing?.id, replyTo?.id]);

  const ensureName = useCallback(async (uid: number) => {
    if (userNamesRef.current[uid]) return;
    if (nameInflightRef.current.has(uid)) return;
    nameInflightRef.current.add(uid);
    try {
      // fetchUser автоматически батчит несколько одновременных запросов
      // в один POST /users/by-ids — N запросов превращаются в 1.
      const u = await fetchUser(uid);
      const label = u ? userListLabel(u) : `#${uid}`;
      setUserNames((p) => (p[uid] ? p : { ...p, [uid]: label }));
    } finally {
      nameInflightRef.current.delete(uid);
    }
  }, []);

  const resetAttachmentInput = useCallback(() => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    setFileInputKey((prev) => prev + 1);
  }, []);

  const clearPickedFiles = useCallback(() => {
    setPickedFiles([]);
    resetAttachmentInput();
  }, [resetAttachmentInput]);

  const clearThreadSelection = useCallback(() => {
    detachedSelectionRef.current = false;
    setSelectedId(null);
    setSelectedChatData(null);
    setCommentRoot(null);
    setMessages([]);
    setSearchMode(false);
    setSearchHitsChat([]);
    searchChatPageRef.current = 0;
    setSearchChatDone(false);
    setReplyTo(null);
    setEditing(null);
    setDraft("");
    setComposeError(null);
    setProfileUserId(null);
    setMyRole(null);
    clearPickedFiles();
  }, [clearPickedFiles]);

  const updateJumpToBottomVisibility = useCallback(() => {
    const el = messagesScrollRef.current;
    if (!el) {
      setShowJumpToBottom(false);
      return;
    }
    const distanceFromBottom = el.scrollHeight - el.clientHeight - el.scrollTop;
    setShowJumpToBottom(distanceFromBottom > 160);
  }, []);

  const isNearMessagesBottom = useCallback(() => {
    const el = messagesScrollRef.current;
    if (!el) return true;
    return el.scrollHeight - el.clientHeight - el.scrollTop < 120;
  }, []);

  const scrollMessagesToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const el = messagesScrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
    messagesBottomRef.current?.scrollIntoView({ block: "end", behavior });
    window.requestAnimationFrame(updateJumpToBottomVisibility);
  }, [updateJumpToBottomVisibility]);

  const forceScrollMessagesToBottom = useCallback(() => {
    const run = () => scrollMessagesToBottom("auto");
    run();
    window.requestAnimationFrame(() => {
      run();
      window.requestAnimationFrame(run);
    });
    window.setTimeout(run, 80);
    window.setTimeout(run, 180);
    window.setTimeout(run, 360);
  }, [scrollMessagesToBottom]);

  const appendPickedFiles = useCallback(
    (picked: FileList | null) => {
      if (!picked?.length) {
        resetAttachmentInput();
        return;
      }
      const validationError = validateAttachmentFiles(picked);
      if (validationError) {
        setComposeError(validationError);
        resetAttachmentInput();
        return;
      }
      const nextItems = Array.from(picked, (file) => ({
        id: nextPickedFileIdRef.current++,
        file,
      }));
      setComposeError(null);
      setPickedFiles((prev) => [...prev, ...nextItems]);
      resetAttachmentInput();
    },
    [resetAttachmentInput],
  );

  const openAttachmentPicker = useCallback(() => {
    const input = fileInputRef.current;
    if (!input) return;
    input.value = "";
    input.click();
  }, []);

  const refreshChats = useCallback(async () => {
    if (chatLoadRef.current) return;
    chatLoadRef.current = true;
    setLoadingChats(true);
    try {
      const targetPages = chatPageRef.current + 1;
      const merged: Chat[] = [];
      let nextDone = false;
      let lastLoadedPage = 0;

      for (let mult = 0; mult < targetPages; mult += 1) {
        const batch = await apiJson<Chat[]>(`/chats?offset_multiplier=${mult}`);
        lastLoadedPage = mult;
        const ids = new Set(merged.map((item) => item.id));
        merged.push(...batch.filter((item) => !ids.has(item.id)));
        for (const c of batch) {
          const lm = c.last_message;
          if (lm?.sender_user_id != null) void ensureName(lm.sender_user_id);
        }
        if (batch.length < PAGE) {
          nextDone = true;
          break;
        }
      }
      chatPageRef.current = lastLoadedPage;
      setChats(merged);
      setChatsDone(nextDone);
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

  useEffect(() => {
    return () => {
      if (refreshChatsTimerRef.current) {
        clearTimeout(refreshChatsTimerRef.current);
      }
    };
  }, []);

  const scheduleRefreshChats = useCallback(() => {
    if (refreshChatsTimerRef.current) return;
    refreshChatsTimerRef.current = setTimeout(() => {
      refreshChatsTimerRef.current = null;
      void refreshChats();
    }, 120);
  }, [refreshChats]);

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
        detachedSelectionRef.current = !!options?.ephemeral;
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
      // Пытаемся взять peer прямо из загруженного объекта чата —
      // backend теперь отдаёт peer_user_id для PRIVATE-чатов.
      const fromList = chats.find((c) => c.id === chatId);
      const fromSelected = selectedChatData?.id === chatId ? selectedChatData : null;
      const peerFromChat = fromList?.peer_user_id ?? fromSelected?.peer_user_id ?? null;
      if (peerFromChat != null) {
        setPrivatePeerByChat((p) => ({ ...p, [chatId]: peerFromChat }));
        return peerFromChat;
      }
      // Fallback на старую логику — нужен только если чат был создан до того,
      // как стал доступен peer_user_id (для надёжности при WebSocket-обновлениях).
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
    [privatePeerByChat, currentUser.id, chats, selectedChatData],
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
    if (selectedId == null || detachedSelectionRef.current) return;
    if (chats.some((c) => c.id === selectedId)) return;
    clearThreadSelection();
  }, [selectedId, chats, clearThreadSelection]);

  useEffect(() => {
    for (const c of chats) {
      if (c.chat_kind === "PRIVATE") void ensurePrivatePeer(c.id);
    }
  }, [chats, ensurePrivatePeer]);

  useEffect(() => {
    if (selectedChatData?.chat_kind === "PRIVATE") {
      void ensurePrivatePeer(selectedChatData.id);
    }
  }, [selectedChatData?.id, selectedChatData?.chat_kind, ensurePrivatePeer]);

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
        const role = await fetchMyRole(selectedId);
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
      const scrollRestore =
        !reset && !searchModeRef.current && messagesScrollRef.current
          ? {
              scrollHeight: messagesScrollRef.current.scrollHeight,
              scrollTop: messagesScrollRef.current.scrollTop,
            }
          : null;
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
          prependScrollRestoreRef.current = null;
          shouldScrollToBottomRef.current = true;
          msgPageRef.current = 0;
          setMessages(reversed);
          setMsgDone(batch.length < PAGE);
        } else {
          prependScrollRestoreRef.current = scrollRestore;
          msgPageRef.current = mult;
          setMessages((prev) => [...reversed, ...prev]);
          if (batch.length < PAGE) setMsgDone(true);
        }
        for (const m of batch) {
          if (m.sender_user_id) void ensureName(m.sender_user_id);
          if (m.reply_message_id) {
            const rid = m.reply_message_id;
            if (replyCache[rid] || replyInflightRef.current.has(rid)) continue;
            replyInflightRef.current.add(rid);
            void (async () => {
              try {
                const rm = await apiJson<Message>(
                  `/chats/id/${selectedId}/messages/id/${rid}`,
                );
                setReplyCache((p) => (p[rm.id] ? p : { ...p, [rm.id]: rm }));
                if (rm.sender_user_id) void ensureName(rm.sender_user_id);
              } catch {
                /* skip */
              } finally {
                replyInflightRef.current.delete(rid);
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
    shouldScrollToBottomRef.current = true;
    void loadMessages(true);
  }, [selectedId, commentRoot?.id, loadMessages]);

  const reloadMsgs = () => {
    if (selectedId) {
      prependScrollRestoreRef.current = null;
      shouldScrollToBottomRef.current = true;
      void loadMessages(true);
    }
  };

  useLayoutEffect(() => {
    const restore = prependScrollRestoreRef.current;
    if (restore) {
      prependScrollRestoreRef.current = null;
      const el = messagesScrollRef.current;
      if (el) {
        el.scrollTop = restore.scrollTop + (el.scrollHeight - restore.scrollHeight);
      }
      updateJumpToBottomVisibility();
      return;
    }
    if (!shouldScrollToBottomRef.current) return;
    shouldScrollToBottomRef.current = false;
    forceScrollMessagesToBottom();
  }, [
    messages.length,
    searchHitsChat.length,
    selectedId,
    commentRoot?.id,
    forceScrollMessagesToBottom,
    updateJumpToBottomVisibility,
  ]);

  useLayoutEffect(() => {
    updateJumpToBottomVisibility();
  }, [selectedId, commentRoot?.id, searchMode, updateJumpToBottomVisibility]);

  useBackendSocket("/chats/post", true, scheduleRefreshChats);
  useBackendSocket("/chats/put", true, scheduleRefreshChats);
  useBackendSocket("/chats/delete", true, scheduleRefreshChats);
  useBackendSocket("/chats/messages/last", true, scheduleRefreshChats);

  const parentKey = commentRoot?.id ?? null;
  const onWsMsg = useCallback(
    (ev: MessageEvent) => {
      if (!selectedId || searchModeRef.current) return;
      try {
        const data = JSON.parse(ev.data as string) as Message;
        const p = data.parent_message_id ?? null;
        if (data.chat_id !== selectedId || p !== parentKey) return;
        if (data.sender_user_id === currentUser.id || isNearMessagesBottom()) {
          shouldScrollToBottomRef.current = true;
        }
        setMessages((prev) => mergeByIdAsc(prev, data));
        if (data.sender_user_id) void ensureName(data.sender_user_id);
      } catch {
        reloadMsgs();
      }
    },
    [selectedId, parentKey, currentUser.id, ensureName, isNearMessagesBottom],
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
    if (commentRoot) return;
    if (
      selectedChat.chat_kind !== "GROUP" &&
      selectedChat.chat_kind !== "PRIVATE"
    )
      return;
    const hasUnreadFromOthers = messages.some(
      (m) =>
        m.sender_user_id != null &&
        m.sender_user_id !== currentUser.id &&
        m.is_read !== true,
    );
    if (!hasUnreadFromOthers || readAllInFlightRef.current) return;
    readAllInFlightRef.current = true;
    void apiFetch(`/chats/id/${selectedId}/messages/read-all`, {
      method: "POST",
    })
      .then(() => {
        setMessages((prev) =>
          prev.map((m) =>
            m.sender_user_id != null && m.sender_user_id !== currentUser.id
              ? { ...m, is_read: true }
              : m,
          ),
        );
      })
      .finally(() => {
        readAllInFlightRef.current = false;
      });
  }, [messages, selectedChat, selectedId, currentUser.id, searchMode, commentRoot]);

  const displayName = (uid: number | null) => {
    if (uid == null) return "Система";
    if (uid === currentUser.id) return "Вы";
    return userNames[uid] ?? `…${uid}`;
  };

  const handleSend = async () => {
    if (!selectedId) return;
    const text = draft.trim();
    const validationError = validateMessageForSend(text, pickedFiles.length > 0);
    if (validationError) {
      setComposeError(validationError);
      return;
    }
    setComposeError(null);
    const fd = new FormData();
    fd.append("message_text", text);
    if (replyTo) fd.append("reply_message_id", String(replyTo.id));
    if (commentRoot) fd.append("parent_message_id", String(commentRoot.id));
    for (const item of pickedFiles) {
      fd.append("file_attachments_list", item.file, item.file.name);
    }
    const hasFiles = pickedFiles.length > 0;
    try {
      if (hasFiles) {
        // С вложениями шлём через XHR для отображения прогресса и поддержки отмены.
        const ctrl = new AbortController();
        uploadAbortRef.current = ctrl;
        setUploadProgress({ loaded: 0, total: 0 });
        try {
          await apiUpload(`/chats/id/${selectedId}/messages`, fd, {
            onProgress: (p) => setUploadProgress(p),
            signal: ctrl.signal,
          });
        } finally {
          uploadAbortRef.current = null;
          setUploadProgress(null);
        }
      } else {
        await apiFetch(`/chats/id/${selectedId}/messages`, {
          method: "POST",
          body: fd,
        });
      }
      setDraft("");
      clearPickedFiles();
      setReplyTo(null);
      shouldScrollToBottomRef.current = true;
      reloadMsgs();
    } catch (e) {
      // Отмена пользователем — не считаем за ошибку и не показываем алерт.
      if (e instanceof DOMException && e.name === "AbortError") return;
      void alert(e instanceof ApiError ? e.message : "Не отправлено");
    }
  };

  /** Прерывает текущую загрузку вложения. Если загрузка не идёт — no-op. */
  const cancelUpload = () => {
    uploadAbortRef.current?.abort();
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
    const nextText = draft.trim();
    if (!nextText) {
      try {
        const attachments = await apiJson<AttachmentMeta[]>(
          `/chats/id/${selectedId}/messages/id/${editing.id}/attachments`,
        );
        const validationError = validateMessageForSend(
          nextText,
          attachments.length > 0,
        );
        if (validationError) {
          setComposeError(validationError);
          return;
        }
      } catch (e) {
        void alert(
          e instanceof ApiError ? e.message : "Не удалось проверить вложения",
        );
        return;
      }
    }
    setComposeError(null);
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
      setChatSearchError(null);
      setSearchMode(false);
      setSearchHitsChat([]);
      searchChatPageRef.current = 0;
      setSearchChatDone(false);
      void loadMessages(true);
      return;
    }
    const validationError = validateMessageSearch(q, "Поиск по чату");
    if (validationError) {
      setChatSearchError(validationError);
      return;
    }
    setChatSearchError(null);
    setLoadingSearchChat(true);
    try {
      prependScrollRestoreRef.current = null;
      const enc = encodeURIComponent(q);
      const path = commentRoot
        ? `/chats/id/${selectedId}/messages/id/${commentRoot.id}/comments/search?message_text=${enc}&offset_multiplier=0`
        : `/chats/id/${selectedId}/messages/search?message_text=${enc}&offset_multiplier=0`;
      const batch = await apiJson<Message[]>(path);
      const reversed = [...batch].reverse();
      shouldScrollToBottomRef.current = true;
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
    const scrollRestore = messagesScrollRef.current
      ? {
          scrollHeight: messagesScrollRef.current.scrollHeight,
          scrollTop: messagesScrollRef.current.scrollTop,
        }
      : null;
    try {
      const mult = searchChatPageRef.current + 1;
      const enc = encodeURIComponent(q);
      const path = commentRoot
        ? `/chats/id/${selectedId}/messages/id/${commentRoot.id}/comments/search?message_text=${enc}&offset_multiplier=${mult}`
        : `/chats/id/${selectedId}/messages/search?message_text=${enc}&offset_multiplier=${mult}`;
      const batch = await apiJson<Message[]>(path);
      searchChatPageRef.current = mult;
      const reversed = [...batch].reverse();
      prependScrollRestoreRef.current = scrollRestore;
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
    const validationError = validateUsernameSearch(q);
    if (validationError) {
      setNewChatError(validationError);
      return;
    }
    setNewChatError(null);
    try {
      const hits = await apiJson<UserInList[]>(
        `/users/search/by-username?username=${encodeURIComponent(q)}&offset_multiplier=0`,
      );
      // Кешируем найденных пользователей, чтобы ensureName не делал лишних запросов.
      hits.forEach(primeUser);
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
    const validationError = validateChatName(name);
    if (validationError) {
      setNewChatError(validationError);
      return;
    }
    setNewChatError(null);
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

  /* ============================ Layout ============================ */

  const shell: CSSProperties = {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    overflow: "hidden",
    background: "var(--bg)",
  };

  const topBar: CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 14px",
    borderBottom: "1px solid var(--border)",
    background: "var(--bg-elevated)",
    flexShrink: 0,
    minHeight: 56,
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
    width: wide ? 320 : "100%",
    maxWidth: "100%",
    borderRight: wide ? "1px solid var(--border)" : "none",
    display: showChatList ? "flex" : "none",
    flexDirection: "column",
    background: "var(--bg-elevated)",
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
            className="ui-icon-btn"
            aria-label="Назад к списку чатов"
            title="Назад"
            onClick={clearThreadSelection}
          >
            <IconChevronLeft />
          </button>
        ) : null}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            color: "var(--accent)",
          }}
        >
          <IconChat size={22} />
        </div>
        <strong style={{ fontSize: "1.02rem", whiteSpace: "nowrap" }}>
          {SERVICE_DISPLAY_NAME}
        </strong>
        <span style={{ flex: 1 }} />
        <span
          style={{
            color: "var(--text-muted)",
            fontSize: "0.85rem",
            display: wide ? "inline-flex" : "none",
            alignItems: "center",
            gap: 6,
            maxWidth: 200,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          <IconUser size={16} />
          {currentUser.username}
        </span>
        <ThemeSwitcher />
        <button
          type="button"
          className="ui-icon-btn"
          onClick={() => setMenuOpen(true)}
          aria-label="Меню"
          title="Меню"
        >
          <IconMenu />
        </button>
        <button
          type="button"
          className="ui-icon-btn ui-icon-btn--danger"
          onClick={() => void handleLogout()}
          aria-label="Выйти"
          title="Выйти"
        >
          <IconLogout size={18} />
        </button>
      </header>

      <div style={row}>
        <aside style={sidebar}>
          <div style={{ padding: 10, flexShrink: 0 }}>
            <button
              type="button"
              className="ui-btn ui-btn--primary ui-btn--block"
              onClick={() => setComposeOpen(true)}
            >
              <IconPlus size={18} />
              Новый чат
            </button>
          </div>
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "0 10px 10px",
              display: "flex",
              flexDirection: "column",
              gap: 6,
              minHeight: 0,
            }}
            onScroll={(e) => {
              const el = e.currentTarget;
              if (el.scrollTop + el.clientHeight >= el.scrollHeight - 32)
                void loadMoreChats();
            }}
          >
            {loadingChats && chats.length === 0 ? (
              <div style={{ padding: 12, color: "var(--text-muted)" }}>
                <span className="ui-spinner" aria-hidden="true" /> Загружаем чаты…
              </div>
            ) : null}
            {sortedChats.map((c) => {
              const selected = selectedId === c.id;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => {
                    detachedSelectionRef.current = false;
                    setSelectedId(c.id);
                    setSelectedChatData(c);
                    setCommentRoot(null);
                    setEditing(null);
                    setReplyTo(null);
                    setDraft("");
                    clearPickedFiles();
                    setSearchMode(false);
                    setSearchHitsChat([]);
                    searchChatPageRef.current = 0;
                    setSearchChatDone(false);
                  }}
                  className={selected ? "ui-row ui-row--selected" : "ui-row ui-row--button"}
                  style={{
                    padding: 10,
                    gap: 12,
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <Avatar src={chatAvatarSrc(c)} label={chatLabel(c)} size={48} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div
                      style={{
                        fontWeight: 700,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {chatLabel(c)}
                    </div>
                    <div
                      style={{
                        fontSize: "0.72rem",
                        color: "var(--text-subtle)",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      {kindIcon(c.chat_kind)}
                      {chatKindLabel(c.chat_kind)}
                    </div>
                    {c.last_message ? (
                      <div
                        style={{
                          fontSize: "0.8rem",
                          color: "var(--text-muted)",
                          marginTop: 4,
                          minWidth: 0,
                          maxWidth: "100%",
                          display: "flex",
                          flexDirection: "column",
                        }}
                      >
                        {c.last_message.sender_user_id != null ? (
                          <div
                            style={{
                              fontWeight: 600,
                              color: "var(--text)",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                              maxWidth: "100%",
                            }}
                            title={displayName(c.last_message.sender_user_id)}
                          >
                            {displayName(c.last_message.sender_user_id)}
                          </div>
                        ) : null}
                        <div
                          style={{
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            maxWidth: "100%",
                          }}
                          title={
                            (c.last_message.message_text ?? "").trim() ||
                            "Вложение"
                          }
                        >
                          {((c.last_message.message_text ?? "").trim() ||
                            "Вложение").replace(/\s+/g, " ")}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </button>
              );
            })}
            {!loadingChats && sortedChats.length === 0 ? (
              <div
                style={{
                  padding: "32px 12px",
                  textAlign: "center",
                  color: "var(--text-muted)",
                  fontSize: "0.9rem",
                }}
              >
                У вас пока нет чатов. Нажмите «Новый чат», чтобы начать.
              </div>
            ) : null}
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
                padding: 24,
                textAlign: "center",
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <div
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: "50%",
                    background: "var(--bg-muted)",
                    display: "grid",
                    placeItems: "center",
                    color: "var(--text-subtle)",
                  }}
                >
                  <IconChat size={28} />
                </div>
                <div>Выберите чат, чтобы открыть переписку</div>
              </div>
            </div>
          ) : (
            <>
              <div
                style={{
                  padding: "10px 14px",
                  borderBottom: "1px solid var(--border)",
                  background: "var(--bg-elevated)",
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 10,
                  alignItems: "center",
                  width: "100%",
                  boxSizing: "border-box",
                  flexShrink: 0,
                }}
              >
                {!wide && selectedChat.chat_kind !== "PROFILE" ? (
                  <button
                    type="button"
                    className="ui-icon-btn"
                    onClick={() => setInfoOpen(true)}
                    aria-label="Информация о чате"
                    title="Информация о чате"
                  >
                    <IconInfo />
                  </button>
                ) : null}
                <Avatar
                  src={chatAvatarSrc(selectedChat)}
                  label={chatLabel(selectedChat)}
                  size={42}
                />
                <div
                  style={{
                    flex: "0 1 auto",
                    minWidth: 0,
                    maxWidth: "min(240px, 38vw)",
                  }}
                >
                  <div
                    style={{
                      fontWeight: 700,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {chatLabel(selectedChat)}
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
                    {kindIcon(selectedChat.chat_kind)}
                    {chatKindLabel(selectedChat.chat_kind)}
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 6,
                    flex: "1 1 160px",
                    minWidth: 0,
                    alignItems: "center",
                  }}
                >
                  <input
                    className="ui-input"
                    placeholder="Поиск в чате…"
                    value={hdrSearch}
                    enterKeyHint="search"
                    type="search"
                    onChange={(e) => {
                      setHdrSearch(e.target.value);
                      setChatSearchError(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        e.stopPropagation();
                        (e.currentTarget as HTMLInputElement).blur();
                        void runHdrSearch();
                      }
                    }}
                    style={{ flex: 1, minWidth: 0, width: "100%" }}
                  />
                  <button
                    type="button"
                    className="ui-icon-btn"
                    style={{ flexShrink: 0 }}
                    onClick={() => void runHdrSearch()}
                    aria-label="Искать в чате"
                    title="Искать в чате"
                  >
                    <IconSearch size={18} />
                  </button>
                </div>
              </div>

              {chatSearchError ? (
                <ValidationError
                  message={chatSearchError}
                  style={{ margin: "8px 12px 0", flexShrink: 0 }}
                />
              ) : null}

              {commentRoot ? (
                <div
                  style={{
                    padding: "8px 12px",
                    borderBottom: "1px solid var(--border)",
                    background: "var(--bg-muted)",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    flexShrink: 0,
                  }}
                >
                  <button
                    type="button"
                    className="ui-btn ui-btn--ghost ui-btn--sm"
                    onClick={() => setCommentRoot(null)}
                  >
                    <IconChevronLeft size={16} /> К корню чата
                  </button>
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
                    flexShrink: 0,
                  }}
                >
                  <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                    <IconSearch size={14} /> Режим поиска: показаны только совпадения
                  </span>
                  <button
                    type="button"
                    className="ui-btn ui-btn--ghost ui-btn--sm"
                    onClick={() => {
                      setSearchMode(false);
                      setSearchHitsChat([]);
                      searchChatPageRef.current = 0;
                      setSearchChatDone(false);
                      void loadMessages(true);
                    }}
                  >
                    <IconX size={14} /> Сбросить
                  </button>
                </div>
              ) : null}

              <div
                style={{
                  flex: 1,
                  minHeight: 0,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                <div
                  ref={messagesScrollRef}
                  style={{
                    height: "100%",
                    overflowY: "auto",
                    padding: 12,
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                  }}
                  onScroll={(e) => {
                    const el = e.currentTarget;
                    updateJumpToBottomVisibility();
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
                  {commentRoot ? (
                    <div
                      style={{
                        padding: "4px 0 8px",
                        borderBottom: "1px solid var(--border)",
                        marginBottom: 4,
                      }}
                    >
                      <MessageBubble
                        m={commentRoot}
                        chatId={selectedChat.id}
                        currentUserId={currentUser.id}
                        displaySender={displayName(commentRoot.sender_user_id)}
                        replySnippet={null}
                        replySenderLabel={null}
                        interactive={false}
                        avatarEpoch={assetEpoch}
                        onOpenAuthorProfile={(uid) => setProfileUserId(uid)}
                      />
                    </div>
                  ) : null}
                  {searchMode && loadingSearchChat && searchHitsChat.length === 0 ? (
                    <span style={{ color: "var(--text-muted)" }}>
                      <span className="ui-spinner" aria-hidden="true" /> Поиск…
                    </span>
                  ) : null}
                  {!searchMode && loadingMsg && messages.length === 0 ? (
                    <span style={{ color: "var(--text-muted)" }}>
                      <span className="ui-spinner" aria-hidden="true" /> Загрузка…
                    </span>
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
                                clearPickedFiles();
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
                        onOpenAuthorProfile={(uid) => setProfileUserId(uid)}
                      />
                    );
                  })}
                  <div ref={messagesBottomRef} style={{ height: 1, flexShrink: 0 }} />
                </div>
                <button
                  type="button"
                  className="ui-icon-btn ui-icon-btn--accent"
                  aria-label="Прокрутить вниз"
                  title="Прокрутить вниз"
                  onClick={() => scrollMessagesToBottom()}
                  style={{
                    position: "absolute",
                    right: 16,
                    bottom: 16,
                    width: 42,
                    height: 42,
                    opacity: showJumpToBottom ? 1 : 0,
                    pointerEvents: showJumpToBottom ? "auto" : "none",
                    transition: "opacity 160ms ease",
                    zIndex: 2,
                  }}
                >
                  <IconChevronDown size={22} />
                </button>
              </div>

              <div
                style={{
                  padding: 12,
                  borderTop: "1px solid var(--border)",
                  background: "var(--bg-elevated)",
                  flexShrink: 0,
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
                          padding: "6px 10px",
                          borderRadius: 10,
                          background: "var(--bg-muted)",
                          fontSize: "0.85rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        <div
                          style={{
                            flex: 1,
                            minWidth: 0,
                            borderLeft: "3px solid var(--accent)",
                            paddingLeft: 8,
                          }}
                        >
                          <div style={{ fontWeight: 600, color: "var(--text)" }}>
                            {displayName(replyTo.sender_user_id)}
                          </div>
                          <div
                            style={{
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {(replyTo.message_text ?? "").slice(0, 100) || "Вложение"}
                          </div>
                        </div>
                        <button
                          type="button"
                          aria-label="Отменить ответ"
                          title="Отменить ответ"
                          onClick={() => setReplyTo(null)}
                          className="ui-icon-btn ui-icon-btn--sm"
                        >
                          <IconX size={16} />
                        </button>
                      </div>
                    ) : null}
                    {editing ? (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 8,
                          marginBottom: 8,
                          fontSize: "0.85rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        <span>Редактирование сообщения</span>
                        <button
                          type="button"
                          className="ui-btn ui-btn--ghost ui-btn--sm"
                          onClick={() => {
                            setEditing(null);
                            setDraft("");
                            setComposeError(null);
                          }}
                        >
                          <IconX size={14} /> Отмена
                        </button>
                      </div>
                    ) : null}
                    <PickedFilesStrip
                      files={pickedFiles}
                      onRemove={(id) => {
                        setPickedFiles((prev) =>
                          prev.filter((item) => item.id !== id),
                        );
                        resetAttachmentInput();
                      }}
                    />
                    {uploadProgress ? (
                      <UploadProgressBar
                        progress={uploadProgress}
                        onCancel={cancelUpload}
                      />
                    ) : null}
                    <ValidationError message={composeError} />
                    <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                      {!editing ? (
                        <>
                          <input
                            key={fileInputKey}
                            ref={fileInputRef}
                            type="file"
                            multiple
                            className="sr-only"
                            onChange={(e) => appendPickedFiles(e.target.files)}
                          />
                          <button
                            type="button"
                            aria-label="Прикрепить файлы"
                            title="Прикрепить файлы"
                            onClick={openAttachmentPicker}
                            className="ui-icon-btn"
                            style={{ flexShrink: 0 }}
                            disabled={!!uploadProgress}
                          >
                            <IconPaperclip size={20} />
                          </button>
                        </>
                      ) : null}
                      <textarea
                        ref={composeTextareaRef}
                        className="ui-textarea"
                        value={draft}
                        onChange={(e) => {
                          setDraft(e.target.value);
                          setComposeError(null);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            if (editing) void handleSaveEdit();
                            else void handleSend();
                          }
                        }}
                        placeholder="Сообщение…"
                        rows={2}
                        disabled={!!uploadProgress}
                        style={{
                          flex: 1,
                          minHeight: 60,
                          maxHeight: 240,
                          resize: "vertical",
                          overflowY: "auto",
                          lineHeight: 1.4,
                        }}
                      />
                      <button
                        type="button"
                        className="ui-icon-btn ui-icon-btn--accent ui-icon-btn--lg"
                        onClick={() =>
                          editing ? void handleSaveEdit() : void handleSend()
                        }
                        title={editing ? "Сохранить" : "Отправить"}
                        aria-label={editing ? "Сохранить" : "Отправить"}
                        disabled={!!uploadProgress}
                      >
                        {uploadProgress ? (
                          <span className="ui-spinner" aria-hidden="true" />
                        ) : (
                          <IconSend size={20} />
                        )}
                      </button>
                    </div>
                  </>
                ) : (
                  <p
                    style={{
                      margin: 0,
                      color: "var(--text-muted)",
                      fontSize: "0.9rem",
                      textAlign: "center",
                      padding: "8px 0",
                    }}
                  >
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
              privatePeerId={privatePeerByChat[selectedChat.id] ?? null}
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
          <div
            style={{
              display: "flex",
              gap: 6,
              marginBottom: 16,
              flexWrap: "wrap",
            }}
          >
            {(
              [
                ["private", "Личный", <IconUser size={16} key="ico" />],
                ["group", "Группа", <IconUsers size={16} key="ico" />],
                ["channel", "Канал", <IconHash size={16} key="ico" />],
              ] as const
            ).map(([k, lab, ico]) => (
              <button
                key={k}
                type="button"
                className={
                  composeTab === k
                    ? "ui-btn ui-btn--tab ui-btn--sm is-active"
                    : "ui-btn ui-btn--tab ui-btn--sm"
                }
                onClick={() => {
                  setComposeTab(k);
                  setNewChatError(null);
                }}
              >
                {ico}
                {lab}
              </button>
            ))}
          </div>
          {composeTab === "private" ? (
            <>
              <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                <label
                  className="ui-field"
                  style={{ flex: 1, minWidth: 0 }}
                >
                  <span className="ui-field-label">Имя пользователя</span>
                  <input
                    className="ui-input"
                    value={usernameQuery}
                    onChange={(e) => {
                      setUsernameQuery(e.target.value);
                      setNewChatError(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void searchUsersCompose();
                    }}
                    maxLength={100}
                  />
                </label>
                <button
                  type="button"
                  className="ui-icon-btn ui-icon-btn--accent"
                  onClick={() => void searchUsersCompose()}
                  aria-label="Найти"
                  title="Найти"
                >
                  <IconSearch size={18} />
                </button>
              </div>
              <ValidationError message={newChatError} />
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                  marginTop: 8,
                  maxHeight: "55vh",
                  overflowY: "auto",
                }}
              >
                {searchHits.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    className="ui-row ui-row--button"
                    onClick={() => void createPrivate(u.id)}
                  >
                    <Avatar
                      src={userAvatarUrl(u.id, assetEpoch)}
                      label={avatarLetterFromUser(u)}
                      size={40}
                    />
                    <span style={{ fontSize: "0.92rem" }}>
                      {userListLabel(u)}
                    </span>
                  </button>
                ))}
                {searchHits.length === 0 ? (
                  <div
                    style={{
                      padding: "16px 12px",
                      color: "var(--text-muted)",
                      fontSize: "0.9rem",
                      textAlign: "center",
                    }}
                  >
                    Введите имя пользователя и нажмите «Найти».
                  </div>
                ) : null}
              </div>
            </>
          ) : (
            <>
              <label className="ui-field">
                <span className="ui-field-label">
                  Название {composeTab === "group" ? "группы" : "канала"}
                </span>
                <input
                  className="ui-input"
                  value={groupName}
                  onChange={(e) => {
                    setGroupName(e.target.value);
                    setNewChatError(null);
                  }}
                  maxLength={100}
                  autoFocus
                />
              </label>
              <ValidationError message={newChatError} />
              <button
                type="button"
                className="ui-btn ui-btn--primary ui-btn--block"
                style={{ marginTop: 8 }}
                onClick={() =>
                  void createGroupOrChannel(
                    composeTab === "group" ? "group" : "channel",
                  )
                }
              >
                <IconPlus size={16} />
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
          onOpenProfile={(id) => {
            setMenuOpen(false);
            setProfileUserId(id);
          }}
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
          onUserDeleted={onLogout}
        />
      ) : null}

      {profileUserId != null ? (
        <UserProfileModal
          userId={profileUserId}
          currentUser={currentUser}
          assetEpoch={assetEpoch}
          onClose={() => setProfileUserId(null)}
          onOpenChat={(id, options) => {
            setMenuOpen(false);
            setProfileUserId(null);
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
            animation: "slide-right 220ms ease-out both",
          }}
        >
          <div
            style={{
              padding: 8,
              borderBottom: "1px solid var(--border)",
              flexShrink: 0,
            }}
          >
            <button
              type="button"
              className="ui-btn ui-btn--ghost"
              onClick={() => setInfoOpen(false)}
            >
              <IconChevronLeft size={18} /> Назад к чату
            </button>
          </div>
          <div
            style={{
              flex: 1,
              minHeight: 0,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <ChatInfoPanel
              variant="sheet"
              chat={selectedChat}
              currentUserId={currentUser.id}
              privatePeerId={privatePeerByChat[selectedChat.id] ?? null}
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

function kindIcon(kind: Chat["chat_kind"]) {
  if (kind === "PRIVATE") return <IconUser size={12} />;
  if (kind === "GROUP") return <IconUsers size={12} />;
  if (kind === "CHANNEL") return <IconHash size={12} />;
  return <IconUser size={12} />;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(0)} КБ`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(mb < 10 ? 1 : 0)} МБ`;
  const gb = mb / 1024;
  return `${gb.toFixed(2)} ГБ`;
}

/**
 * Прогресс-бар отправки вложений с возможностью отмены.
 * Показывает процент, абсолютные байты и кнопку отмены текущей загрузки.
 */
function UploadProgressBar({
  progress,
  onCancel,
}: {
  progress: UploadProgress;
  onCancel: () => void;
}) {
  const percent =
    progress.total > 0
      ? Math.min(100, Math.round((progress.loaded / progress.total) * 100))
      : 0;
  const isUnknownTotal = progress.total === 0;
  const isFinalizing = !isUnknownTotal && progress.loaded >= progress.total;
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        padding: "8px 10px",
        marginBottom: 8,
        background: "var(--bg-muted)",
        border: "1.5px solid var(--border)",
        borderRadius: 10,
      }}
      aria-live="polite"
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          fontSize: "0.85rem",
          color: "var(--text-muted)",
        }}
      >
        <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <IconPaperclip size={14} />
          {isFinalizing
            ? "Обработка на сервере…"
            : isUnknownTotal
              ? "Загрузка вложения…"
              : `Загрузка вложения: ${percent}% · ${formatBytes(progress.loaded)} / ${formatBytes(progress.total)}`}
        </span>
        <button
          type="button"
          className="ui-btn ui-btn--ghost ui-btn--sm"
          onClick={onCancel}
          title="Отменить загрузку"
        >
          <IconX size={14} /> Отмена
        </button>
      </div>
      {/* Полоса прогресса. Если total неизвестен — показываем «бегущую» */}
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
