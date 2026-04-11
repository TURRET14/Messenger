import {
  useCallback,
  useEffect,
  useState,
  type CSSProperties,
  type FormEvent,
} from "react";
import { ApiError, apiFetch, apiJson } from "./api/client";
import type { CurrentUser } from "./api/types";
import { SERVICE_DISPLAY_NAME } from "./config";
import { IconUser } from "./components/Icons";
import { ThemeSwitcher } from "./components/ThemeSwitcher";
import { MessengerApp } from "./views/MessengerApp";

type Screen =
  | { name: "loading" }
  | { name: "login" }
  | { name: "register" }
  | { name: "register-code"; email: string }
  | { name: "app"; user: CurrentUser };

type AuthScreen =
  | { name: "login" }
  | { name: "register" }
  | { name: "register-code"; email: string };

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
        Загрузка…
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

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiFetch("/login", {
        method: "POST",
        body: JSON.stringify({ login, password }),
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
    setError(null);
    setBusy(true);
    try {
      await apiFetch("/users/register", {
        method: "POST",
        body: JSON.stringify({
          username: regUsername,
          name: regName,
          surname: regSurname || null,
          second_name: regSecond || null,
          email_address: regEmail,
          login: regLogin,
          password: regPassword,
        }),
      });
      setScreen({ name: "register-code", email: regEmail });
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
    setError(null);
    setBusy(true);
    try {
      await apiFetch("/users", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      setScreen({ name: "login" });
      setLogin(regLogin);
      setPassword(regPassword);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Неверный код или ошибка",
      );
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
            <form onSubmit={(e) => void handleLogin(e)}>
              <label className="sr-only" htmlFor="login">
                Логин
              </label>
              <input
                id="login"
                style={input}
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                autoComplete="username"
                placeholder="Логин"
                required
              />
              <label className="sr-only" htmlFor="password">
                Пароль
              </label>
              <input
                id="password"
                type="password"
                style={input}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                placeholder="Пароль"
                required
                minLength={5}
              />
              {error ? (
                <p style={{ color: "var(--danger)", fontSize: "0.9rem" }}>
                  {error}
                </p>
              ) : null}
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
                style={{
                  border: "none",
                  background: "none",
                  color: "var(--accent)",
                  cursor: "pointer",
                  textDecoration: "underline",
                  padding: 0,
                  font: "inherit",
                }}
              >
                Регистрация
              </button>
            </p>
          </>
        ) : null}

        {screen.name === "register" ? (
          <>
            <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Регистрация</h2>
            <form onSubmit={(e) => void handleRegisterRequest(e)}>
              <input
                style={input}
                value={regUsername}
                onChange={(e) => setRegUsername(e.target.value)}
                placeholder="Имя пользователя (username)"
                required
                maxLength={100}
              />
              <input
                style={input}
                value={regName}
                onChange={(e) => setRegName(e.target.value)}
                placeholder="Имя"
                required
                maxLength={100}
              />
              <input
                style={input}
                value={regSurname}
                onChange={(e) => setRegSurname(e.target.value)}
                placeholder="Фамилия (необязательно)"
                maxLength={100}
              />
              <input
                style={input}
                value={regSecond}
                onChange={(e) => setRegSecond(e.target.value)}
                placeholder="Отчество (необязательно)"
                maxLength={100}
              />
              <input
                style={input}
                type="email"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                placeholder="Электронная почта"
                required
              />
              <input
                style={input}
                value={regLogin}
                onChange={(e) => setRegLogin(e.target.value)}
                placeholder="Логин для входа"
                required
                maxLength={100}
              />
              <input
                style={input}
                type="password"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                placeholder="Пароль (от 5 символов)"
                required
                minLength={5}
                maxLength={100}
              />
              {error ? (
                <p style={{ color: "var(--danger)", fontSize: "0.9rem" }}>
                  {error}
                </p>
              ) : null}
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
                style={{
                  border: "none",
                  background: "none",
                  color: "var(--accent)",
                  cursor: "pointer",
                  textDecoration: "underline",
                  padding: 0,
                  font: "inherit",
                }}
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
            <form onSubmit={(e) => void handleRegisterComplete(e)}>
              <input
                style={input}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Код"
                required
                maxLength={100}
              />
              {error ? (
                <p style={{ color: "var(--danger)", fontSize: "0.9rem" }}>
                  {error}
                </p>
              ) : null}
              <button type="submit" disabled={busy} style={btn}>
                Создать аккаунт
              </button>
            </form>
          </>
        ) : null}
      </div>
    </div>
  );
}
