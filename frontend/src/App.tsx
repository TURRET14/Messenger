import {
  ArrowLeft,
  CalendarDays,
  Check,
  CheckCheck,
  CircleX,
  DoorOpen,
  Edit3,
  File as FileIcon,
  FileAudio,
  FileImage,
  FileText,
  FileVideo,
  Globe,
  Info,
  LoaderCircle,
  Lock,
  LogIn,
  LogOut,
  Mail,
  Megaphone,
  Menu,
  MessageCircle,
  Mic,
  Moon,
  Phone,
  Plus,
  Search,
  Send,
  Settings,
  ShieldBan,
  Square,
  Sun,
  Trash2,
  UserPlus,
  UserRound,
  Users,
  X,
} from 'lucide-react';
import {
  type ReactNode,
  type PropsWithChildren,
  useDeferredValue,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  QueryClient,
  QueryClientProvider,
  useInfiniteQuery,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import type { InfiniteData } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { z } from 'zod';

import { api, ApiError } from './api';
import {
  ALLOWED_IMAGE_EXTENSIONS,
  ALLOWED_IMAGE_TYPES,
  ATTACHMENT_MAX_SIZE_BYTES,
  AVATAR_MAX_SIZE_BYTES,
  PAGE_SIZE,
  SERVICE_NAME,
} from './config';
import { useAvatarVersionStore, useConfirmationDialogStore, useErrorDialogStore, useThemeStore, useUiStore } from './store';
import type {
  ApiValidationError,
  Chat,
  ChatKind,
  ChatMembership,
  ChatRole,
  CurrentUserProfile,
  FriendUserListItem,
  Message,
  MessageAttachment,
  PendingAttachment,
  UserListItem,
  UserProfile,
} from './types';
import {
  cn,
  formatBytes,
  formatDateOnly,
  formatDateTime,
  formatTimeOnly,
  getFullUserName,
  getInitials,
  isAudioType,
  isImageType,
  isVideoType,
} from './utils';
import { ManagedSocket } from './websocket';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 5_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});

const loginSchema = z.object({
  login: z.string().min(1, 'Введите логин.'),
  password: z.string().min(5, 'Пароль должен содержать минимум 5 символов.'),
});

const registerSchema = z
  .object({
    username: z.string().min(1, 'Введите username.').max(100, 'Слишком длинный username.'),
    name: z.string().min(1, 'Введите имя.').max(100, 'Слишком длинное имя.'),
    surname: z.string().max(100, 'Слишком длинная фамилия.').optional().or(z.literal('')),
    second_name: z.string().max(100, 'Слишком длинное отчество.').optional().or(z.literal('')),
    email_address: z.email('Введите корректную электронную почту.'),
    login: z.string().min(1, 'Введите логин.').max(100, 'Слишком длинный логин.'),
    password: z.string().min(5, 'Пароль должен содержать минимум 5 символов.').max(100),
    repeat_password: z.string().min(5, 'Повторите пароль.'),
  })
  .refine((value) => value.password === value.repeat_password, {
    message: 'Пароли не совпадают.',
    path: ['repeat_password'],
  });

type LoginFormValues = z.infer<typeof loginSchema>;
type RegisterFormValues = z.infer<typeof registerSchema>;
type SearchMode = 'username' | 'names';
type UserRowActions = {
  onOpenProfile?: () => void;
  onOpenPrivateChat?: () => void;
  onSendRequest?: () => void;
  onDeleteFriend?: () => void;
  onBlock?: () => void;
  onUnblock?: () => void;
  onAcceptRequest?: () => void;
  onDeclineRequest?: () => void;
  onDeleteRequest?: () => void;
  extraText?: string;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeController />
      <Routes>
        <Route path="/" element={<Navigate replace to="/app" />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/app" element={<ProtectedApp />} />
        <Route path="*" element={<Navigate replace to="/app" />} />
      </Routes>
      <GlobalDialogs />
    </QueryClientProvider>
  );
}

function ThemeController() {
  const mode = useThemeStore((state) => state.mode);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const applyTheme = () => {
      const resolved = mode === 'system' ? (media.matches ? 'dark' : 'light') : mode;
      document.documentElement.dataset.theme = resolved;
    };

    applyTheme();
    media.addEventListener('change', applyTheme);
    return () => media.removeEventListener('change', applyTheme);
  }, [mode]);

  return null;
}

function AuthPage() {
  const navigate = useNavigate();
  const showError = useApiErrorHandler();
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [registrationConfirmOpen, setRegistrationConfirmOpen] = useState(false);
  const [registrationCode, setRegistrationCode] = useState('');

  const currentUserQuery = useQuery({
    queryKey: ['session', 'current-user'],
    queryFn: api.getCurrentUser,
    retry: false,
  });

  useEffect(() => {
    if (currentUserQuery.data) {
      navigate('/app', { replace: true });
    }
  }, [currentUserQuery.data, navigate]);

  const loginForm = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      login: '',
      password: '',
    },
  });

  const registerForm = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: '',
      name: '',
      surname: '',
      second_name: '',
      email_address: '',
      login: '',
      password: '',
      repeat_password: '',
    },
  });

  const loginMutation = useMutation({
    mutationFn: api.login,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['session', 'current-user'] });
      navigate('/app', { replace: true });
    },
    onError: (error) => showError(error),
  });

  const registerMutation = useMutation({
    mutationFn: api.register,
    onSuccess: () => {
      setRegistrationCode('');
      setRegistrationConfirmOpen(true);
    },
    onError: (error) => showError(error),
  });

  const confirmMutation = useMutation({
    mutationFn: api.confirmRegistration,
    onSuccess: () => {
      setRegistrationConfirmOpen(false);
      setTab('login');
      registerForm.reset();
    },
    onError: (error) => showError(error),
  });

  return (
    <div className="auth-page">
      <div className="auth-hero">
        <div className="hero-badge">
          <MessageCircle size={16} />
          <span>{SERVICE_NAME}</span>
        </div>
        <h1>{SERVICE_NAME}</h1>
        <p className="hero-subtitle">
          Современный мессенджер с чатами, каналами, комментариями, друзьями и живым обновлением данных в реальном времени.
        </p>
      </div>

      <div className="auth-card card">
        <div className="auth-tabs">
          <button className={cn('tab-button', tab === 'login' && 'is-active')} onClick={() => setTab('login')} type="button">
            <LogIn size={16} />
            <span>Вход</span>
          </button>
          <button className={cn('tab-button', tab === 'register' && 'is-active')} onClick={() => setTab('register')} type="button">
            <UserPlus size={16} />
            <span>Регистрация</span>
          </button>
        </div>

        {tab === 'login' ? (
          <form className="auth-form" onSubmit={loginForm.handleSubmit((values) => loginMutation.mutate(values))}>
            <Field error={loginForm.formState.errors.login?.message} label="Логин">
              <input {...loginForm.register('login')} placeholder="Например, ivan_login" />
            </Field>
            <Field error={loginForm.formState.errors.password?.message} label="Пароль">
              <input {...loginForm.register('password')} placeholder="Введите пароль" type="password" />
            </Field>
            <button className="primary-button" disabled={loginMutation.isPending} type="submit">
              {loginMutation.isPending ? <LoaderCircle className="spin" size={18} /> : <LogIn size={18} />}
              <span>Войти</span>
            </button>
            <button className="ghost-button" onClick={() => setTab('register')} type="button">
              <UserPlus size={18} />
              <span>Перейти к регистрации</span>
            </button>
          </form>
        ) : (
          <form
            className="auth-form auth-form-register"
            onSubmit={registerForm.handleSubmit((values) =>
              registerMutation.mutate({
                username: values.username,
                name: values.name,
                surname: values.surname || null,
                second_name: values.second_name || null,
                email_address: values.email_address,
                login: values.login,
                password: values.password,
              }),
            )}
          >
            <Field error={registerForm.formState.errors.username?.message} label="Username">
              <input {...registerForm.register('username')} placeholder="ivan_petrov" />
            </Field>
            <Field error={registerForm.formState.errors.name?.message} label="Имя">
              <input {...registerForm.register('name')} placeholder="Иван" />
            </Field>
            <Field error={registerForm.formState.errors.surname?.message} label="Фамилия">
              <input {...registerForm.register('surname')} placeholder="Петров" />
            </Field>
            <Field error={registerForm.formState.errors.second_name?.message} label="Отчество">
              <input {...registerForm.register('second_name')} placeholder="Сергеевич" />
            </Field>
            <Field error={registerForm.formState.errors.email_address?.message} label="Электронная почта">
              <input {...registerForm.register('email_address')} placeholder="ivan@example.com" type="email" />
            </Field>
            <Field error={registerForm.formState.errors.login?.message} label="Логин">
              <input {...registerForm.register('login')} placeholder="ivan_login" />
            </Field>
            <Field error={registerForm.formState.errors.password?.message} label="Пароль">
              <input {...registerForm.register('password')} placeholder="Не короче 5 символов" type="password" />
            </Field>
            <Field error={registerForm.formState.errors.repeat_password?.message} label="Повтор пароля">
              <input {...registerForm.register('repeat_password')} placeholder="Повторите пароль" type="password" />
            </Field>
            <button className="primary-button" disabled={registerMutation.isPending} type="submit">
              {registerMutation.isPending ? <LoaderCircle className="spin" size={18} /> : <Mail size={18} />}
              <span>Зарегистрироваться</span>
            </button>
          </form>
        )}
      </div>

      <ModalFrame
        description="После регистрации введите код подтверждения, который был отправлен на указанную электронную почту."
        onClose={() => {
          if (!confirmMutation.isPending) {
            setRegistrationConfirmOpen(false);
          }
        }}
        open={registrationConfirmOpen}
        title="Подтверждение регистрации"
      >
        <form
          className="stack-vertical"
          onSubmit={(event) => {
            event.preventDefault();
            confirmMutation.mutate(registrationCode);
          }}
        >
          <Field label="Код подтверждения">
            <input onChange={(event) => setRegistrationCode(event.target.value)} placeholder="Введите код из письма" value={registrationCode} />
          </Field>
          <button className="primary-button" disabled={!registrationCode || confirmMutation.isPending} type="submit">
            {confirmMutation.isPending ? <LoaderCircle className="spin" size={18} /> : <Check size={18} />}
            <span>Подтвердить</span>
          </button>
        </form>
      </ModalFrame>
    </div>
  );
}

function ProtectedApp() {
  const showError = useApiErrorHandler();
  const currentUserQuery = useQuery({
    queryKey: ['session', 'current-user'],
    queryFn: api.getCurrentUser,
    retry: false,
  });

  useEffect(() => {
    if (currentUserQuery.error instanceof ApiError && currentUserQuery.error.status === 401) {
      showError(currentUserQuery.error, { redirectToAuth: true });
    }
  }, [currentUserQuery.error, showError]);

  if (currentUserQuery.isLoading) {
    return <SplashScreen subtitle="Проверяем активную сессию и загружаем рабочее пространство." title={`Добро пожаловать в ${SERVICE_NAME}`} />;
  }

  if (!currentUserQuery.data) {
    return <Navigate replace to="/auth" />;
  }

  return <MessengerShell currentUser={currentUserQuery.data} />;
}

function MessengerShell({ currentUser }: { currentUser: CurrentUserProfile }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const selectedChatId = useUiStore((state) => state.selectedChatId);
  const setSelectedChatId = useUiStore((state) => state.setSelectedChatId);
  const commentsRootId = useUiStore((state) => state.commentsRootId);
  const setCommentsRootId = useUiStore((state) => state.setCommentsRootId);
  const isMenuOpen = useUiStore((state) => state.isMenuOpen);
  const setMenuOpen = useUiStore((state) => state.setMenuOpen);
  const isMobileInfoOpen = useUiStore((state) => state.isMobileInfoOpen);
  const setMobileInfoOpen = useUiStore((state) => state.setMobileInfoOpen);
  const openModal = useUiStore((state) => state.openModal);
  const isCompactLayout = useMediaQuery('(max-width: 900px)');

  const chatsQuery = useInfiniteQuery({
    queryKey: ['chats'],
    queryFn: ({ pageParam }) => api.getChats(pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => (lastPage.length === PAGE_SIZE ? pages.length : undefined),
  });

  const chats = useMemo(() => flattenInfiniteList(chatsQuery.data), [chatsQuery.data]);
  const selectedChat = useMemo(() => chats.find((chat) => chat.id === selectedChatId) ?? null, [chats, selectedChatId]);
  const mobileLayoutMode = selectedChat ? 'show-chat-view' : 'show-list-view';

  useEffect(() => {
    if (!selectedChatId && chats[0] && !isCompactLayout) {
      setSelectedChatId(chats[0].id);
    }
  }, [chats, isCompactLayout, selectedChatId, setSelectedChatId]);

  useSocketSubscription({
    path: '/chats/post',
    enabled: true,
    onMessage: () => queryClientRef.invalidateQueries({ queryKey: ['chats'] }),
    onError: showError,
  });
  useSocketSubscription({
    path: '/chats/put',
    enabled: true,
    onMessage: (event) => {
      try {
        const payload = JSON.parse(event.data) as { id?: number };
        if (payload.id) {
          useAvatarVersionStore.getState().bumpChatVersion(payload.id);
          void queryClientRef.invalidateQueries({ queryKey: ['chat-memberships', payload.id] });
        }
      } catch {
        // ignore malformed websocket payloads
      }
      void queryClientRef.invalidateQueries({ queryKey: ['chats'] });
    },
    onError: showError,
  });
  useSocketSubscription({
    path: '/chats/delete',
    enabled: true,
    onMessage: () => queryClientRef.invalidateQueries({ queryKey: ['chats'] }),
    onError: showError,
  });
  useSocketSubscription({
    path: '/chats/messages/last',
    enabled: true,
    onMessage: () => queryClientRef.invalidateQueries({ queryKey: ['last-message'] }),
    onError: showError,
  });

  const chatLoadRef = useInfiniteLoader(() => chatsQuery.fetchNextPage(), Boolean(chatsQuery.hasNextPage), chatsQuery.isFetchingNextPage);

  return (
    <div className={cn('messenger-layout', mobileLayoutMode, isMobileInfoOpen ? 'info-open' : 'info-closed')}>
      <aside className="chat-sidebar">
        <div className="sidebar-toolbar">
          <button className="icon-button" onClick={() => setMenuOpen(true)} type="button">
            <Menu size={20} />
          </button>
          <div className="toolbar-title">
            <span>{SERVICE_NAME}</span>
            <small>{currentUser.username}</small>
          </div>
          <button className="icon-button accent" onClick={() => openModal({ type: 'create-chat' })} type="button">
            <Plus size={20} />
          </button>
        </div>

        <div className="chat-list">
          {chats.map((chat) => (
            <ChatListItem
              active={chat.id === selectedChatId}
              chat={chat}
              key={chat.id}
              onSelect={() => {
                setSelectedChatId(chat.id);
                setCommentsRootId(null);
                setMobileInfoOpen(!isCompactLayout);
              }}
            />
          ))}
          <div className="loader-anchor" ref={chatLoadRef} />
          {chatsQuery.isFetchingNextPage ? <MiniLoader label="Подгружаем чаты..." /> : null}
          {!chats.length && !chatsQuery.isLoading ? (
            <EmptyState
              icon={<MessageCircle size={28} />}
              subtitle="Создайте новый чат, канал или откройте профиль пользователя, чтобы начать общение."
              title="Чатов пока нет"
            />
          ) : null}
        </div>
      </aside>

      <main className="chat-main">
        {selectedChat ? (
          <ChatWorkspace chat={selectedChat} commentsRootId={commentsRootId} currentUser={currentUser} />
        ) : (
          <WelcomeScreen currentUser={currentUser} />
        )}
      </main>

      <aside className={cn('chat-info-shell', isMobileInfoOpen && 'is-open')}>
        {selectedChat ? (
          <ChatInfoPanel chat={selectedChat} currentUser={currentUser} onCloseMobile={() => setMobileInfoOpen(false)} />
        ) : (
          <div className="chat-info-empty" />
        )}
      </aside>

      <MenuDrawer currentUser={currentUser} onClose={() => setMenuOpen(false)} open={isMenuOpen} />
      <ModalHost />
    </div>
  );
}

function ChatListItem({ chat, active, onSelect }: { chat: Chat; active: boolean; onSelect: () => void }) {
  const lastMessageQuery = useQuery({
    queryKey: ['last-message', chat.id],
    queryFn: () => api.getLastMessage(chat.id),
  });

  return (
    <button className={cn('chat-list-item', active && 'is-active')} onClick={onSelect} type="button">
      <Avatar chat={chat} size="lg" />
      <div className="chat-list-item__body">
        <div className="chat-list-item__top">
          <strong>{chat.name}</strong>
        </div>
        <div className="chat-list-item__bottom">
          <span>
            {lastMessageQuery.data?.message?.message_text
              ? truncateText(lastMessageQuery.data.message.message_text, 72)
              : 'Сообщений пока нет'}
          </span>
        </div>
      </div>
    </button>
  );
}

function ChatWorkspace({
  chat,
  currentUser,
  commentsRootId,
}: {
  chat: Chat;
  currentUser: CurrentUserProfile;
  commentsRootId: number | null;
}) {
  const showError = useApiErrorHandler();
  const queryClientRef = useQueryClient();
  const setCommentsRootId = useUiStore((state) => state.setCommentsRootId);
  const setSelectedChatId = useUiStore((state) => state.setSelectedChatId);
  const isMobileInfoOpen = useUiStore((state) => state.isMobileInfoOpen);
  const setMobileInfoOpen = useUiStore((state) => state.setMobileInfoOpen);
  const [searchText, setSearchText] = useState('');
  const deferredSearchText = useDeferredValue(searchText.trim());
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const [editingMessage, setEditingMessage] = useState<Message | null>(null);
  const normalizedRootId = commentsRootId ?? undefined;
  const currentMembershipQuery = useQuery({
    queryKey: ['chat-memberships', chat.id, 'current-user'],
    queryFn: () => api.getChatMemberships(chat.id, 0),
    enabled: chat.chat_kind === 'CHANNEL' || chat.chat_kind === 'GROUP',
  });
  const currentMembership =
    currentMembershipQuery.data?.find((membership) => membership.chat_user_id === currentUser.id) ?? undefined;

  const chatQueryKey = commentsRootId
    ? ['messages', chat.id, 'comments', commentsRootId, deferredSearchText]
    : ['messages', chat.id, 'root', deferredSearchText];

  const messagesQuery = useInfiniteQuery({
    queryKey: chatQueryKey,
    queryFn: ({ pageParam }) => {
      if (commentsRootId && deferredSearchText) {
        return api.searchComments(chat.id, commentsRootId, pageParam, deferredSearchText);
      }
      if (commentsRootId) {
        return api.getComments(chat.id, commentsRootId, pageParam);
      }
      if (deferredSearchText) {
        return api.searchMessages(chat.id, pageParam, deferredSearchText);
      }
      return api.getMessages(chat.id, pageParam);
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => (lastPage.length === PAGE_SIZE ? pages.length : undefined),
  });

  const rootMessageQuery = useQuery({
    queryKey: ['message', chat.id, commentsRootId],
    queryFn: () => api.getMessage(chat.id, commentsRootId ?? 0),
    enabled: Boolean(commentsRootId),
  });

  const messages = useMemo(() => flattenDescendingMessages(messagesQuery.data), [messagesQuery.data]);
  const messageLoadRef = useInfiniteLoader(
    () => messagesQuery.fetchNextPage(),
    Boolean(messagesQuery.hasNextPage),
    messagesQuery.isFetchingNextPage,
  );

  useSocketSubscription({
    path: `/chats/${chat.id}/messages/post${normalizedRootId ? `?parent_message_id=${normalizedRootId}` : ''}`,
    enabled: true,
    onMessage: () => queryClientRef.invalidateQueries({ queryKey: chatQueryKey }),
    onError: showError,
  });
  useSocketSubscription({
    path: `/chats/${chat.id}/messages/put${normalizedRootId ? `?parent_message_id=${normalizedRootId}` : ''}`,
    enabled: true,
    onMessage: () => queryClientRef.invalidateQueries({ queryKey: chatQueryKey }),
    onError: showError,
  });
  useSocketSubscription({
    path: `/chats/${chat.id}/messages/delete${normalizedRootId ? `?parent_message_id=${normalizedRootId}` : ''}`,
    enabled: true,
    onMessage: () => queryClientRef.invalidateQueries({ queryKey: chatQueryKey }),
    onError: showError,
  });
  useSocketSubscription({
    path: `/chats/${chat.id}/messages/read`,
    enabled: chat.chat_kind === 'GROUP' || chat.chat_kind === 'PRIVATE',
    onMessage: () => queryClientRef.invalidateQueries({ queryKey: chatQueryKey }),
    onError: showError,
  });

  useMarkVisibleMessagesAsRead(chat, currentUser, messages);

  return (
    <div className="chat-workspace">
      <div className="chat-header">
        <button
          className="icon-button mobile-only"
          onClick={() => {
            setSelectedChatId(null);
            setCommentsRootId(null);
            setMobileInfoOpen(false);
          }}
          type="button"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="chat-header__identity">
          <Avatar chat={chat} size="md" />
          <div>
            <strong>{chat.name}</strong>
            <span>{chatLabelMap[chat.chat_kind]}</span>
          </div>
        </div>
        <div className="chat-search-bar chat-search-bar--inline">
          <label className="search-input">
            <Search size={16} />
            <input onChange={(event) => setSearchText(event.target.value)} placeholder="Поиск по сообщениям" value={searchText} />
          </label>
        </div>
        <div className="chat-header__actions">
          {commentsRootId ? (
            <button className="ghost-button" onClick={() => setCommentsRootId(null)} type="button">
              <ArrowBackIcon />
              <span>К основному чату</span>
            </button>
          ) : null}
          <button className={cn('icon-button', isMobileInfoOpen && 'is-active')} onClick={() => setMobileInfoOpen(!isMobileInfoOpen)} type="button">
            <Info size={18} />
          </button>
        </div>
      </div>

      {commentsRootId && rootMessageQuery.data ? (
        <div className="root-message-card card compact">
          <small>Корневое сообщение ветки комментариев</small>
          <MessageQuote message={rootMessageQuery.data} own={rootMessageQuery.data.sender_user_id === currentUser.id} />
        </div>
      ) : null}

      <div className="message-stream">
        {messagesQuery.isLoading ? <SplashScreen compact subtitle="Получаем сообщения выбранного чата." title="Загрузка сообщений" /> : null}
        {!messages.length && !messagesQuery.isLoading ? (
          <EmptyState
            icon={<FileText size={28} />}
            subtitle={deferredSearchText ? 'По этому запросу ничего не найдено.' : 'Напишите первое сообщение, чтобы начать диалог.'}
            title={deferredSearchText ? 'Сообщений не найдено' : 'Здесь пока тихо'}
          />
        ) : null}

        {messages.map((message) => (
          <MessageCard
            chat={chat}
            currentMembership={currentMembership}
            currentUser={currentUser}
            key={message.id}
            message={message}
            onDelete={() => openDeleteMessageDialog(chat.id, message.id, queryClientRef, showError, chatQueryKey)}
            onEdit={() => setEditingMessage(message)}
            onOpenComments={() => setCommentsRootId(message.id)}
            onReply={() => setReplyTo(message)}
          />
        ))}
        <div className="loader-anchor" ref={messageLoadRef} />
        {messagesQuery.isFetchingNextPage ? <MiniLoader label="Подгружаем сообщения..." /> : null}
      </div>

      <MessageComposer
        chat={chat}
        currentMembership={currentMembership}
        currentUser={currentUser}
        editingMessage={editingMessage}
        key={`${chat.id}-${editingMessage?.id ?? 'new'}`}
        onCancelEdit={() => setEditingMessage(null)}
        onCancelReply={() => setReplyTo(null)}
        onSubmitted={async () => {
          setReplyTo(null);
          setEditingMessage(null);
          await queryClientRef.invalidateQueries({ queryKey: chatQueryKey });
          await queryClientRef.invalidateQueries({ queryKey: ['last-message', chat.id] });
        }}
        replyTo={replyTo}
      />
    </div>
  );
}

function MessageCard({
  chat,
  currentMembership,
  message,
  currentUser,
  onReply,
  onDelete,
  onEdit,
  onOpenComments,
}: {
  chat: Chat;
  currentMembership?: ChatMembership;
  message: Message;
  currentUser: CurrentUserProfile;
  onReply: () => void;
  onDelete: () => void;
  onEdit: () => void;
  onOpenComments: () => void;
}) {
  const own = message.sender_user_id === currentUser.id;
  const senderQuery = useUserProfile(message.sender_user_id);
  const attachmentsQuery = useQuery({
    queryKey: ['message-attachments', chat.id, message.id],
    queryFn: () => api.getMessageAttachments(chat.id, message.id),
  });
  const canReply = canSendMessage(chat, currentUser.id, currentMembership);
  const canEdit = own;
  const canDelete = own || ((chat.chat_kind === 'PROFILE' || chat.chat_kind === 'CHANNEL') && chat.owner_user_id === currentUser.id);

  return (
    <article className={cn('message-card', own && 'is-own')}>
      <div className="message-card__meta">
        <Avatar fallbackLabel={senderQuery.data?.name} size="sm" userId={message.sender_user_id} />
        <div>
          <strong>{senderQuery.data ? getFullUserName(senderQuery.data) : 'Удалённый пользователь'}</strong>
          <span>{message.sender_user_id ? `@${senderQuery.data?.username ?? '...'}` : 'Системное событие'}</span>
        </div>
      </div>

      {message.reply_message_id ? <ReferencedMessage chatId={chat.id} messageId={message.reply_message_id} /> : null}
      {message.message_text ? <p className="message-card__text">{message.message_text}</p> : null}
      <AttachmentGallery attachments={attachmentsQuery.data ?? []} chatId={chat.id} messageId={message.id} />

      <div className="message-card__footer">
        <span>{formatTimeOnly(message.date_and_time_sent)}</span>
        {message.date_and_time_edited ? <span>изменено {formatTimeOnly(message.date_and_time_edited)}</span> : null}
        {own && message.is_read !== null ? (
          <span className="status-pill">{message.is_read ? <CheckCheck size={14} /> : <Check size={14} />}</span>
        ) : null}
      </div>

      <div className="message-card__actions">
        {canReply ? (
          <button className="subtle-button" onClick={onReply} type="button">
            <MessageCircle size={14} />
            <span>Ответить</span>
          </button>
        ) : null}
        {canEdit ? (
          <button className="subtle-button" onClick={onEdit} type="button">
            <Edit3 size={14} />
            <span>Изменить</span>
          </button>
        ) : null}
        {canDelete ? (
          <button className="subtle-button danger-text" onClick={onDelete} type="button">
            <Trash2 size={14} />
            <span>Удалить</span>
          </button>
        ) : null}
        {(chat.chat_kind === 'PROFILE' || chat.chat_kind === 'CHANNEL') && !message.parent_message_id ? (
          <button className="subtle-button" onClick={onOpenComments} type="button">
            <MessageCircle size={14} />
            <span>Комментарии</span>
          </button>
        ) : null}
      </div>
    </article>
  );
}

function MessageComposer({
  chat,
  currentMembership,
  currentUser,
  replyTo,
  editingMessage,
  onCancelReply,
  onCancelEdit,
  onSubmitted,
}: {
  chat: Chat;
  currentMembership?: ChatMembership;
  currentUser: CurrentUserProfile;
  replyTo: Message | null;
  editingMessage: Message | null;
  onCancelReply: () => void;
  onCancelEdit: () => void;
  onSubmitted: () => Promise<void>;
}) {
  const showError = useApiErrorHandler();
  const [messageText, setMessageText] = useState(() => editingMessage?.message_text ?? '');
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingError, setRecordingError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const fileInputId = useId();

  useEffect(
    () => () => attachments.forEach((item) => item.previewUrl && URL.revokeObjectURL(item.previewUrl)),
    [attachments],
  );

  const mutation = useMutation({
    mutationFn: async () => {
      if (editingMessage) {
        await api.updateMessage(chat.id, editingMessage.id, messageText);
        return;
      }

      await api.postMessage(
        chat.id,
        {
          messageText,
          replyMessageId: replyTo?.id ?? null,
          parentMessageId: replyTo?.parent_message_id ? replyTo.parent_message_id : undefined,
          files: attachments.map((item) => item.file),
        },
        setUploadProgress,
      );
    },
    onSuccess: async () => {
      setMessageText('');
      setUploadProgress(null);
      attachments.forEach((item) => item.previewUrl && URL.revokeObjectURL(item.previewUrl));
      setAttachments([]);
      await onSubmitted();
    },
    onError: (error) => {
      setUploadProgress(null);
      showError(error);
    },
  });

  const canSend = canSendMessage(chat, currentUser.id, currentMembership);
  const isSubmitDisabled = mutation.isPending || (!editingMessage && !messageText.trim() && attachments.length === 0);

  const handleFilesSelected = (files: FileList | null) => {
    if (!files) {
      return;
    }

    const nextItems: PendingAttachment[] = [];
    for (const file of Array.from(files)) {
      if (file.size > ATTACHMENT_MAX_SIZE_BYTES) {
        showError(
          new ApiError(400, 'FILE_TOO_LARGE', `Файл ${file.name} превышает допустимый размер ${formatBytes(ATTACHMENT_MAX_SIZE_BYTES)}.`, null),
        );
        continue;
      }

      nextItems.push({
        id: crypto.randomUUID(),
        file,
        previewUrl: null,
        kind: detectAttachmentKind(file),
      });
    }

    setAttachments((current) => [...current, ...nextItems]);
  };

  const handleToggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      setRecordingError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        stream.getTracks().forEach((track) => track.stop());
        const extension = blob.type.includes('ogg') ? 'ogg' : 'webm';
        const file = new File([blob], `Голосовое сообщение.${extension}`, { type: blob.type || 'audio/webm' });
        setAttachments((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            file,
            previewUrl: null,
            kind: 'audio',
          },
        ]);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      setRecordingError('Не удалось получить доступ к микрофону.');
    }
  };

  return (
    <div className="composer">
      {replyTo ? (
        <div className="composer-banner">
          <div className="composer-banner__body">
            <small>Ответ на сообщение</small>
            <MessageQuote message={replyTo} own={replyTo.sender_user_id === currentUser.id} />
          </div>
          <button className="icon-button" onClick={onCancelReply} type="button">
            <X size={16} />
          </button>
        </div>
      ) : null}

      {editingMessage ? (
        <div className="composer-banner">
          <div>
            <small>Редактирование сообщения</small>
            <p>Изменить можно только текст сообщения.</p>
          </div>
          <button className="icon-button" onClick={onCancelEdit} type="button">
            <X size={16} />
          </button>
        </div>
      ) : null}

      {attachments.length ? (
        <div className="attachment-draft-grid">
          {attachments.map((attachment) => (
            <AttachmentDraftCard
              attachment={attachment}
              key={attachment.id}
              onRemove={() =>
                setAttachments((current) => {
                  const target = current.find((item) => item.id === attachment.id);
                  if (target?.previewUrl) {
                    URL.revokeObjectURL(target.previewUrl);
                  }
                  return current.filter((item) => item.id !== attachment.id);
                })
              }
            />
          ))}
        </div>
      ) : null}

      {recordingError ? <div className="helper-error">{recordingError}</div> : null}
      {uploadProgress !== null ? <ProgressBar label={`Загрузка файлов: ${uploadProgress}%`} progress={uploadProgress} /> : null}

      <form
        className="composer__form"
        onSubmit={(event) => {
          event.preventDefault();
          if (isSubmitDisabled || !canSend) {
            return;
          }
          mutation.mutate();
        }}
      >
        <textarea
          onChange={(event) => setMessageText(event.target.value)}
          placeholder={canSend ? 'Введите сообщение' : 'У вас нет прав на отправку сообщений в этом чате'}
          rows={1}
          value={messageText}
        />
        <label className="icon-button" htmlFor={fileInputId}>
          <Plus size={18} />
          <input hidden id={fileInputId} multiple onChange={(event) => handleFilesSelected(event.target.files)} type="file" />
        </label>
        <button className={cn('icon-button', isRecording && 'danger')} onClick={handleToggleRecording} type="button">
          {isRecording ? <Square size={18} /> : <Mic size={18} />}
        </button>
        <button className="primary-button compact" disabled={isSubmitDisabled || !canSend} type="submit">
          {mutation.isPending ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}
        </button>
      </form>
    </div>
  );
}

function ChatInfoPanel({
  chat,
  currentUser,
  onCloseMobile,
}: {
  chat: Chat;
  currentUser: CurrentUserProfile;
  onCloseMobile: () => void;
}) {
  const openModal = useUiStore((state) => state.openModal);
  const showError = useApiErrorHandler();
  const queryClientRef = useQueryClient();
  const membershipsQuery = useInfiniteQuery({
    queryKey: ['chat-memberships', chat.id],
    queryFn: ({ pageParam }) => api.getChatMemberships(chat.id, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => (lastPage.length === PAGE_SIZE ? pages.length : undefined),
  });

  const memberships = useMemo(() => flattenInfiniteList(membershipsQuery.data), [membershipsQuery.data]);
  const membershipLoadRef = useInfiniteLoader(
    () => membershipsQuery.fetchNextPage(),
    Boolean(membershipsQuery.hasNextPage),
    membershipsQuery.isFetchingNextPage,
  );
  const currentMembership = memberships.find((membership) => membership.chat_user_id === currentUser.id) ?? null;
  const canManageMembers = currentMembership?.chat_role === 'OWNER' || currentMembership?.chat_role === 'ADMIN';
  const canEditChat = currentMembership?.chat_role === 'OWNER' || currentMembership?.chat_role === 'ADMIN';
  const isOwner = currentMembership?.chat_role === 'OWNER';

  return (
    <div className="chat-info card">
      <div className="chat-info__header">
        <div className="chat-info__identity">
          <Avatar chat={chat} size="xl" />
          <div>
            <strong>{chat.name}</strong>
            <span>{chatLabelMap[chat.chat_kind]}</span>
          </div>
        </div>
        <button className="icon-button mobile-only" onClick={onCloseMobile} type="button">
          <X size={18} />
        </button>
      </div>

      <div className="info-grid">
        <InfoLine icon={getChatKindIcon(chat.chat_kind)} label="Тип чата" value={chatLabelMap[chat.chat_kind]} />
        <InfoLine icon={<CalendarDays size={16} />} label="Создан" value={formatDateOnly(chat.date_and_time_created)} />
      </div>

      <div className="stack-vertical">
        {canEditChat && (chat.chat_kind === 'GROUP' || chat.chat_kind === 'CHANNEL') ? (
          <>
            <ActionButton
              icon={<Edit3 size={16} />}
              label="Изменить название"
              onClick={() => openModal({ type: 'edit-chat-name', chatId: chat.id, initialName: chat.name })}
            />
            <AvatarUploadButton
              currentLabel="Изменить фотографию чата"
              onFileSelected={(file) => updateChatAvatar(chat.id, file, showError, queryClientRef)}
            />
            <ActionButton
              danger
              icon={<Trash2 size={16} />}
              label="Сбросить фотографию чата"
              onClick={() => resetChatAvatar(chat.id, showError, queryClientRef)}
            />
          </>
        ) : null}

        {canManageMembers && (chat.chat_kind === 'GROUP' || chat.chat_kind === 'CHANNEL') ? (
          <ActionButton icon={<UserPlus size={16} />} label="Добавить участника" onClick={() => openModal({ type: 'add-member', chatId: chat.id })} />
        ) : null}

        {isOwner && (chat.chat_kind === 'GROUP' || chat.chat_kind === 'CHANNEL') ? (
          <ActionButton danger icon={<Trash2 size={16} />} label="Удалить чат" onClick={() => openDeleteChatDialog(chat.id, queryClientRef, showError)} />
        ) : (
          <ActionButton danger icon={<DoorOpen size={16} />} label="Покинуть чат" onClick={() => openLeaveChatDialog(chat.id, queryClientRef, showError)} />
        )}
      </div>

      <div className="chat-member-list">
        <div className="section-heading">
          <span>Участники</span>
          <small>{memberships.length}</small>
        </div>
        {memberships.map((membership) => (
          <ChatMemberRow chat={chat} currentMembership={currentMembership} key={membership.id} membership={membership} />
        ))}
        <div className="loader-anchor" ref={membershipLoadRef} />
        {membershipsQuery.isFetchingNextPage ? <MiniLoader label="Подгружаем участников..." /> : null}
      </div>
    </div>
  );
}

function MenuDrawer({
  currentUser,
  open,
  onClose,
}: {
  currentUser: CurrentUserProfile;
  open: boolean;
  onClose: () => void;
}) {
  const openModal = useUiStore((state) => state.openModal);
  const setMode = useThemeStore((state) => state.setMode);
  const mode = useThemeStore((state) => state.mode);
  const openMenuModal = (modal: Parameters<typeof openModal>[0]) => {
    openModal(modal);
    onClose();
  };

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  return (
    <div className={cn('menu-drawer-overlay', open && 'is-open')} onClick={onClose} role="presentation">
      <div className="menu-drawer" onClick={(event) => event.stopPropagation()} role="presentation">
        <div className="menu-drawer__top">
          <Avatar fallbackLabel={currentUser.name} size="xl" userId={currentUser.id} />
          <div>
            <strong>{getFullUserName(currentUser)}</strong>
            <span>@{currentUser.username}</span>
          </div>
          <button className="icon-button" onClick={onClose} type="button">
            <X size={18} />
          </button>
        </div>

        <div className="menu-actions">
          <ActionButton icon={<UserRound size={16} />} label="Профиль" onClick={() => openMenuModal({ type: 'profile', editable: true, userId: currentUser.id })} />
          <ActionButton icon={<Users size={16} />} label="Друзья" onClick={() => openMenuModal({ type: 'friends' })} />
          <ActionButton icon={<Mail size={16} />} label="Полученные заявки" onClick={() => openMenuModal({ type: 'received-requests' })} />
          <ActionButton icon={<Send size={16} />} label="Отправленные заявки" onClick={() => openMenuModal({ type: 'sent-requests' })} />
          <ActionButton icon={<Globe size={16} />} label="Пользователи" onClick={() => openMenuModal({ type: 'users' })} />
          <ActionButton icon={<ShieldBan size={16} />} label="Заблокированные" onClick={() => openMenuModal({ type: 'blocks' })} />
          <ActionButton icon={<Settings size={16} />} label="Сессии" onClick={() => openMenuModal({ type: 'sessions' })} />
        </div>

        <div className="theme-switcher">
          <div className="section-heading">
            <span>Тема</span>
          </div>
          <div className="theme-switcher__buttons">
            <ThemeButton active={mode === 'system'} icon={<Globe size={16} />} label="Как в системе" onClick={() => { setMode('system'); onClose(); }} />
            <ThemeButton active={mode === 'light'} icon={<Sun size={16} />} label="Светлая" onClick={() => { setMode('light'); onClose(); }} />
            <ThemeButton active={mode === 'dark'} icon={<Moon size={16} />} label="Тёмная" onClick={() => { setMode('dark'); onClose(); }} />
          </div>
        </div>
      </div>
    </div>
  );
}

function ModalHost() {
  const modal = useUiStore((state) => state.modal);
  const closeModal = useUiStore((state) => state.closeModal);

  if (modal.type === 'none') {
    return null;
  }

  if (modal.type === 'profile') {
    return <ProfileModal editable={modal.editable} onClose={closeModal} userId={modal.userId} />;
  }
  if (modal.type === 'friends') {
    return <FriendsModal onClose={closeModal} />;
  }
  if (modal.type === 'users') {
    return <UsersModal onClose={closeModal} />;
  }
  if (modal.type === 'received-requests') {
    return <FriendRequestsModal kind="received" onClose={closeModal} />;
  }
  if (modal.type === 'sent-requests') {
    return <FriendRequestsModal kind="sent" onClose={closeModal} />;
  }
  if (modal.type === 'blocks') {
    return <BlocksModal onClose={closeModal} />;
  }
  if (modal.type === 'create-chat') {
    return <CreateChatModal onClose={closeModal} />;
  }
  if (modal.type === 'sessions') {
    return <SessionsModal onClose={closeModal} />;
  }
  if (modal.type === 'add-member') {
    return <AddChatMemberModal chatId={modal.chatId} onClose={closeModal} />;
  }
  if (modal.type === 'edit-profile') {
    return <EditProfileModal onClose={closeModal} />;
  }
  if (modal.type === 'edit-email') {
    return <EditEmailModal onClose={closeModal} />;
  }
  if (modal.type === 'edit-login') {
    return <EditLoginModal onClose={closeModal} />;
  }
  if (modal.type === 'edit-password') {
    return <EditPasswordModal onClose={closeModal} />;
  }
  if (modal.type === 'edit-chat-name') {
    return <EditChatNameModal chatId={modal.chatId} initialName={modal.initialName} onClose={closeModal} />;
  }
  if (modal.type === 'delete-user') {
    return <DeleteUserModal login={modal.login} onClose={closeModal} />;
  }

  return null;
}

function ProfileModal({
  userId,
  editable,
  onClose,
}: {
  userId: number;
  editable: boolean;
  onClose: () => void;
}) {
  const showError = useApiErrorHandler();
  const queryClientRef = useQueryClient();
  const navigate = useNavigate();
  const openModal = useUiStore((state) => state.openModal);
  const profileQuery = useQuery({
    queryKey: ['user-profile', userId],
    queryFn: () => (editable ? api.getCurrentUser() : api.getUser(userId)),
  });
  const currentLoginQuery = useQuery({
    queryKey: ['current-login'],
    queryFn: api.getCurrentUserLogin,
    enabled: editable,
  });

  if (!profileQuery.data) {
    return (
      <ModalFrame onClose={onClose} open title="Профиль">
        <SplashScreen compact subtitle="Получаем данные профиля." title="Загрузка" />
      </ModalFrame>
    );
  }

  const profile = profileQuery.data;

  return (
    <ModalFrame onClose={onClose} open title={editable ? 'Мой профиль' : 'Профиль пользователя'}>
      <div className="profile-modal">
        <div className="profile-hero card compact">
          <Avatar fallbackLabel={profile.name} size="xl" userId={profile.id} />
          <div>
            <h3>{getFullUserName(profile)}</h3>
            <p>@{profile.username}</p>
          </div>
          {editable ? (
            <div className="profile-hero__actions">
              <AvatarUploadButton currentLabel="Изменить фотографию" onFileSelected={(file) => updateCurrentUserAvatar(file, showError, queryClientRef)} />
              <ActionButton danger icon={<Trash2 size={16} />} label="Сбросить фотографию" onClick={() => resetCurrentUserAvatar(showError, queryClientRef)} />
            </div>
          ) : null}
        </div>

        <div className="profile-details">
          <InfoLine icon={<UserRound size={16} />} label="Имя" value={profile.name} />
          <InfoLine icon={<UserRound size={16} />} label="Фамилия" value={profile.surname || 'Не указана'} />
          <InfoLine icon={<UserRound size={16} />} label="Отчество" value={profile.second_name || 'Не указано'} />
          <InfoLine icon={<CalendarDays size={16} />} label="Дата рождения" value={profile.date_of_birth ? formatDateOnly(profile.date_of_birth) : 'Не указана'} />
          <InfoLine icon={<Info size={16} />} label="Пол" value={profile.gender ? genderLabelMap[profile.gender] : 'Не указан'} />
          <InfoLine icon={<PhoneIcon />} label="Телефон" value={profile.phone_number || 'Не указан'} />
          <InfoLine icon={<Mail size={16} />} label="Почта" value={editable ? (profile as CurrentUserProfile).email_address : 'Скрыто'} />
          <InfoLine icon={<FileText size={16} />} label="О себе" value={profile.about || 'Описание отсутствует'} />
          <InfoLine icon={<CalendarDays size={16} />} label="Дата регистрации" value={formatDateTime(profile.date_and_time_registered)} />
        </div>

        {editable ? (
          <div className="stack-vertical">
            <ActionButton icon={<Edit3 size={16} />} label="Изменить основные данные" onClick={() => openModal({ type: 'edit-profile' })} />
            <ActionButton icon={<Mail size={16} />} label="Сменить электронную почту" onClick={() => openModal({ type: 'edit-email' })} />
            <ActionButton icon={<Lock size={16} />} label="Сменить пароль" onClick={() => openModal({ type: 'edit-password' })} />
            <ActionButton icon={<LogIn size={16} />} label="Сменить логин" onClick={() => openModal({ type: 'edit-login' })} />
            <ActionButton icon={<Settings size={16} />} label="Открыть список сессий" onClick={() => openModal({ type: 'sessions' })} />
            <ActionButton icon={<MessageCircle size={16} />} label="Открыть чат профиля" onClick={() => void openUserProfileChat(profile.id, navigate, queryClientRef, showError, onClose)} />
            <ActionButton danger icon={<Trash2 size={16} />} label="Удалить пользователя" onClick={() => openModal({ type: 'delete-user', login: currentLoginQuery.data?.login ?? '' })} />
          </div>
        ) : (
          <UserProfileActions profile={profile} />
        )}
      </div>
    </ModalFrame>
  );
}

function FriendsModal({ onClose }: { onClose: () => void }) {
  return (
    <UserBrowserModal<FriendUserListItem>
      emptyText="Список друзей пуст."
      fetchAll={(page) => api.getFriends(page)}
      fetchByNames={(page, params) => api.searchFriendsByNames(page, params)}
      fetchByUsername={(page, value) => api.searchFriendsByUsername(page, value)}
      mapActions={(user) => ({
        onDeleteFriend: () => deleteFriend(user.friendship_id),
        onOpenPrivateChat: () => void openPrivateChat(user.id),
        onOpenProfile: () => openUserProfile(user.id),
        onBlock: () => blockUserAction(user.id),
        extraText: `В друзьях с ${formatDateOnly(user.date_and_time_added)}`,
      })}
      onClose={onClose}
      title="Друзья"
    />
  );
}

function UsersModal({ onClose }: { onClose: () => void }) {
  const currentUser = queryClient.getQueryData<CurrentUserProfile>(['session', 'current-user']);
  return (
    <UserBrowserModal<UserListItem>
      emptyText="Пользователей пока нет."
      fetchAll={(page) => api.getUsers(page)}
      fetchByNames={(page, params) => api.searchUsersByNames(page, params)}
      fetchByUsername={(page, value) => api.searchUsersByUsername(page, value)}
      mapActions={(user) => ({
        onSendRequest: currentUser?.id === user.id ? undefined : () => sendFriendRequestAction(user.id),
        onOpenPrivateChat: currentUser?.id === user.id ? undefined : () => void openPrivateChat(user.id),
        onOpenProfile: () => openUserProfile(user.id),
        onBlock: currentUser?.id === user.id ? undefined : () => blockUserAction(user.id),
      })}
      onClose={onClose}
      title="Пользователи"
    />
  );
}

function FriendRequestsModal({ kind, onClose }: { kind: 'received' | 'sent'; onClose: () => void }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const requestsQuery = useInfiniteQuery({
    queryKey: ['friend-requests', kind],
    queryFn: ({ pageParam }) => (kind === 'received' ? api.getReceivedFriendRequests(pageParam) : api.getSentFriendRequests(pageParam)),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => (lastPage.length === PAGE_SIZE ? pages.length : undefined),
  });

  const requests = useMemo(() => flattenInfiniteList(requestsQuery.data), [requestsQuery.data]);
  const userIds = useMemo(() => requests.map((request) => (kind === 'received' ? request.sender_user_id : request.receiver_user_id)), [requests, kind]);
  const userQueries = useQueries({
    queries: userIds.map((userId) => ({
      queryKey: ['user-profile', userId],
      queryFn: () => api.getUser(userId),
      enabled: Boolean(userId),
    })),
  });
  const loadRef = useInfiniteLoader(() => requestsQuery.fetchNextPage(), Boolean(requestsQuery.hasNextPage), requestsQuery.isFetchingNextPage);

  return (
    <ModalFrame onClose={onClose} open title={kind === 'received' ? 'Полученные заявки в друзья' : 'Отправленные заявки в друзья'}>
      <div className="stack-vertical">
        {requests.map((request, index) => {
          const user = userQueries[index]?.data;
          return (
            <UserRow
              actions={
                kind === 'received'
                  ? {
                      onAcceptRequest: () =>
                        mutateWithRefresh(async () => api.acceptFriendRequest(request.id), queryClientRef, showError, [
                          ['friend-requests', 'received'],
                          ['friend-requests', 'sent'],
                          ['friends'],
                        ]),
                      onDeclineRequest: () =>
                        mutateWithRefresh(async () => api.declineFriendRequest(request.id), queryClientRef, showError, [['friend-requests', 'received']]),
                      onOpenProfile: user ? () => openUserProfile(user.id) : undefined,
                    }
                  : {
                      onDeleteRequest: () =>
                        mutateWithRefresh(async () => api.deleteSentFriendRequest(request.id), queryClientRef, showError, [['friend-requests', 'sent']]),
                      onOpenProfile: user ? () => openUserProfile(user.id) : undefined,
                    }
              }
              key={request.id}
              subtitle={`Отправлено ${formatDateTime(request.date_and_time_sent)}`}
              user={user}
            />
          );
        })}
        <div className="loader-anchor" ref={loadRef} />
      </div>
    </ModalFrame>
  );
}

function BlocksModal({ onClose }: { onClose: () => void }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const blocksQuery = useQuery({
    queryKey: ['blocks'],
    queryFn: api.getBlocks,
  });

  const userQueries = useQueries({
    queries: (blocksQuery.data ?? []).map((block) => ({
      queryKey: ['user-profile', block.blocked_user_id],
      queryFn: () => api.getUser(block.blocked_user_id),
      enabled: Boolean(block.blocked_user_id),
    })),
  });

  return (
    <ModalFrame onClose={onClose} open title="Заблокированные пользователи">
      <div className="stack-vertical">
        {(blocksQuery.data ?? []).map((block, index) => (
          <UserRow
            actions={{
              onOpenProfile: userQueries[index]?.data ? () => openUserProfile(userQueries[index].data!.id) : undefined,
              onUnblock: () =>
                mutateWithRefresh(async () => api.unblockUser(block.id), queryClientRef, showError, [['blocks']]),
            }}
            key={block.id}
            subtitle={`Заблокирован ${formatDateTime(block.date_and_time_blocked)}`}
            user={userQueries[index]?.data}
          />
        ))}
      </div>
    </ModalFrame>
  );
}

function CreateChatModal({ onClose }: { onClose: () => void }) {
  const [chatType, setChatType] = useState<'GROUP' | 'CHANNEL'>('GROUP');
  const [name, setName] = useState('');
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();

  return (
    <ModalFrame onClose={onClose} open title="Создание нового чата">
      <form
        className="stack-vertical"
        onSubmit={async (event) => {
          event.preventDefault();
          if (!name.trim()) {
            return;
          }
          await mutateWithRefresh(
            () => (chatType === 'GROUP' ? api.createGroupChat(name.trim()) : api.createChannel(name.trim())),
            queryClientRef,
            showError,
            [['chats']],
            onClose,
          );
        }}
      >
        <div className="segmented-control">
          <button className={cn(chatType === 'GROUP' && 'is-active')} onClick={() => setChatType('GROUP')} type="button">
            <Users size={16} />
            <span>Групповой чат</span>
          </button>
          <button className={cn(chatType === 'CHANNEL' && 'is-active')} onClick={() => setChatType('CHANNEL')} type="button">
            <Megaphone size={16} />
            <span>Канал</span>
          </button>
        </div>
        <Field label="Название">
          <input onChange={(event) => setName(event.target.value)} placeholder={chatType === 'GROUP' ? 'Например, Команда проекта' : 'Например, Новости команды'} value={name} />
        </Field>
        <button className="primary-button" type="submit">
          <Plus size={18} />
          <span>Создать</span>
        </button>
      </form>
    </ModalFrame>
  );
}

function SessionsModal({ onClose }: { onClose: () => void }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const sessionsQuery = useQuery({
    queryKey: ['sessions'],
    queryFn: api.getSessions,
  });

  return (
    <ModalFrame onClose={onClose} open title="Активные сессии">
      <div className="stack-vertical">
        {(sessionsQuery.data ?? []).map((session) => (
          <div className="session-card card compact" key={session.session_id}>
            <div>
              <strong>{session.user_agent}</strong>
              <p>Создана: {formatDateTime(new Date(session.creation_datetime * 1000).toISOString())}</p>
              <p>Истекает: {formatDateTime(new Date(session.expiration_datetime * 1000).toISOString())}</p>
            </div>
            <button
              className="ghost-button danger-text"
              onClick={() => mutateWithRefresh(async () => api.deleteSession(session.session_id), queryClientRef, showError, [['sessions']])}
              type="button"
            >
              <Trash2 size={16} />
              <span>Удалить</span>
            </button>
          </div>
        ))}
        {(sessionsQuery.data ?? []).length ? (
          <button className="ghost-button" onClick={() => mutateWithRefresh(api.deleteAllSessions, queryClientRef, showError, [['sessions']])} type="button">
            <LogOut size={16} />
            <span>Удалить все остальные сессии</span>
          </button>
        ) : null}
      </div>
    </ModalFrame>
  );
}

function AddChatMemberModal({ chatId, onClose }: { chatId: number; onClose: () => void }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const friendsQuery = useInfiniteQuery({
    queryKey: ['friends', 'add-member'],
    queryFn: ({ pageParam }) => api.getFriends(pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => (lastPage.length === PAGE_SIZE ? pages.length : undefined),
  });

  const friends = useMemo(() => flattenInfiniteList(friendsQuery.data), [friendsQuery.data]);

  return (
    <ModalFrame onClose={onClose} open title="Добавление участника">
      <div className="stack-vertical">
        {friends.map((friend) => (
          <UserRow
            actions={{
              onOpenProfile: () => openUserProfile(friend.id),
              extraText: `В друзьях с ${formatDateOnly(friend.date_and_time_added)}`,
            }}
            customAction={
              <button
                className="primary-button compact"
                onClick={() => mutateWithRefresh(async () => api.addChatUser(chatId, friend.id), queryClientRef, showError, [['chat-memberships', chatId]], onClose)}
                type="button"
              >
                <UserPlus size={16} />
                <span>Добавить</span>
              </button>
            }
            key={friend.id}
            user={friend}
          />
        ))}
      </div>
    </ModalFrame>
  );
}

function EditProfileModal({ onClose }: { onClose: () => void }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const profileQuery = useQuery({ queryKey: ['session', 'current-user'], queryFn: api.getCurrentUser });
  const schema = z.object({
    username: z.string().min(1, 'Введите username.').max(100),
    name: z.string().min(1, 'Введите имя.').max(100),
    surname: z.string().max(100).optional().or(z.literal('')),
    second_name: z.string().max(100).optional().or(z.literal('')),
    date_of_birth: z.string().optional().or(z.literal('')),
    gender: z.enum(['', 'MALE', 'FEMALE']),
    phone_number: z.string().optional().or(z.literal('')),
    about: z.string().max(5000).optional().or(z.literal('')),
  });
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    values: profileQuery.data
      ? {
          username: profileQuery.data.username,
          name: profileQuery.data.name,
          surname: profileQuery.data.surname ?? '',
          second_name: profileQuery.data.second_name ?? '',
          date_of_birth: profileQuery.data.date_of_birth ?? '',
          gender: (profileQuery.data.gender ?? '') as '' | 'MALE' | 'FEMALE',
          phone_number: profileQuery.data.phone_number ?? '',
          about: profileQuery.data.about ?? '',
        }
      : undefined,
  });
  const mutation = useMutation({
    mutationFn: async (values: z.infer<typeof schema>) => {
      if (!profileQuery.data) return;
      await api.updateProfile({
        username: values.username,
        name: values.name,
        surname: values.surname || null,
        second_name: values.second_name || null,
        date_of_birth: values.date_of_birth || null,
        gender: values.gender || null,
        email_address: profileQuery.data.email_address,
        phone_number: values.phone_number || null,
        about: values.about || null,
      });
    },
    onSuccess: async () => {
      await queryClientRef.invalidateQueries({ queryKey: ['session', 'current-user'] });
      onClose();
    },
    onError: (error) => showError(error),
  });

  return (
    <ModalFrame onClose={onClose} open title="Изменение профиля">
      <form className="stack-vertical" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <div className="grid-columns">
          <Field error={form.formState.errors.username?.message} label="Username"><input {...form.register('username')} /></Field>
          <Field error={form.formState.errors.name?.message} label="Имя"><input {...form.register('name')} /></Field>
          <Field error={form.formState.errors.surname?.message} label="Фамилия"><input {...form.register('surname')} /></Field>
        </div>
        <div className="grid-columns">
          <Field error={form.formState.errors.second_name?.message} label="Отчество"><input {...form.register('second_name')} /></Field>
          <Field error={form.formState.errors.date_of_birth?.message} label="Дата рождения"><input {...form.register('date_of_birth')} placeholder="YYYY-MM-DD" /></Field>
          <Field error={form.formState.errors.gender?.message} label="Пол">
            <select {...form.register('gender')} className="select-input">
              <option value="">Не указан</option>
              <option value="MALE">Мужской</option>
              <option value="FEMALE">Женский</option>
            </select>
          </Field>
        </div>
        <Field error={form.formState.errors.phone_number?.message} label="Телефон"><input {...form.register('phone_number')} placeholder="+79991234567" /></Field>
        <Field error={form.formState.errors.about?.message} label="О себе"><textarea {...form.register('about')} rows={4} /></Field>
        <div className="dialog-actions">
          <button className="ghost-button" onClick={onClose} type="button"><X size={18} /><span>Отмена</span></button>
          <button className="primary-button" disabled={mutation.isPending} type="submit">{mutation.isPending ? <LoaderCircle className="spin" size={18} /> : <Check size={18} />}<span>Сохранить</span></button>
        </div>
      </form>
    </ModalFrame>
  );
}

function EditEmailModal({ onClose }: { onClose: () => void }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const profileQuery = useQuery({ queryKey: ['session', 'current-user'], queryFn: api.getCurrentUser });
  const [step, setStep] = useState<'email' | 'confirm'>('email');
  const emailForm = useForm<{ email: string }>({ values: { email: profileQuery.data?.email_address ?? '' } });
  const codeForm = useForm<{ code: string }>({ defaultValues: { code: '' } });
  const sendMutation = useMutation({
    mutationFn: async (email: string) => api.updateEmail(email),
    onSuccess: () => setStep('confirm'),
    onError: (error) => showError(error),
  });
  const confirmMutation = useMutation({
    mutationFn: async (code: string) => api.confirmEmail(code),
    onSuccess: async () => {
      await queryClientRef.invalidateQueries({ queryKey: ['session', 'current-user'] });
      onClose();
    },
    onError: (error) => showError(error),
  });

  return (
    <ModalFrame onClose={onClose} open title="Смена электронной почты">
      {step === 'email' ? (
        <form className="stack-vertical" onSubmit={emailForm.handleSubmit((values) => sendMutation.mutate(values.email))}>
          <Field label="Новый адрес электронной почты"><input {...emailForm.register('email')} type="email" /></Field>
          <div className="dialog-actions">
            <button className="ghost-button" onClick={onClose} type="button"><X size={18} /><span>Отмена</span></button>
            <button className="primary-button" disabled={sendMutation.isPending} type="submit">{sendMutation.isPending ? <LoaderCircle className="spin" size={18} /> : <Mail size={18} />}<span>Отправить код</span></button>
          </div>
        </form>
      ) : (
        <form className="stack-vertical" onSubmit={codeForm.handleSubmit((values) => confirmMutation.mutate(values.code))}>
          <p>На новый адрес отправлен код подтверждения. Введите его ниже.</p>
          <Field label="Код подтверждения"><input {...codeForm.register('code')} /></Field>
          <div className="dialog-actions">
            <button className="ghost-button" onClick={() => setStep('email')} type="button"><ArrowBackIcon /><span>Назад</span></button>
            <button className="primary-button" disabled={confirmMutation.isPending} type="submit">{confirmMutation.isPending ? <LoaderCircle className="spin" size={18} /> : <Check size={18} />}<span>Подтвердить</span></button>
          </div>
        </form>
      )}
    </ModalFrame>
  );
}

function EditLoginModal({ onClose }: { onClose: () => void }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const loginQuery = useQuery({ queryKey: ['current-login'], queryFn: api.getCurrentUserLogin });
  const form = useForm<{ login: string }>({ values: { login: loginQuery.data?.login ?? '' } });
  const mutation = useMutation({
    mutationFn: async (login: string) => api.updateLogin(login),
    onSuccess: async () => {
      await queryClientRef.invalidateQueries({ queryKey: ['current-login'] });
      onClose();
    },
    onError: (error) => showError(error),
  });
  return (
    <ModalFrame onClose={onClose} open title="Смена логина">
      <form className="stack-vertical" onSubmit={form.handleSubmit((values) => mutation.mutate(values.login))}>
        <Field label="Новый логин"><input {...form.register('login')} /></Field>
        <div className="dialog-actions">
          <button className="ghost-button" onClick={onClose} type="button"><X size={18} /><span>Отмена</span></button>
          <button className="primary-button" disabled={mutation.isPending} type="submit">{mutation.isPending ? <LoaderCircle className="spin" size={18} /> : <Check size={18} />}<span>Сохранить</span></button>
        </div>
      </form>
    </ModalFrame>
  );
}

function EditPasswordModal({ onClose }: { onClose: () => void }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const schema = z.object({
    old_password: z.string().min(5, 'Введите текущий пароль.'),
    new_password: z.string().min(5, 'Новый пароль должен содержать минимум 5 символов.'),
    confirm_password: z.string().min(5, 'Повторите новый пароль.'),
  }).refine((value) => value.new_password === value.confirm_password, { message: 'Пароли не совпадают.', path: ['confirm_password'] });
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { old_password: '', new_password: '', confirm_password: '' } });
  const mutation = useMutation({
    mutationFn: async (values: z.infer<typeof schema>) => api.updatePassword(values.old_password, values.new_password),
    onSuccess: async () => {
      await queryClientRef.invalidateQueries({ queryKey: ['session', 'current-user'] });
      onClose();
    },
    onError: (error) => showError(error),
  });
  return (
    <ModalFrame onClose={onClose} open title="Смена пароля">
      <form className="stack-vertical" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <Field error={form.formState.errors.old_password?.message} label="Текущий пароль"><input {...form.register('old_password')} type="password" /></Field>
        <Field error={form.formState.errors.new_password?.message} label="Новый пароль"><input {...form.register('new_password')} type="password" /></Field>
        <Field error={form.formState.errors.confirm_password?.message} label="Повтор нового пароля"><input {...form.register('confirm_password')} type="password" /></Field>
        <div className="dialog-actions">
          <button className="ghost-button" onClick={onClose} type="button"><X size={18} /><span>Отмена</span></button>
          <button className="primary-button" disabled={mutation.isPending} type="submit">{mutation.isPending ? <LoaderCircle className="spin" size={18} /> : <Check size={18} />}<span>Сохранить</span></button>
        </div>
      </form>
    </ModalFrame>
  );
}

function EditChatNameModal({ chatId, initialName, onClose }: { chatId: number; initialName: string; onClose: () => void }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const form = useForm<{ name: string }>({ defaultValues: { name: initialName } });
  const mutation = useMutation({
    mutationFn: async (name: string) => api.updateChatName(chatId, name),
    onSuccess: async () => {
      await queryClientRef.invalidateQueries({ queryKey: ['chats'] });
      onClose();
    },
    onError: (error) => showError(error),
  });
  return (
    <ModalFrame onClose={onClose} open title="Изменение названия чата">
      <form className="stack-vertical" onSubmit={form.handleSubmit((values) => mutation.mutate(values.name))}>
        <Field label="Название"><input {...form.register('name')} /></Field>
        <div className="dialog-actions">
          <button className="ghost-button" onClick={onClose} type="button"><X size={18} /><span>Отмена</span></button>
          <button className="primary-button" disabled={mutation.isPending} type="submit">{mutation.isPending ? <LoaderCircle className="spin" size={18} /> : <Check size={18} />}<span>Сохранить</span></button>
        </div>
      </form>
    </ModalFrame>
  );
}

function DeleteUserModal({ login, onClose }: { login: string; onClose: () => void }) {
  const navigate = useNavigate();
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const form = useForm<{ password: string }>({ defaultValues: { password: '' } });
  const mutation = useMutation({
    mutationFn: async (password: string) => {
      await api.login({ login, password });
      await api.deleteUser();
    },
    onSuccess: async () => {
      await queryClientRef.invalidateQueries({ queryKey: ['session', 'current-user'] });
      navigate('/auth', { replace: true });
      onClose();
    },
    onError: (error) => showError(error),
  });
  return (
    <ModalFrame onClose={onClose} open title="Удаление пользователя" description="После подтверждения аккаунт будет удалён. Это действие необратимо.">
      <form className="stack-vertical" onSubmit={form.handleSubmit((values) => mutation.mutate(values.password))}>
        <Field label="Пароль для подтверждения"><input {...form.register('password')} type="password" /></Field>
        <div className="dialog-actions">
          <button className="ghost-button" onClick={onClose} type="button"><X size={18} /><span>Отмена</span></button>
          <button className="primary-button danger" disabled={mutation.isPending} type="submit">{mutation.isPending ? <LoaderCircle className="spin" size={18} /> : <Trash2 size={18} />}<span>Удалить аккаунт</span></button>
        </div>
      </form>
    </ModalFrame>
  );
}

function UserBrowserModal<T extends UserListItem>({
  title,
  emptyText,
  onClose,
  fetchAll,
  fetchByUsername,
  fetchByNames,
  mapActions,
}: {
  title: string;
  emptyText: string;
  onClose: () => void;
  fetchAll: (page: number) => Promise<T[]>;
  fetchByUsername: (page: number, value: string) => Promise<T[]>;
  fetchByNames: (page: number, params: { name?: string; surname?: string; second_name?: string }) => Promise<T[]>;
  mapActions: (user: T) => UserRowActions;
}) {
  const [searchMode, setSearchMode] = useState<SearchMode>('username');
  const [username, setUsername] = useState('');
  const [name, setName] = useState('');
  const [surname, setSurname] = useState('');
  const [secondName, setSecondName] = useState('');
  const deferredUsername = useDeferredValue(username.trim());
  const deferredName = useDeferredValue(name.trim());
  const deferredSurname = useDeferredValue(surname.trim());
  const deferredSecondName = useDeferredValue(secondName.trim());

  const query = useInfiniteQuery({
    queryKey: [title, searchMode, deferredUsername, deferredName, deferredSurname, deferredSecondName],
    queryFn: ({ pageParam }) => {
      if (searchMode === 'username' && deferredUsername) {
        return fetchByUsername(pageParam, deferredUsername);
      }
      if (searchMode === 'names' && (deferredName || deferredSurname || deferredSecondName)) {
        return fetchByNames(pageParam, {
          name: deferredName || undefined,
          surname: deferredSurname || undefined,
          second_name: deferredSecondName || undefined,
        });
      }
      return fetchAll(pageParam);
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => (lastPage.length === PAGE_SIZE ? pages.length : undefined),
  });

  const users = useMemo(() => flattenInfiniteList(query.data), [query.data]);
  const loadRef = useInfiniteLoader(() => query.fetchNextPage(), Boolean(query.hasNextPage), query.isFetchingNextPage);

  return (
    <ModalFrame onClose={onClose} open title={title}>
      <div className="stack-vertical">
        <div className="segmented-control">
          <button className={cn(searchMode === 'username' && 'is-active')} onClick={() => setSearchMode('username')} type="button">
            <Search size={16} />
            <span>Поиск по username</span>
          </button>
          <button className={cn(searchMode === 'names' && 'is-active')} onClick={() => setSearchMode('names')} type="button">
            <Users size={16} />
            <span>Поиск по ФИО</span>
          </button>
        </div>

        {searchMode === 'username' ? (
          <Field label="Username">
            <input onChange={(event) => setUsername(event.target.value)} placeholder="Введите username" value={username} />
          </Field>
        ) : (
          <div className="grid-columns">
            <Field label="Имя">
              <input onChange={(event) => setName(event.target.value)} placeholder="Имя" value={name} />
            </Field>
            <Field label="Фамилия">
              <input onChange={(event) => setSurname(event.target.value)} placeholder="Фамилия" value={surname} />
            </Field>
            <Field label="Отчество">
              <input onChange={(event) => setSecondName(event.target.value)} placeholder="Отчество" value={secondName} />
            </Field>
          </div>
        )}

        <div className="stack-vertical">
          {users.map((user) => (
            <UserRow actions={mapActions(user)} key={user.id} user={user} />
          ))}
          {!users.length && !query.isLoading ? <EmptyState icon={<Users size={26} />} subtitle={emptyText} title="Ничего не найдено" /> : null}
          <div className="loader-anchor" ref={loadRef} />
          {query.isFetchingNextPage ? <MiniLoader label="Подгружаем список..." /> : null}
        </div>
      </div>
    </ModalFrame>
  );
}

function UserRow({
  user,
  subtitle,
  actions,
  customAction,
}: {
  user: UserListItem | UserProfile | null | undefined;
  subtitle?: string;
  actions: UserRowActions;
  customAction?: ReactNode;
}) {
  return (
    <div className="user-row card compact">
      <button className={cn('user-row__main', actions.onOpenProfile && 'is-clickable')} onClick={actions.onOpenProfile} type="button">
        <Avatar fallbackLabel={user?.name} size="md" userId={user?.id} />
        <div>
          <strong>{user ? getFullUserName(user) : 'Загрузка пользователя...'}</strong>
          <span>{user ? `@${user.username}` : 'Подождите немного'}</span>
          {subtitle ? <small>{subtitle}</small> : null}
          {actions.extraText ? <small>{actions.extraText}</small> : null}
        </div>
      </button>

      <div className="user-row__actions">
        {actions.onOpenProfile ? <button className="subtle-button" onClick={actions.onOpenProfile} type="button"><Info size={14} /><span>Профиль</span></button> : null}
        {actions.onOpenPrivateChat ? <button className="subtle-button" onClick={actions.onOpenPrivateChat} type="button"><MessageCircle size={14} /><span>Чат</span></button> : null}
        {actions.onSendRequest ? <button className="subtle-button" onClick={actions.onSendRequest} type="button"><UserPlus size={14} /><span>Заявка</span></button> : null}
        {actions.onDeleteFriend ? <button className="subtle-button danger-text" onClick={actions.onDeleteFriend} type="button"><Trash2 size={14} /><span>Удалить</span></button> : null}
        {actions.onBlock ? <button className="subtle-button danger-text" onClick={actions.onBlock} type="button"><ShieldBan size={14} /><span>Блок</span></button> : null}
        {actions.onUnblock ? <button className="subtle-button" onClick={actions.onUnblock} type="button"><Check size={14} /><span>Разблокировать</span></button> : null}
        {actions.onAcceptRequest ? <button className="subtle-button" onClick={actions.onAcceptRequest} type="button"><Check size={14} /><span>Принять</span></button> : null}
        {actions.onDeclineRequest ? <button className="subtle-button danger-text" onClick={actions.onDeclineRequest} type="button"><CircleX size={14} /><span>Отклонить</span></button> : null}
        {actions.onDeleteRequest ? <button className="subtle-button danger-text" onClick={actions.onDeleteRequest} type="button"><Trash2 size={14} /><span>Удалить</span></button> : null}
        {customAction}
      </div>
    </div>
  );
}

function WelcomeScreen({ currentUser }: { currentUser: CurrentUserProfile }) {
  return (
    <div className="welcome-screen">
      <div className="welcome-screen__badge">
        <MessageCircle size={20} />
        <span>{SERVICE_NAME}</span>
      </div>
      <h2>Здравствуйте, {currentUser.name}.</h2>
      <p>Выберите чат слева, откройте профиль пользователя, создайте канал или начните новый диалог.</p>
    </div>
  );
}

function SplashScreen({ title, subtitle, compact = false }: { title: string; subtitle: string; compact?: boolean }) {
  return (
    <div className={cn('splash-screen', compact && 'is-compact')}>
      <LoaderCircle className="spin" size={compact ? 26 : 34} />
      <h3>{title}</h3>
      <p>{subtitle}</p>
    </div>
  );
}

function EmptyState({ icon, title, subtitle }: { icon: ReactNode; title: string; subtitle: string }) {
  return (
    <div className="empty-state">
      <div className="empty-state__icon">{icon}</div>
      <h3>{title}</h3>
      <p>{subtitle}</p>
    </div>
  );
}

function MiniLoader({ label }: { label: string }) {
  return (
    <div className="mini-loader">
      <LoaderCircle className="spin" size={16} />
      <span>{label}</span>
    </div>
  );
}

function GlobalDialogs() {
  const errorDialog = useErrorDialogStore((state) => state.dialog);
  const closeError = useErrorDialogStore((state) => state.closeDialog);
  const confirmation = useConfirmationDialogStore((state) => state.dialog);
  const closeConfirmation = useConfirmationDialogStore((state) => state.closeDialog);
  const [isConfirming, setIsConfirming] = useState(false);

  const handleConfirm = async () => {
    if (!confirmation.onConfirm) {
      return;
    }
    try {
      setIsConfirming(true);
      await confirmation.onConfirm();
    } finally {
      setIsConfirming(false);
      closeConfirmation();
    }
  };

  return (
    <>
      <ModalFrame onClose={closeError} open={errorDialog.open} title={errorDialog.title || 'Ошибка'}>
        <div className="stack-vertical">
          <div className="error-dialog">
            <div><strong>Код</strong><span>{errorDialog.code || 'UNKNOWN_ERROR'}</span></div>
            <div><strong>HTTP статус</strong><span>{errorDialog.status || 'Неизвестно'}</span></div>
          </div>
          <p>{errorDialog.message}</p>
          <button className="primary-button" onClick={closeError} type="button">
            <Check size={18} />
            <span>Понятно</span>
          </button>
        </div>
      </ModalFrame>

      <ModalFrame onClose={closeConfirmation} open={confirmation.open} title={confirmation.title}>
        <div className="stack-vertical">
          <p>{confirmation.description}</p>
          <div className="dialog-actions">
            <button className="ghost-button" onClick={closeConfirmation} type="button">
              <X size={18} />
              <span>Отмена</span>
            </button>
            <button className={cn('primary-button', confirmation.danger && 'danger')} disabled={isConfirming} onClick={handleConfirm} type="button">
              {isConfirming ? <LoaderCircle className="spin" size={18} /> : <Check size={18} />}
              <span>{confirmation.confirmLabel}</span>
            </button>
          </div>
        </div>
      </ModalFrame>
    </>
  );
}

function ModalFrame({
  open,
  title,
  description,
  onClose,
  children,
}: PropsWithChildren<{ open: boolean; title: string; description?: string; onClose?: () => void }>) {
  useEffect(() => {
    if (!open || !onClose) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-frame card" onClick={(event) => event.stopPropagation()} role="presentation">
        <div className="modal-frame__header">
          <div>
            <h2>{title}</h2>
            {description ? <p>{description}</p> : null}
          </div>
          {onClose ? <button className="icon-button" onClick={onClose} type="button"><X size={18} /></button> : null}
        </div>
        <div className="modal-frame__content">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, error, children }: PropsWithChildren<{ label: string; error?: string }>) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {error ? <small className="helper-error">{error}</small> : null}
    </label>
  );
}

function InfoLine({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="info-line">
      <span className="info-line__icon">{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function ActionButton({ icon, label, onClick, danger = false }: { icon: ReactNode; label: string; onClick: () => void; danger?: boolean }) {
  return (
    <button className={cn('action-button', danger && 'danger')} onClick={onClick} type="button">
      {icon}
      <span>{label}</span>
    </button>
  );
}

function ThemeButton({ active, icon, label, onClick }: { active: boolean; icon: ReactNode; label: string; onClick: () => void }) {
  return (
    <button className={cn('theme-button', active && 'is-active')} onClick={onClick} type="button">
      {icon}
      <span>{label}</span>
    </button>
  );
}

function Avatar({ userId, chat, size, fallbackLabel }: { userId?: number | null; chat?: Chat; size: 'sm' | 'md' | 'lg' | 'xl'; fallbackLabel?: string | null }) {
  const classes = cn('avatar', `avatar--${size}`);
  const [hidden, setHidden] = useState(false);
  const userVersion = useAvatarVersionStore((state) => (userId ? state.userVersions[userId] : undefined));
  const chatVersion = useAvatarVersionStore((state) => (chat?.id ? state.chatVersions[chat.id] : undefined));

  if (!hidden) {
    if (chat && (chat.chat_kind === 'GROUP' || chat.chat_kind === 'CHANNEL')) {
      return <img alt={chat.name} className={classes} onError={() => setHidden(true)} src={api.buildUrl(`/chats/id/${chat.id}/avatar?v=${chatVersion ?? 0}`)} />;
    }
    if (userId) {
      return <img alt="Аватар пользователя" className={classes} onError={() => setHidden(true)} src={api.buildUrl(`/users/id/${userId}/avatar?v=${userVersion ?? 0}`)} />;
    }
  }

  const fallback = fallbackLabel?.trim() || chat?.name || 'Пользователь';
  return <div className={cn(classes, 'avatar-fallback')}>{getInitials(fallback)}</div>;
}

function AttachmentGallery({ chatId, messageId, attachments }: { chatId: number; messageId: number; attachments: MessageAttachment[] }) {
  if (!attachments.length) {
    return null;
  }
  return (
    <div className="attachment-gallery">
      {attachments.map((attachment) => (
        <AttachmentPreview attachment={attachment} chatId={chatId} key={attachment.id} messageId={messageId} />
      ))}
    </div>
  );
}

function AttachmentPreview({ attachment, chatId, messageId }: { attachment: MessageAttachment; chatId: number; messageId: number }) {
  const fileUrl = api.buildUrl(`/chats/id/${chatId}/messages/id/${messageId}/attachments/id/${attachment.id}`);
  if (attachment.kind === 'image') {
    return (
      <a className="attachment-preview attachment-preview--media" href={fileUrl} rel="noreferrer" target="_blank">
        <img alt={attachment.file_name} className="attachment-preview__image" src={fileUrl} />
        <span>{attachment.file_name}</span>
      </a>
    );
  }

  if (attachment.kind === 'video') {
    return (
      <div className="attachment-preview attachment-preview--media">
        <video className="attachment-preview__video" controls preload="metadata" src={fileUrl} />
        <a href={fileUrl} rel="noreferrer" target="_blank">{attachment.file_name}</a>
      </div>
    );
  }

  if (attachment.kind === 'audio') {
    return (
      <div className="attachment-preview attachment-preview--audio">
        <div className="attachment-preview__icon"><FileAudio size={18} /></div>
        <div className="attachment-preview__meta">
          <strong>{attachment.file_name}</strong>
          <audio controls preload="metadata" src={fileUrl} />
        </div>
      </div>
    );
  }

  return <a className="attachment-preview" href={fileUrl} rel="noreferrer" target="_blank"><FileIcon size={18} /><span>{attachment.file_name}</span></a>;
}

function AttachmentDraftCard({ attachment, onRemove }: { attachment: PendingAttachment; onRemove: () => void }) {
  return (
    <div className="attachment-draft-card">
      <div className="attachment-draft-card__preview">
        <AttachmentKindIcon kind={attachment.kind} />
      </div>
      <div className="attachment-draft-card__meta">
        <strong>{attachment.file.name}</strong>
        <span>{formatBytes(attachment.file.size)}</span>
      </div>
      <button className="icon-button" onClick={onRemove} type="button"><X size={16} /></button>
    </div>
  );
}

function AttachmentKindIcon({ kind }: { kind: PendingAttachment['kind'] }) {
  if (kind === 'image') return <FileImage size={18} />;
  if (kind === 'video') return <FileVideo size={18} />;
  if (kind === 'audio') return <FileAudio size={18} />;
  return <FileText size={18} />;
}

function ProgressBar({ progress, label }: { progress: number; label: string }) {
  return <div className="progress-block"><div className="progress-block__label"><span>{label}</span><strong>{progress}%</strong></div><div className="progress-block__track"><div className="progress-block__fill" style={{ width: `${progress}%` }} /></div></div>;
}

function ReferencedMessage({ chatId, messageId }: { chatId: number; messageId: number }) {
  const query = useQuery({ queryKey: ['message', chatId, messageId], queryFn: () => api.getMessage(chatId, messageId) });
  return query.data ? <MessageQuote message={query.data} own={false} /> : null;
}

function MessageQuote({ message, own }: { message: Message; own: boolean }) {
  return <div className={cn('message-quote', own && 'is-own')}><small>{message.message_text ? truncateText(message.message_text, 120) : 'Сообщение без текста'}</small></div>;
}

function ChatMemberRow({ chat, membership, currentMembership }: { chat: Chat; membership: ChatMembership; currentMembership: ChatMembership | null }) {
  const queryClientRef = useQueryClient();
  const showError = useApiErrorHandler();
  const userQuery = useUserProfile(membership.chat_user_id);
  const canDemote = currentMembership?.chat_role === 'OWNER' && membership.chat_user_id !== currentMembership.chat_user_id && membership.chat_role === 'ADMIN';
  const canPromote = currentMembership?.chat_role === 'OWNER' && membership.chat_user_id !== currentMembership.chat_user_id && membership.chat_role === 'USER';
  const canRemove = (currentMembership?.chat_role === 'OWNER' || currentMembership?.chat_role === 'ADMIN') && membership.chat_user_id !== currentMembership?.chat_user_id && membership.chat_role !== 'OWNER';

  return (
    <div className="member-row card compact">
      <button className="member-row__main is-clickable" onClick={() => openUserProfile(membership.chat_user_id)} type="button">
        <Avatar fallbackLabel={userQuery.data?.name} size="md" userId={membership.chat_user_id} />
        <div>
          <strong>{userQuery.data ? getFullUserName(userQuery.data) : 'Загрузка пользователя...'}</strong>
          <span>{chatRoleLabelMap[membership.chat_role]}</span>
          <small>Добавлен {formatDateOnly(membership.date_and_time_added)}</small>
        </div>
      </button>
      <div className="member-row__actions">
        {canPromote ? <button className="subtle-button" onClick={() => mutateWithRefresh(async () => api.addChatAdmin(chat.id, membership.chat_user_id), queryClientRef, showError, [['chat-memberships', chat.id]])} type="button"><ShieldBan size={14} /><span>Сделать админом</span></button> : null}
        {canDemote ? <button className="subtle-button" onClick={() => mutateWithRefresh(async () => api.deleteChatAdmin(chat.id, membership.chat_user_id), queryClientRef, showError, [['chat-memberships', chat.id]])} type="button"><ShieldBan size={14} /><span>Снять администратора</span></button> : null}
        {canRemove ? <button className="subtle-button danger-text" onClick={() => mutateWithRefresh(async () => api.deleteChatUser(chat.id, membership.chat_user_id), queryClientRef, showError, [['chat-memberships', chat.id]])} type="button"><Trash2 size={14} /><span>Удалить</span></button> : null}
      </div>
    </div>
  );
}

function UserProfileActions({ profile }: { profile: UserProfile }) {
  return (
    <div className="stack-vertical">
      <ActionButton icon={<MessageCircle size={16} />} label="Открыть приватный чат" onClick={() => void openPrivateChat(profile.id)} />
      <ActionButton icon={<Info size={16} />} label="Открыть чат профиля" onClick={() => void openUserProfileChat(profile.id)} />
      <ActionButton icon={<UserPlus size={16} />} label="Отправить заявку в друзья" onClick={() => sendFriendRequestAction(profile.id)} />
      <ActionButton danger icon={<ShieldBan size={16} />} label="Заблокировать" onClick={() => blockUserAction(profile.id)} />
    </div>
  );
}

function AvatarUploadButton({ currentLabel, onFileSelected }: { currentLabel: string; onFileSelected: (file: File) => Promise<void> }) {
  const inputId = useId();
  const showError = useApiErrorHandler();

  return (
    <label className="ghost-button avatar-upload-button" htmlFor={inputId}>
      <Edit3 size={16} />
      <span>{currentLabel}</span>
      <input
        accept={ALLOWED_IMAGE_EXTENSIONS.join(',')}
        hidden
        id={inputId}
        onChange={async (event) => {
          const file = event.target.files?.[0];
          if (!file) return;
          if (!ALLOWED_IMAGE_TYPES.includes(file.type) && !ALLOWED_IMAGE_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext))) {
            showError(new ApiError(400, 'UNSUPPORTED_IMAGE_TYPE', 'Поддерживаются только PNG, JPG, JPEG и WEBP.', null));
            return;
          }
          if (file.size > AVATAR_MAX_SIZE_BYTES) {
            showError(new ApiError(400, 'IMAGE_TOO_LARGE', `Файл превышает лимит ${formatBytes(AVATAR_MAX_SIZE_BYTES)} для аватарки.`, null));
            return;
          }
          await onFileSelected(file);
        }}
        type="file"
      />
    </label>
  );
}

function PhoneIcon() {
  return <Phone size={16} />;
}

function ArrowBackIcon() {
  return <ArrowLeft size={16} />;
}

function useApiErrorHandler() {
  const navigate = useNavigate();
  const openDialog = useErrorDialogStore((state) => state.openDialog);
  return (error: unknown, options?: { redirectToAuth?: boolean }) => {
    const dialog = buildDialogPayload(error);
    openDialog(dialog);
    if (options?.redirectToAuth) navigate('/auth', { replace: true });
  };
}

function getApiErrorHandlerStatic() {
  return (error: unknown) => useErrorDialogStore.getState().openDialog(buildDialogPayload(error));
}

function buildDialogPayload(error: unknown) {
  if (error instanceof ApiError) return { title: error.status === 401 ? 'Ошибка авторизации' : 'Ошибка запроса', code: error.code, message: error.message, status: error.status };
  if (isValidationError(error)) return { title: 'Ошибка валидации', code: 'VALIDATION_ERROR', message: error.detail[0]?.msg ?? 'Проверьте введённые данные.', status: 422 };
  if (error instanceof Error) return { title: 'Ошибка', code: error.name, message: error.message, status: 0 };
  return { title: 'Ошибка', code: 'UNKNOWN_ERROR', message: 'Произошла непредвиденная ошибка.', status: 0 };
}

function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const media = window.matchMedia(query);
    const update = (event: MediaQueryListEvent) => setMatches(event.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [query]);

  return matches;
}

function getChatKindIcon(chatKind: ChatKind) {
  if (chatKind === 'GROUP') return <Users size={16} />;
  if (chatKind === 'CHANNEL') return <Megaphone size={16} />;
  return <MessageCircle size={16} />;
}

function useInfiniteLoader(onReach: () => void, enabled: boolean, loading: boolean) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const target = ref.current;
    if (!target || !enabled || loading) return;
    const observer = new IntersectionObserver((entries) => { if (entries[0]?.isIntersecting) onReach(); }, { rootMargin: '180px' });
    observer.observe(target);
    return () => observer.disconnect();
  }, [enabled, loading, onReach]);
  return ref;
}

function useSocketSubscription({ path, enabled, onMessage, onError }: { path: string; enabled: boolean; onMessage: (event: MessageEvent) => void; onError: (error: unknown) => void }) {
  const socketRef = useRef<ManagedSocket | null>(null);
  useEffect(() => {
    if (!socketRef.current) {
      socketRef.current = new ManagedSocket({ path, enabled, onMessage });
      return () => socketRef.current?.disconnect(true);
    }
    try {
      socketRef.current.update({ path, enabled, onMessage });
    } catch (error) {
      onError(error);
    }
  }, [enabled, onError, onMessage, path]);
}

function useMarkVisibleMessagesAsRead(chat: Chat, currentUser: CurrentUserProfile, messages: Message[]) {
  useEffect(() => {
    if (chat.chat_kind !== 'PRIVATE' && chat.chat_kind !== 'GROUP') return;
    const unread = messages.filter((message) => message.sender_user_id !== currentUser.id && message.is_read === false);
    if (!unread.length) return;
    void Promise.allSettled(unread.slice(-8).map((message) => api.markMessageAsRead(chat.id, message.id)));
  }, [chat.chat_kind, chat.id, currentUser.id, messages]);
}

function useUserProfile(userId: number | null | undefined) {
  return useQuery({ queryKey: ['user-profile', userId], queryFn: () => api.getUser(userId ?? 0), enabled: Boolean(userId) });
}

function flattenInfiniteList<T>(data: InfiniteData<T[], unknown> | undefined): T[] { return data?.pages.flatMap((page) => page) ?? []; }
function flattenDescendingMessages(data: InfiniteData<Message[], unknown> | undefined): Message[] { return (data?.pages.flatMap((page) => page) ?? []).reverse(); }
function detectAttachmentKind(file: File): PendingAttachment['kind'] { if (isImageType(file.type)) return 'image'; if (isVideoType(file.type)) return 'video'; if (isAudioType(file.type)) return 'audio'; return 'file'; }
function truncateText(value: string, maxLength: number) { return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value; }
function canSendMessage(chat: Chat, _currentUserId: number, membership: ChatMembership | undefined) { if (chat.chat_kind === 'CHANNEL') return membership?.chat_role === 'OWNER' || membership?.chat_role === 'ADMIN'; return true; }
function isValidationError(error: unknown): error is ApiValidationError { return Boolean(error && typeof error === 'object' && 'detail' in error); }

const confirmationStoreAccessor = useConfirmationDialogStore.getState;

function openDeleteMessageDialog(chatId: number, messageId: number, queryClientRef: QueryClient, showError: (error: unknown) => void, queryKey: readonly unknown[]) {
  confirmationStoreAccessor().openDialog({ title: 'Удаление сообщения', description: 'Сообщение и его вложения будут удалены без возможности восстановления.', confirmLabel: 'Удалить сообщение', danger: true, onConfirm: async () => mutateWithRefresh(async () => api.deleteMessage(chatId, messageId), queryClientRef, showError, [queryKey, ['last-message', chatId]]) });
}
function openDeleteChatDialog(chatId: number, queryClientRef: QueryClient, showError: (error: unknown) => void) {
  confirmationStoreAccessor().openDialog({ title: 'Удаление чата', description: 'Чат будет удалён вместе с историей сообщений и вложениями.', confirmLabel: 'Удалить чат', danger: true, onConfirm: async () => mutateWithRefresh(async () => api.deleteChat(chatId), queryClientRef, showError, [['chats']]) });
}
function openLeaveChatDialog(chatId: number, queryClientRef: QueryClient, showError: (error: unknown) => void) {
  confirmationStoreAccessor().openDialog({ title: 'Выход из чата', description: 'Вы уверены, что хотите покинуть выбранный чат?', confirmLabel: 'Покинуть чат', danger: true, onConfirm: async () => mutateWithRefresh(async () => api.leaveChat(chatId), queryClientRef, showError, [['chats']]) });
}
async function updateChatAvatar(chatId: number, file: File, showError: (error: unknown) => void, queryClientRef: QueryClient) { try { await api.updateChatAvatar(chatId, file); useAvatarVersionStore.getState().bumpChatVersion(chatId); await queryClientRef.invalidateQueries({ queryKey: ['chats'] }); await queryClientRef.invalidateQueries({ queryKey: ['chat-memberships', chatId] }); } catch (error) { showError(error); } }
async function updateCurrentUserAvatar(file: File, showError: (error: unknown) => void, queryClientRef: QueryClient) { try { const currentUser = queryClientRef.getQueryData<CurrentUserProfile>(['session', 'current-user']); await api.updateAvatar(file); if (currentUser?.id) useAvatarVersionStore.getState().bumpUserVersion(currentUser.id); await queryClientRef.invalidateQueries({ queryKey: ['session', 'current-user'] }); } catch (error) { showError(error); } }
async function resetChatAvatar(chatId: number, showError: (error: unknown) => void, queryClientRef: QueryClient) { try { await api.deleteChatAvatar(chatId); useAvatarVersionStore.getState().bumpChatVersion(chatId); await queryClientRef.invalidateQueries({ queryKey: ['chats'] }); await queryClientRef.invalidateQueries({ queryKey: ['chat-memberships', chatId] }); } catch (error) { showError(error); } }
async function resetCurrentUserAvatar(showError: (error: unknown) => void, queryClientRef: QueryClient) { try { const currentUser = queryClientRef.getQueryData<CurrentUserProfile>(['session', 'current-user']); await api.deleteAvatar(); if (currentUser?.id) useAvatarVersionStore.getState().bumpUserVersion(currentUser.id); await queryClientRef.invalidateQueries({ queryKey: ['session', 'current-user'] }); } catch (error) { showError(error); } }
async function openUserProfileChat(userId: number, navigate?: ReturnType<typeof useNavigate>, queryClientRef?: QueryClient, showError?: (error: unknown) => void, onComplete?: () => void) { try { const result = await api.getProfileChat(userId); useUiStore.getState().setSelectedChatId(result.id); useUiStore.getState().setCommentsRootId(null); onComplete?.(); navigate?.('/app', { replace: true }); if (queryClientRef) await queryClientRef.invalidateQueries({ queryKey: ['chats'] }); } catch (error) { showError?.(error); } }
async function openPrivateChat(userId: number) { try { const result = await api.createPrivateChat(userId); useUiStore.getState().setSelectedChatId(result.id); useUiStore.getState().setCommentsRootId(null); await queryClient.invalidateQueries({ queryKey: ['chats'] }); } catch (error) { getApiErrorHandlerStatic()(error); } }
function sendFriendRequestAction(userId: number) { void mutateWithRefresh(async () => api.sendFriendRequest(userId), queryClient, getApiErrorHandlerStatic(), [['friend-requests', 'sent']]); }
function blockUserAction(userId: number) { void mutateWithRefresh(async () => api.blockUser(userId), queryClient, getApiErrorHandlerStatic(), [['blocks'], ['friends'], ['friend-requests', 'sent'], ['friend-requests', 'received'], ['chats']]); }
function deleteFriend(friendshipId: number) { void mutateWithRefresh(async () => api.deleteFriendship(friendshipId), queryClient, getApiErrorHandlerStatic(), [['friends']]); }
function openUserProfile(userId: number) {
  const currentUser = queryClient.getQueryData<CurrentUserProfile>(['session', 'current-user']);
  useUiStore.getState().openModal({ type: 'profile', editable: currentUser?.id === userId, userId });
}
async function mutateWithRefresh(action: () => Promise<unknown>, queryClientRef: QueryClient, showError: (error: unknown) => void, queryKeys: ReadonlyArray<readonly unknown[]>, onSuccess?: () => void) { try { await action(); for (const key of queryKeys) await queryClientRef.invalidateQueries({ queryKey: [...key] }); onSuccess?.(); } catch (error) { showError(error); } }

const chatLabelMap: Record<ChatKind, string> = { PRIVATE: 'Приватный чат', GROUP: 'Групповой чат', CHANNEL: 'Канал', PROFILE: 'Чат профиля' };
const chatRoleLabelMap: Record<ChatRole, string> = { USER: 'Участник', ADMIN: 'Администратор', OWNER: 'Владелец' };
const genderLabelMap = { MALE: 'Мужской', FEMALE: 'Женский' } as const satisfies Record<NonNullable<UserProfile['gender']>, string>;

export default App;
