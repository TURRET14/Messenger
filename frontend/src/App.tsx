import {
  useCallback,
  useEffect,
  useState,
  type CSSProperties,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  ApiError,
  AUTH_EXPIRED_EVENT,
  apiFetch,
  apiJson,
  resetAuthExpiredLatch,
} from "./api/client";
import { clearUserCache } from "./api/userCache";
import type { CurrentUser } from "./api/types";
import {
  IconAtSign,
  IconChat,
  IconChevronLeft,
  IconKey,
  IconLock,
  IconMail,
  IconUser,
  IconUserPlus,
} from "./components/Icons";
import { ThemeSwitcher } from "./components/ThemeSwitcher";
import { ValidationError } from "./components/ui/ValidationError";
import { SERVICE_DISPLAY_NAME } from "./config";
import {
  validateCode,
  validateEmailAddress,
  validateLogin,
  validatePassword,
  validateRegisterForm,
} from "./validation";
import { MessengerApp } from "./views/MessengerApp";

type Screen =
  | { name: "loading" }
  | { name: "login" }
  | { name: "register" }
  | { name: "register-code"; email: string }
  | { name: "reset-request" }
  | { name: "reset-confirm"; email: string }
  | { name: "app"; user: CurrentUser };

type AuthScreen =
  | { name: "login" }
  | { name: "register" }
  | { name: "register-code"; email: string }
  | { name: "reset-request" }
  | { name: "reset-confirm"; email: string };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ name: "loading" });

  const checkSession = useCallback(async () => {
    try {
      const user = await apiJson<CurrentUser>("/users/me");
      setScreen({ name: "app", user });
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setScreen({ name: "login" });
      } else {
        setScreen({ name: "login" });
      }
    }
  }, []);

  useEffect(() => {
    document.title = SERVICE_DISPLAY_NAME;
  }, []);

  useEffect(() => {
    void checkSession();
  }, [checkSession]);

  const logout = useCallback(async () => {
    try {
      await apiFetch("/users/me/sessions/all", { method: "DELETE" });
    } catch {
      /* сессия могла уже истечь */
    }
    // Кеш пользователей — модульный, страница не перезагружается: чистим
    // вручную, иначе данные предыдущего аккаунта утекут в следующий вход.
    clearUserCache();
    setScreen({ name: "login" });
    resetAuthExpiredLatch();
  }, []);

  // Глобальная обработка 401: api/client стреляет CustomEvent, когда любой
  // запрос вернул «недействительный токен». Не показываем собственный
  // диалог — сообщение об ошибке уже выводится в catch-блоке вызывающего
  // кода. Просто молча возвращаемся на экран входа, чтобы пользователь
  // оказался там сразу, как только закроет уже открытый диалог.
  useEffect(() => {
    const onAuthExpired = () => {
      clearUserCache();
      setScreen({ name: "login" });
      resetAuthExpiredLatch();
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, onAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onAuthExpired);
  }, []);

  if (screen.name === "loading") {
    return (
      <div
        style={{
          height: "100%",
          display: "grid",
          placeItems: "center",
        }}
      >
        <span className="ui-spinner ui-spinner--xl" aria-hidden="true" />
      </div>
    );
  }

  if (screen.name === "app") {
    return (
      <MessengerApp currentUser={screen.user} onLogout={() => void logout()} />
    );
  }

  return (
    <AuthShell
      screen={screen as AuthScreen}
      onLoggedIn={() => void checkSession()}
      setScreen={setScreen}
    />
  );
}

const inputIconWrap: CSSProperties = {
  position: "relative",
  display: "block",
};

const iconInside: CSSProperties = {
  position: "absolute",
  left: 12,
  top: "50%",
  transform: "translateY(-50%)",
  color: "var(--text-subtle)",
  pointerEvents: "none",
};

const inputWithIconStyle: CSSProperties = {
  paddingLeft: 38,
};

function FieldWithIcon({
  icon,
  children,
}: {
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <div style={inputIconWrap}>
      <span style={iconInside}>{icon}</span>
      {children}
    </div>
  );
}

function AuthShell({
  screen,
  onLoggedIn,
  setScreen,
}: {
  screen: AuthScreen;
  onLoggedIn: () => void;
  setScreen: (s: Screen) => void;
}) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [regUsername, setRegUsername] = useState("");
  const [regName, setRegName] = useState("");
  const [regSurname, setRegSurname] = useState("");
  const [regSecond, setRegSecond] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regLogin, setRegLogin] = useState("");
  const [regPassword, setRegPassword] = useState("");

  const [code, setCode] = useState("");
  const [resetEmail, setResetEmail] = useState("");
  const [resetCode, setResetCode] = useState("");
  const [resetNewPassword, setResetNewPassword] = useState("");

  // Очищаем ошибки при смене экрана
  useEffect(() => {
    setError(null);
  }, [screen.name]);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();

    const loginError = validateLogin(login);
    if (loginError) {
      setError(loginError);
      return;
    }

    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    setError(null);
    setBusy(true);
    try {
      await apiFetch("/login", {
        method: "POST",
        body: JSON.stringify({ login: login.trim(), password }),
      });
      onLoggedIn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка входа");
    } finally {
      setBusy(false);
    }
  };

  const handleRegisterRequest = async (e: FormEvent) => {
    e.preventDefault();

    const validationError = validateRegisterForm({
      username: regUsername,
      name: regName,
      surname: regSurname,
      secondName: regSecond,
      email: regEmail,
      login: regLogin,
      password: regPassword,
    });
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setBusy(true);
    try {
      await apiFetch("/users/register", {
        method: "POST",
        body: JSON.stringify({
          username: regUsername.trim(),
          name: regName.trim(),
          surname: regSurname.trim() || null,
          second_name: regSecond.trim() || null,
          email_address: regEmail.trim(),
          login: regLogin.trim(),
          password: regPassword,
        }),
      });
      setScreen({ name: "register-code", email: regEmail.trim() });
      setCode("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка регистрации");
    } finally {
      setBusy(false);
    }
  };

  const handleRegisterComplete = async (e: FormEvent) => {
    e.preventDefault();
    if (screen.name !== "register-code") return;

    const codeError = validateCode(code);
    if (codeError) {
      setError(codeError);
      return;
    }

    setError(null);
    setBusy(true);
    try {
      await apiFetch("/users", {
        method: "POST",
        body: JSON.stringify({ code: code.trim() }),
      });
      setScreen({ name: "login" });
      setLogin(regLogin.trim());
      setPassword(regPassword);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Неверный код или ошибка");
    } finally {
      setBusy(false);
    }
  };

  const handleResetRequest = async (e: FormEvent) => {
    e.preventDefault();

    const emailError = validateEmailAddress(resetEmail, "Электронная почта");
    if (emailError) {
      setError(emailError);
      return;
    }

    setError(null);
    setBusy(true);
    try {
      await apiFetch("/users/password/reset", {
        method: "POST",
        body: JSON.stringify({ email_address: resetEmail.trim() }),
      });
      setScreen({ name: "reset-confirm", email: resetEmail.trim() });
      setResetCode("");
      setResetNewPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось отправить код");
    } finally {
      setBusy(false);
    }
  };

  const handleResetConfirm = async (e: FormEvent) => {
    e.preventDefault();

    const codeError = validateCode(resetCode);
    if (codeError) {
      setError(codeError);
      return;
    }

    const passwordError = validatePassword(resetNewPassword, "Новый пароль");
    if (passwordError) {
      setError(passwordError);
      return;
    }

    setError(null);
    setBusy(true);
    try {
      await apiFetch("/users/password/reset/confirm", {
        method: "POST",
        body: JSON.stringify({
          code: resetCode.trim(),
          new_password: resetNewPassword,
        }),
      });
      setScreen({ name: "login" });
      setPassword("");
      setResetCode("");
      setResetNewPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось изменить пароль");
    } finally {
      setBusy(false);
    }
  };

  const card: CSSProperties = {
    width: "min(440px, 100%)",
    padding: 28,
    borderRadius: 18,
    background: "var(--bg-elevated)",
    border: "1px solid var(--border)",
  };

  const linkBtn: CSSProperties = {
    border: "none",
    background: "none",
    color: "var(--accent)",
    cursor: "pointer",
    padding: 0,
    font: "inherit",
    fontWeight: 600,
  };

  const subtleLink: CSSProperties = {
    border: "none",
    background: "none",
    color: "var(--text-muted)",
    cursor: "pointer",
    padding: 0,
    font: "inherit",
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
  };

  const formStack: CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  };

  const sectionTitle: CSSProperties = {
    margin: "0 0 6px",
    fontSize: "1.35rem",
    fontWeight: 700,
  };

  const subHelp: CSSProperties = {
    margin: "0 0 18px",
    fontSize: "0.92rem",
    color: "var(--text-muted)",
  };

  return (
    <div
      style={{
        minHeight: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "32px 16px",
        gap: 20,
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          width: "min(440px, 100%)",
          justifyContent: "space-between",
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            color: "var(--text)",
            fontWeight: 700,
          }}
        >
          <IconChat size={22} />
          <span>{SERVICE_DISPLAY_NAME}</span>
        </div>
        <ThemeSwitcher />
      </header>

      <div style={card} className="anim-slide-up">
        {screen.name === "login" ? (
          <>
            <h1 style={sectionTitle}>Вход в аккаунт</h1>
            <p style={subHelp}>Войдите, чтобы открыть свои чаты.</p>
            <form noValidate onSubmit={(e) => void handleLogin(e)} style={formStack}>
              <label className="ui-field">
                <span className="ui-field-label">Логин</span>
                <FieldWithIcon icon={<IconUser size={18} />}>
                  <input
                    className="ui-input"
                    style={inputWithIconStyle}
                    value={login}
                    onChange={(e) => {
                      setLogin(e.target.value);
                      setError(null);
                    }}
                    autoComplete="username"
                    placeholder="Ваш логин"
                    required
                    maxLength={100}
                  />
                </FieldWithIcon>
              </label>
              <label className="ui-field">
                <span className="ui-field-label">Пароль</span>
                <FieldWithIcon icon={<IconLock size={18} />}>
                  <input
                    type="password"
                    className="ui-input"
                    style={inputWithIconStyle}
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      setError(null);
                    }}
                    autoComplete="current-password"
                    placeholder="Минимум 5 символов"
                    required
                    minLength={5}
                    maxLength={100}
                  />
                </FieldWithIcon>
              </label>
              <ValidationError message={error} />
              <button
                type="submit"
                disabled={busy}
                className="ui-btn ui-btn--primary ui-btn--lg ui-btn--block"
              >
                {busy ? <span className="ui-spinner" aria-hidden="true" /> : null}
                {busy ? "Входим…" : "Войти"}
              </button>
            </form>
            <div
              style={{
                marginTop: 16,
                display: "flex",
                flexDirection: "column",
                gap: 10,
                fontSize: "0.92rem",
                textAlign: "center",
              }}
            >
              <div>
                Нет аккаунта?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setScreen({ name: "register" });
                    setError(null);
                  }}
                  style={linkBtn}
                >
                  Зарегистрироваться
                </button>
              </div>
              <div>
                <button
                  type="button"
                  onClick={() => {
                    setScreen({ name: "reset-request" });
                    setResetEmail("");
                    setError(null);
                  }}
                  style={subtleLink}
                >
                  <IconKey size={14} /> Забыли пароль?
                </button>
              </div>
            </div>
          </>
        ) : null}

        {screen.name === "register" ? (
          <>
            <h1 style={sectionTitle}>Регистрация</h1>
            <p style={subHelp}>Создайте новый аккаунт за пару минут.</p>
            <form
              noValidate
              onSubmit={(e) => void handleRegisterRequest(e)}
              style={formStack}
            >
              <label className="ui-field">
                <span className="ui-field-label">Имя пользователя</span>
                <FieldWithIcon icon={<IconAtSign size={18} />}>
                  <input
                    className="ui-input"
                    style={inputWithIconStyle}
                    value={regUsername}
                    onChange={(e) => {
                      setRegUsername(e.target.value);
                      setError(null);
                    }}
                    placeholder="Уникальное имя в системе"
                    required
                    maxLength={100}
                  />
                </FieldWithIcon>
              </label>

              <div
                style={{
                  display: "grid",
                  gap: 12,
                  gridTemplateColumns: "1fr 1fr",
                }}
              >
                <label className="ui-field">
                  <span className="ui-field-label">Фамилия</span>
                  <input
                    className="ui-input"
                    value={regSurname}
                    onChange={(e) => {
                      setRegSurname(e.target.value);
                      setError(null);
                    }}
                    placeholder="Не обязательно"
                    maxLength={100}
                  />
                </label>
                <label className="ui-field">
                  <span className="ui-field-label">Имя</span>
                  <input
                    className="ui-input"
                    value={regName}
                    onChange={(e) => {
                      setRegName(e.target.value);
                      setError(null);
                    }}
                    required
                    maxLength={100}
                  />
                </label>
              </div>
              <label className="ui-field">
                <span className="ui-field-label">Отчество</span>
                <input
                  className="ui-input"
                  value={regSecond}
                  onChange={(e) => {
                    setRegSecond(e.target.value);
                    setError(null);
                  }}
                  placeholder="Не обязательно"
                  maxLength={100}
                />
              </label>

              <label className="ui-field">
                <span className="ui-field-label">Электронная почта</span>
                <FieldWithIcon icon={<IconMail size={18} />}>
                  <input
                    className="ui-input"
                    style={inputWithIconStyle}
                    type="email"
                    value={regEmail}
                    onChange={(e) => {
                      setRegEmail(e.target.value);
                      setError(null);
                    }}
                    autoComplete="email"
                    required
                    maxLength={254}
                  />
                </FieldWithIcon>
              </label>

              <label className="ui-field">
                <span className="ui-field-label">Логин для входа</span>
                <FieldWithIcon icon={<IconUser size={18} />}>
                  <input
                    className="ui-input"
                    style={inputWithIconStyle}
                    value={regLogin}
                    onChange={(e) => {
                      setRegLogin(e.target.value);
                      setError(null);
                    }}
                    autoComplete="username"
                    required
                    maxLength={100}
                  />
                </FieldWithIcon>
              </label>

              <label className="ui-field">
                <span className="ui-field-label">Пароль</span>
                <FieldWithIcon icon={<IconLock size={18} />}>
                  <input
                    className="ui-input"
                    style={inputWithIconStyle}
                    type="password"
                    value={regPassword}
                    onChange={(e) => {
                      setRegPassword(e.target.value);
                      setError(null);
                    }}
                    autoComplete="new-password"
                    placeholder="Минимум 5 символов"
                    required
                    minLength={5}
                    maxLength={100}
                  />
                </FieldWithIcon>
              </label>

              <ValidationError message={error} />
              <button
                type="submit"
                disabled={busy}
                className="ui-btn ui-btn--primary ui-btn--lg ui-btn--block"
              >
                {busy ? <span className="ui-spinner" aria-hidden="true" /> : null}
                <IconUserPlus size={18} />
                {busy ? "Отправляем…" : "Отправить код на почту"}
              </button>
            </form>
            <div
              style={{
                marginTop: 16,
                fontSize: "0.92rem",
                textAlign: "center",
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setScreen({ name: "login" });
                  setError(null);
                }}
                style={subtleLink}
              >
                <IconChevronLeft size={14} /> Назад ко входу
              </button>
            </div>
          </>
        ) : null}

        {screen.name === "register-code" ? (
          <>
            <h1 style={sectionTitle}>Подтверждение</h1>
            <p style={subHelp}>
              Мы отправили 6-значный код на <strong>{screen.email}</strong>.
              Введите его ниже, чтобы завершить регистрацию.
            </p>
            <form
              noValidate
              onSubmit={(e) => void handleRegisterComplete(e)}
              style={formStack}
            >
              <label className="ui-field">
                <span className="ui-field-label">Код из письма</span>
                <input
                  className="ui-input"
                  value={code}
                  onChange={(e) => {
                    setCode(e.target.value);
                    setError(null);
                  }}
                  placeholder="6 цифр"
                  autoComplete="one-time-code"
                  inputMode="numeric"
                  required
                  maxLength={100}
                  autoFocus
                />
              </label>
              <ValidationError message={error} />
              <button
                type="submit"
                disabled={busy}
                className="ui-btn ui-btn--primary ui-btn--lg ui-btn--block"
              >
                {busy ? <span className="ui-spinner" aria-hidden="true" /> : null}
                {busy ? "Создаём аккаунт…" : "Создать аккаунт"}
              </button>
            </form>
            <div
              style={{
                marginTop: 16,
                fontSize: "0.92rem",
                textAlign: "center",
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setScreen({ name: "register" });
                  setError(null);
                }}
                style={subtleLink}
              >
                <IconChevronLeft size={14} /> Изменить данные
              </button>
            </div>
          </>
        ) : null}

        {screen.name === "reset-request" ? (
          <>
            <h1 style={sectionTitle}>Восстановление пароля</h1>
            <p style={subHelp}>
              Укажите электронную почту аккаунта — отправим вам код для сброса
              пароля.
            </p>
            <form
              noValidate
              onSubmit={(e) => void handleResetRequest(e)}
              style={formStack}
            >
              <label className="ui-field">
                <span className="ui-field-label">Электронная почта</span>
                <FieldWithIcon icon={<IconMail size={18} />}>
                  <input
                    className="ui-input"
                    style={inputWithIconStyle}
                    type="email"
                    value={resetEmail}
                    onChange={(e) => {
                      setResetEmail(e.target.value);
                      setError(null);
                    }}
                    autoComplete="email"
                    required
                    maxLength={254}
                  />
                </FieldWithIcon>
              </label>
              <ValidationError message={error} />
              <button
                type="submit"
                disabled={busy}
                className="ui-btn ui-btn--primary ui-btn--lg ui-btn--block"
              >
                {busy ? <span className="ui-spinner" aria-hidden="true" /> : null}
                {busy ? "Отправляем…" : "Отправить код"}
              </button>
            </form>
            <div
              style={{
                marginTop: 16,
                fontSize: "0.92rem",
                textAlign: "center",
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setScreen({ name: "login" });
                  setError(null);
                }}
                style={subtleLink}
              >
                <IconChevronLeft size={14} /> Назад ко входу
              </button>
            </div>
          </>
        ) : null}

        {screen.name === "reset-confirm" ? (
          <>
            <h1 style={sectionTitle}>Сброс пароля</h1>
            <p style={subHelp}>
              Введите код из письма, отправленного на{" "}
              <strong>{screen.email}</strong>, и задайте новый пароль.
            </p>
            <form
              noValidate
              onSubmit={(e) => void handleResetConfirm(e)}
              style={formStack}
            >
              <label className="ui-field">
                <span className="ui-field-label">Код из письма</span>
                <input
                  className="ui-input"
                  value={resetCode}
                  onChange={(e) => {
                    setResetCode(e.target.value);
                    setError(null);
                  }}
                  placeholder="6 цифр"
                  autoComplete="one-time-code"
                  inputMode="numeric"
                  required
                  maxLength={100}
                  autoFocus
                />
              </label>
              <label className="ui-field">
                <span className="ui-field-label">Новый пароль</span>
                <FieldWithIcon icon={<IconLock size={18} />}>
                  <input
                    type="password"
                    className="ui-input"
                    style={inputWithIconStyle}
                    value={resetNewPassword}
                    onChange={(e) => {
                      setResetNewPassword(e.target.value);
                      setError(null);
                    }}
                    autoComplete="new-password"
                    placeholder="Минимум 5 символов"
                    required
                    minLength={5}
                    maxLength={100}
                  />
                </FieldWithIcon>
              </label>
              <ValidationError message={error} />
              <button
                type="submit"
                disabled={busy}
                className="ui-btn ui-btn--primary ui-btn--lg ui-btn--block"
              >
                {busy ? <span className="ui-spinner" aria-hidden="true" /> : null}
                {busy ? "Сохраняем…" : "Изменить пароль"}
              </button>
            </form>
            <div
              style={{
                marginTop: 16,
                fontSize: "0.92rem",
                textAlign: "center",
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setScreen({ name: "reset-request" });
                  setError(null);
                }}
                style={subtleLink}
              >
                Отправить код заново
              </button>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
