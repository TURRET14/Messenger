import {
  useCallback,
  useEffect,
  useState,
  type CSSProperties,
  type FormEvent,
} from "react";
import { ApiError, apiFetch, apiJson } from "./api/client";
import type { CurrentUser } from "./api/types";
import { IconUser } from "./components/Icons";
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
    setScreen({ name: "login" });
  }, []);

  if (screen.name === "loading") {
    return (
      <div
        style={{
          height: "100%",
          display: "grid",
          placeItems: "center",
          color: "var(--text-muted)",
        }}
      >
        Загрузка...
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
    width: "min(420px, 100%)",
    padding: 28,
    borderRadius: 16,
    background: "var(--bg-elevated)",
    border: "1px solid var(--border)",
    boxShadow: "0 8px 32px var(--shadow)",
  };

  const input: CSSProperties = {
    width: "100%",
    padding: "10px 12px",
    marginBottom: 12,
    borderRadius: 10,
    border: "1px solid var(--border)",
    background: "var(--bg)",
  };

  const btn: CSSProperties = {
    width: "100%",
    padding: "12px 16px",
    borderRadius: 10,
    border: "none",
    background: "var(--accent)",
    color: "#fff",
    fontWeight: 600,
    cursor: busy ? "wait" : "pointer",
  };

  const linkBtn: CSSProperties = {
    border: "none",
    background: "none",
    color: "var(--accent)",
    cursor: "pointer",
    textDecoration: "underline",
    padding: 0,
    font: "inherit",
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
          width: "min(420px, 100%)",
          justifyContent: "flex-end",
        }}
      >
        <ThemeSwitcher />
      </header>

      <div style={card}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 20,
          }}
        >
          <IconUser size={28} title="" />
          <h1 style={{ margin: 0, fontSize: "1.35rem" }}>
            {SERVICE_DISPLAY_NAME}
          </h1>
        </div>

        {screen.name === "login" ? (
          <>
            <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Вход</h2>
            <form noValidate onSubmit={(e) => void handleLogin(e)}>
              <label className="sr-only" htmlFor="login">
                Логин
              </label>
              <input
                id="login"
                style={input}
                value={login}
                onChange={(e) => {
                  setLogin(e.target.value);
                  setError(null);
                }}
                autoComplete="username"
                placeholder="Логин"
                required
                maxLength={100}
              />
              <label className="sr-only" htmlFor="password">
                Пароль
              </label>
              <input
                id="password"
                type="password"
                style={input}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError(null);
                }}
                autoComplete="current-password"
                placeholder="Пароль"
                required
                minLength={5}
                maxLength={100}
              />
              <ValidationError message={error} />
              <button type="submit" disabled={busy} style={btn}>
                Войти
              </button>
            </form>
            <p style={{ marginTop: 16, fontSize: "0.9rem", textAlign: "center" }}>
              Нет аккаунта?{" "}
              <button
                type="button"
                onClick={() => {
                  setScreen({ name: "register" });
                  setError(null);
                }}
                style={linkBtn}
              >
                Регистрация
              </button>
            </p>
            <p style={{ marginTop: 8, fontSize: "0.9rem", textAlign: "center" }}>
              <button
                type="button"
                onClick={() => {
                  setScreen({ name: "reset-request" });
                  setResetEmail(login.trim());
                  setError(null);
                }}
                style={linkBtn}
              >
                Забыли пароль?
              </button>
            </p>
          </>
        ) : null}

        {screen.name === "register" ? (
          <>
            <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Регистрация</h2>
            <form noValidate onSubmit={(e) => void handleRegisterRequest(e)}>
              <input
                style={input}
                value={regUsername}
                onChange={(e) => {
                  setRegUsername(e.target.value);
                  setError(null);
                }}
                placeholder="Имя пользователя"
                required
                maxLength={100}
              />
              <input
                style={input}
                value={regSurname}
                onChange={(e) => {
                  setRegSurname(e.target.value);
                  setError(null);
                }}
                placeholder="Фамилия (необязательно)"
                maxLength={100}
              />
              <input
                style={input}
                value={regName}
                onChange={(e) => {
                  setRegName(e.target.value);
                  setError(null);
                }}
                placeholder="Имя"
                required
                maxLength={100}
              />
              <input
                style={input}
                value={regSecond}
                onChange={(e) => {
                  setRegSecond(e.target.value);
                  setError(null);
                }}
                placeholder="Отчество (необязательно)"
                maxLength={100}
              />
              <input
                style={input}
                type="email"
                value={regEmail}
                onChange={(e) => {
                  setRegEmail(e.target.value);
                  setError(null);
                }}
                placeholder="Электронная почта"
                required
                maxLength={254}
              />
              <input
                style={input}
                value={regLogin}
                onChange={(e) => {
                  setRegLogin(e.target.value);
                  setError(null);
                }}
                placeholder="Логин для входа"
                required
                maxLength={100}
              />
              <input
                style={input}
                type="password"
                value={regPassword}
                onChange={(e) => {
                  setRegPassword(e.target.value);
                  setError(null);
                }}
                placeholder="Пароль (от 5 символов)"
                required
                minLength={5}
                maxLength={100}
              />
              <ValidationError message={error} />
              <button type="submit" disabled={busy} style={btn}>
                Отправить код на почту
              </button>
            </form>
            <p style={{ marginTop: 16, fontSize: "0.9rem", textAlign: "center" }}>
              <button
                type="button"
                onClick={() => {
                  setScreen({ name: "login" });
                  setError(null);
                }}
                style={linkBtn}
              >
                Назад ко входу
              </button>
            </p>
          </>
        ) : null}

        {screen.name === "register-code" ? (
          <>
            <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Подтверждение</h2>
            <p style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
              Введите код из письма, отправленного на {screen.email}
            </p>
            <form noValidate onSubmit={(e) => void handleRegisterComplete(e)}>
              <input
                style={input}
                value={code}
                onChange={(e) => {
                  setCode(e.target.value);
                  setError(null);
                }}
                placeholder="Код"
                required
                maxLength={100}
              />
              <ValidationError message={error} />
              <button type="submit" disabled={busy} style={btn}>
                Создать аккаунт
              </button>
            </form>
          </>
        ) : null}

        {screen.name === "reset-request" ? (
          <>
            <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Восстановление пароля</h2>
            <p style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
              Введите электронную почту аккаунта. Мы отправим код для сброса пароля.
            </p>
            <form noValidate onSubmit={(e) => void handleResetRequest(e)}>
              <input
                style={input}
                type="email"
                value={resetEmail}
                onChange={(e) => {
                  setResetEmail(e.target.value);
                  setError(null);
                }}
                placeholder="Электронная почта"
                required
                maxLength={254}
              />
              <ValidationError message={error} />
              <button type="submit" disabled={busy} style={btn}>
                Отправить код
              </button>
            </form>
            <p style={{ marginTop: 16, fontSize: "0.9rem", textAlign: "center" }}>
              <button
                type="button"
                onClick={() => {
                  setScreen({ name: "login" });
                  setError(null);
                }}
                style={linkBtn}
              >
                Назад ко входу
              </button>
            </p>
          </>
        ) : null}

        {screen.name === "reset-confirm" ? (
          <>
            <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Сброс пароля</h2>
            <p style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
              Введите код из письма, отправленного на {screen.email}, и задайте новый пароль.
            </p>
            <form noValidate onSubmit={(e) => void handleResetConfirm(e)}>
              <input
                style={input}
                value={resetCode}
                onChange={(e) => {
                  setResetCode(e.target.value);
                  setError(null);
                }}
                placeholder="Код из письма"
                required
                maxLength={100}
              />
              <input
                style={input}
                type="password"
                value={resetNewPassword}
                onChange={(e) => {
                  setResetNewPassword(e.target.value);
                  setError(null);
                }}
                placeholder="Новый пароль"
                required
                minLength={5}
                maxLength={100}
              />
              <ValidationError message={error} />
              <button type="submit" disabled={busy} style={btn}>
                Изменить пароль
              </button>
            </form>
            <p style={{ marginTop: 16, fontSize: "0.9rem", textAlign: "center" }}>
              <button
                type="button"
                onClick={() => {
                  setScreen({ name: "reset-request" });
                  setError(null);
                }}
                style={linkBtn}
              >
                Отправить код заново
              </button>
            </p>
          </>
        ) : null}
      </div>
    </div>
  );
}
