import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, apiFetch, apiJson } from "../api/client";
import type {
  CurrentUser,
  FriendRequest,
  FriendUser,
  UserBlockRow,
  UserInList,
} from "../api/types";
import { Avatar, userAvatarUrl } from "../components/ui/Avatar";
import { ModalChrome } from "../components/ui/ModalChrome";
import { useDialogs } from "../context/DialogsContext";
import { userListLabel } from "./userFormat";

const PAGE = 50;

type Tab =
  | "profile"
  | "users"
  | "friends"
  | "in"
  | "out"
  | "blocks";

export function MainAppMenu({
  currentUser,
  onClose,
  onOpenProfile,
  onRefreshUser,
}: {
  currentUser: CurrentUser;
  onClose: () => void;
  onOpenProfile: (userId: number) => void;
  onRefreshUser: () => Promise<void>;
}) {
  const { alert } = useDialogs();
  const [tab, setTab] = useState<Tab>("profile");

  const [u, setU] = useState<CurrentUser>(currentUser);
  const [emailNew, setEmailNew] = useState("");
  const [emailCode, setEmailCode] = useState("");

  const [users, setUsers] = useState<UserInList[]>([]);
  const [uDone, setUDone] = useState(false);
  const [uSearch, setUSearch] = useState({ mode: "username" as "username" | "names", q: "", n: "", s: "", o: "" });

  const [friends, setFriends] = useState<FriendUser[]>([]);
  const [fDone, setFDone] = useState(false);
  const [fSearch, setFSearch] = useState({ mode: "username" as "username" | "names", q: "", n: "", s: "", o: "" });

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

  const loadingRef = useRef(false);
  const uPageRef = useRef(0);
  const fPageRef = useRef(0);

  useEffect(() => {
    setU(currentUser);
  }, [currentUser]);

  const saveProfile = async () => {
    try {
      await apiFetch("/users/me", {
        method: "PATCH",
        body: JSON.stringify({
          username: u.username,
          name: u.name,
          surname: u.surname || null,
          second_name: u.second_name || null,
          date_of_birth: u.date_of_birth || null,
          gender: u.gender,
          email_address: u.email_address,
          phone_number: u.phone_number || null,
          about: u.about || null,
        }),
      });
      await onRefreshUser();
      void alert("Профиль сохранён");
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не сохранено");
    }
  };

  const requestEmailChange = async () => {
    try {
      await apiFetch("/users/me/email", {
        method: "PATCH",
        body: JSON.stringify({ email_address: emailNew }),
      });
      void alert("Код отправлен на новую почту");
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const confirmEmail = async () => {
    try {
      await apiFetch("/users/me/email/confirm", {
        method: "PATCH",
        body: JSON.stringify({ code: emailCode }),
      });
      await onRefreshUser();
      void alert("Почта обновлена");
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Неверный код");
    }
  };

  const uploadAvatar = async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    try {
      await apiFetch("/users/me/avatar", { method: "PUT", body: fd });
      await onRefreshUser();
      void alert("Фото обновлено");
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не загружено");
    }
  };

  const loadUsers = useCallback(
    async (reset: boolean) => {
      if (loadingRef.current && !reset) return;
      loadingRef.current = true;
      try {
        const mult = reset ? 0 : uPageRef.current + 1;
        let batch: UserInList[] = [];
        if (uSearch.mode === "username") {
          const q = uSearch.q.trim();
          if (!q) {
            batch = await apiJson<UserInList[]>(
              `/users?offset_multiplier=${mult}`,
            );
          } else {
            batch = await apiJson<UserInList[]>(
              `/users/search/by-username?username=${encodeURIComponent(q)}&offset_multiplier=${mult}`,
            );
          }
        } else {
          const p = new URLSearchParams();
          p.set("offset_multiplier", String(mult));
          if (uSearch.n.trim()) p.set("name", uSearch.n.trim());
          if (uSearch.s.trim()) p.set("surname", uSearch.s.trim());
          if (uSearch.o.trim()) p.set("second_name", uSearch.o.trim());
          batch = await apiJson<UserInList[]>(
            `/users/search/by-names?${p.toString()}`,
          );
        }
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
    async (reset: boolean) => {
      if (loadingRef.current && !reset) return;
      loadingRef.current = true;
      try {
        const mult = reset ? 0 : fPageRef.current + 1;
        let batch: FriendUser[] = [];
        if (fSearch.mode === "username") {
          const q = fSearch.q.trim();
          if (!q) {
            batch = await apiJson<FriendUser[]>(
              `/users/me/friends?offset_multiplier=${mult}`,
            );
          } else {
            batch = await apiJson<FriendUser[]>(
              `/users/me/friends/search/by-username?username=${encodeURIComponent(q)}&offset_multiplier=${mult}`,
            );
          }
        } else {
          const p = new URLSearchParams();
          p.set("offset_multiplier", String(mult));
          if (fSearch.n.trim()) p.set("name", fSearch.n.trim());
          if (fSearch.s.trim()) p.set("surname", fSearch.s.trim());
          if (fSearch.o.trim()) p.set("second_name", fSearch.o.trim());
          batch = await apiJson<FriendUser[]>(
            `/users/me/friends/search/by-names?${p.toString()}`,
          );
        }
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
        setIDone(batch.length < PAGE);
      } else {
        iPageRef.current = mult;
        setIncoming((prev) => {
          const ids = new Set(prev.map((x) => x.id));
          return [...prev, ...batch.filter((x) => !ids.has(x.id))];
        });
        if (batch.length < PAGE) setIDone(true);
      }
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
        setODone(batch.length < PAGE);
      } else {
        oPageRef.current = mult;
        setOutgoing((prev) => {
          const ids = new Set(prev.map((x) => x.id));
          return [...prev, ...batch.filter((x) => !ids.has(x.id))];
        });
        if (batch.length < PAGE) setODone(true);
      }
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
      for (const b of batch) {
        const uid = b.blocked_user_id;
        if (blockUsers[uid]) continue;
        void apiJson<UserInList>(`/users/id/${uid}`)
          .then((usr) =>
            setBlockUsers((p) => (p[uid] ? p : { ...p, [uid]: usr })),
          )
          .catch(() => {});
      }
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  useEffect(() => {
    if (tab === "users") void loadUsers(true);
  }, [tab]);

  useEffect(() => {
    if (tab === "friends") void loadFriends(true);
  }, [tab]);

  useEffect(() => {
    if (tab === "in") void loadIncoming(true);
  }, [tab]);

  useEffect(() => {
    if (tab === "out") void loadOutgoing(true);
  }, [tab]);

  useEffect(() => {
    if (tab === "blocks") void loadBlocks(true);
  }, [tab]);

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
    try {
      await apiFetch(`/users/me/friends/requests/received/id/${id}`, {
        method: "DELETE",
      });
      void loadIncoming(true);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const cancelSent = async (id: number) => {
    try {
      await apiFetch(`/users/me/friends/requests/sent/id/${id}`, {
        method: "DELETE",
      });
      void loadOutgoing(true);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const removeFriend = async (fid: number) => {
    try {
      await apiFetch(`/users/me/friends/${fid}`, { method: "DELETE" });
      void loadFriends(true);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const unblock = async (blockId: number) => {
    try {
      await apiFetch(`/users/me/blocks/id/${blockId}`, { method: "DELETE" });
      void loadBlocks(true);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Ошибка");
    }
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "profile", label: "Профиль" },
    { id: "users", label: "Люди" },
    { id: "friends", label: "Друзья" },
    { id: "in", label: "Заявки" },
    { id: "out", label: "Исходящие" },
    { id: "blocks", label: "Блокировки" },
  ];

  return (
    <ModalChrome title="Меню" onClose={onClose}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 6,
          marginBottom: 16,
        }}
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={tab === t.id ? "ui-btn ui-btn--primary" : "ui-btn ui-btn--ghost"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "profile" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", justifyContent: "center" }}>
            <Avatar src={userAvatarUrl(u.id)} label={u.username} size={88} />
          </div>
          <label className="sr-only" htmlFor="av">Аватар</label>
          <input
            id="av"
            type="file"
            accept="image/*"
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (f) void uploadAvatar(f);
            }}
          />
          {(
            [
              ["username", "Имя пользователя"],
              ["name", "Имя"],
              ["surname", "Фамилия"],
              ["second_name", "Отчество"],
              ["phone_number", "Телефон +…"],
              ["about", "О себе"],
            ] as const
          ).map(([key, ph]) => (
            <input
              key={key}
              className="ui-input"
              placeholder={ph}
              value={(u[key] as string) ?? ""}
              onChange={(e) => setU({ ...u, [key]: e.target.value || null })}
            />
          ))}
          <input
            className="ui-input"
            type="date"
            value={u.date_of_birth?.slice(0, 10) ?? ""}
            onChange={(e) =>
              setU({ ...u, date_of_birth: e.target.value || null })
            }
          />
          <select
            className="ui-input"
            value={u.gender ?? ""}
            onChange={(e) =>
              setU({
                ...u,
                gender: (e.target.value || null) as CurrentUser["gender"],
              })
            }
          >
            <option value="">Пол не указан</option>
            <option value="MALE">Мужской</option>
            <option value="FEMALE">Женский</option>
          </select>
          <input
            className="ui-input"
            type="email"
            value={u.email_address}
            onChange={(e) => setU({ ...u, email_address: e.target.value })}
            placeholder="Текущая почта в профиле"
          />
          <button type="button" className="ui-btn ui-btn--primary" onClick={() => void saveProfile()}>
            Сохранить профиль
          </button>
          <hr style={{ borderColor: "var(--border)" }} />
          <h3 style={{ margin: 0, fontSize: "1rem" }}>Смена почты</h3>
          <input
            className="ui-input"
            placeholder="Новая электронная почта"
            value={emailNew}
            onChange={(e) => setEmailNew(e.target.value)}
          />
          <button type="button" className="ui-btn ui-btn--ghost" onClick={() => void requestEmailChange()}>
            Отправить код на новую почту
          </button>
          <input
            className="ui-input"
            placeholder="Код из письма"
            value={emailCode}
            onChange={(e) => setEmailCode(e.target.value)}
          />
          <button type="button" className="ui-btn ui-btn--primary" onClick={() => void confirmEmail()}>
            Подтвердить почту
          </button>
        </div>
      ) : null}

      {tab === "users" ? (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              className={uSearch.mode === "username" ? "ui-btn ui-btn--primary" : "ui-btn ui-btn--ghost"}
              onClick={() => setUSearch((s) => ({ ...s, mode: "username" }))}
            >
              По username
            </button>
            <button
              type="button"
              className={uSearch.mode === "names" ? "ui-btn ui-btn--primary" : "ui-btn ui-btn--ghost"}
              onClick={() => setUSearch((s) => ({ ...s, mode: "names" }))}
            >
              По ФИО
            </button>
          </div>
          {uSearch.mode === "username" ? (
            <input
              className="ui-input"
              placeholder="Username"
              value={uSearch.q}
              onChange={(e) => setUSearch((s) => ({ ...s, q: e.target.value }))}
              style={{ marginBottom: 8 }}
            />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 8 }}>
              <input className="ui-input" placeholder="Имя" value={uSearch.n} onChange={(e) => setUSearch((s) => ({ ...s, n: e.target.value }))} />
              <input className="ui-input" placeholder="Фамилия" value={uSearch.s} onChange={(e) => setUSearch((s) => ({ ...s, s: e.target.value }))} />
              <input className="ui-input" placeholder="Отчество" value={uSearch.o} onChange={(e) => setUSearch((s) => ({ ...s, o: e.target.value }))} />
            </div>
          )}
          <button type="button" className="ui-btn ui-btn--primary" style={{ width: "100%", marginBottom: 12 }} onClick={() => void loadUsers(true)}>
            Искать / обновить
          </button>
          <div style={{ maxHeight: 360, overflowY: "auto" }}>
            {users.map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => onOpenProfile(row.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  width: "100%",
                  padding: 8,
                  marginBottom: 6,
                  borderRadius: 10,
                  border: "1px solid var(--border)",
                  background: "var(--bg)",
                  cursor: "pointer",
                  textAlign: "left",
                  color: "inherit",
                }}
              >
                <Avatar src={userAvatarUrl(row.id)} label={row.username} size={40} />
                <span style={{ fontSize: "0.9rem" }}>{userListLabel(row)}</span>
              </button>
            ))}
          </div>
          {!uDone ? (
            <button type="button" className="ui-btn ui-btn--ghost" style={{ width: "100%", marginTop: 8 }} onClick={() => void loadUsers(false)}>
              Загрузить ещё
            </button>
          ) : null}
        </div>
      ) : null}

      {tab === "friends" ? (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
            <button type="button" className={fSearch.mode === "username" ? "ui-btn ui-btn--primary" : "ui-btn ui-btn--ghost"} onClick={() => setFSearch((s) => ({ ...s, mode: "username" }))}>
              По username
            </button>
            <button type="button" className={fSearch.mode === "names" ? "ui-btn ui-btn--primary" : "ui-btn ui-btn--ghost"} onClick={() => setFSearch((s) => ({ ...s, mode: "names" }))}>
              По ФИО
            </button>
          </div>
          {fSearch.mode === "username" ? (
            <input className="ui-input" value={fSearch.q} onChange={(e) => setFSearch((s) => ({ ...s, q: e.target.value }))} style={{ marginBottom: 8 }} />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 8 }}>
              <input className="ui-input" placeholder="Имя" value={fSearch.n} onChange={(e) => setFSearch((s) => ({ ...s, n: e.target.value }))} />
              <input className="ui-input" placeholder="Фамилия" value={fSearch.s} onChange={(e) => setFSearch((s) => ({ ...s, s: e.target.value }))} />
              <input className="ui-input" placeholder="Отчество" value={fSearch.o} onChange={(e) => setFSearch((s) => ({ ...s, o: e.target.value }))} />
            </div>
          )}
          <button type="button" className="ui-btn ui-btn--primary" style={{ width: "100%", marginBottom: 12 }} onClick={() => void loadFriends(true)}>
            Обновить
          </button>
          <div style={{ maxHeight: 360, overflowY: "auto" }}>
            {friends.map((row) => (
              <div
                key={row.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 8,
                }}
              >
                <button
                  type="button"
                  onClick={() => onOpenProfile(row.id)}
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    border: "1px solid var(--border)",
                    borderRadius: 10,
                    padding: 8,
                    background: "var(--bg)",
                    cursor: "pointer",
                    textAlign: "left",
                    color: "inherit",
                  }}
                >
                  <Avatar src={userAvatarUrl(row.id)} label={row.username} size={40} />
                  <span style={{ fontSize: "0.9rem" }}>{userListLabel(row)}</span>
                </button>
                <button type="button" className="ui-btn ui-btn--danger" onClick={() => void removeFriend(row.friendship_id)}>
                  Удалить
                </button>
              </div>
            ))}
          </div>
          {!fDone ? (
            <button type="button" className="ui-btn ui-btn--ghost" style={{ width: "100%" }} onClick={() => void loadFriends(false)}>
              Ещё
            </button>
          ) : null}
        </div>
      ) : null}

      {tab === "in" ? (
        <div style={{ maxHeight: 400, overflowY: "auto" }}>
          {incoming.map((r) => (
            <div key={r.id} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
              <button type="button" className="ui-btn ui-btn--ghost" onClick={() => onOpenProfile(r.sender_user_id)}>
                От пользователя #{r.sender_user_id}
              </button>
              <button type="button" className="ui-btn ui-btn--primary" onClick={() => void acceptReq(r.id)}>
                Принять
              </button>
              <button type="button" className="ui-btn ui-btn--ghost" onClick={() => void declineReq(r.id)}>
                Отклонить
              </button>
            </div>
          ))}
          {!iDone ? (
            <button type="button" className="ui-btn ui-btn--ghost" onClick={() => void loadIncoming(false)}>
              Ещё
            </button>
          ) : null}
        </div>
      ) : null}

      {tab === "out" ? (
        <div style={{ maxHeight: 400, overflowY: "auto" }}>
          {outgoing.map((r) => (
            <div key={r.id} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
              <span>→ #{r.receiver_user_id}</span>
              <button type="button" className="ui-btn ui-btn--ghost" onClick={() => void cancelSent(r.id)}>
                Отозвать
              </button>
            </div>
          ))}
          {!oDone ? (
            <button type="button" className="ui-btn ui-btn--ghost" onClick={() => void loadOutgoing(false)}>
              Ещё
            </button>
          ) : null}
        </div>
      ) : null}

      {tab === "blocks" ? (
        <div style={{ maxHeight: 400, overflowY: "auto" }}>
          {blocks.map((b) => {
            const bu = blockUsers[b.blocked_user_id];
            return (
              <div key={b.id} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
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
                    cursor: "pointer",
                    padding: 0,
                    color: "inherit",
                    textAlign: "left",
                  }}
                >
                  <Avatar
                    src={userAvatarUrl(b.blocked_user_id)}
                    label={bu?.username ?? `#${b.blocked_user_id}`}
                    size={40}
                  />
                  <span>{bu ? userListLabel(bu) : `Пользователь ${b.blocked_user_id}`}</span>
                </button>
                <button type="button" className="ui-btn ui-btn--primary" onClick={() => void unblock(b.id)}>
                  Разблокировать
                </button>
              </div>
            );
          })}
          {!bDone ? (
            <button type="button" className="ui-btn ui-btn--ghost" onClick={() => void loadBlocks(false)}>
              Ещё
            </button>
          ) : null}
        </div>
      ) : null}
    </ModalChrome>
  );
}
