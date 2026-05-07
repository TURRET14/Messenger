import { useState, type CSSProperties } from "react";
import { apiUrl } from "../../api/client";

const wrap = (size: number, clickable: boolean): CSSProperties => ({
  width: size,
  height: size,
  borderRadius: "50%",
  overflow: "hidden",
  flexShrink: 0,
  background: "var(--bg-muted)",
  border: `${size >= 64 ? 2 : 1.5}px solid var(--border-strong)`,
  display: "grid",
  placeItems: "center",
  fontWeight: 700,
  fontSize: size * 0.40,
  color: "var(--accent)",
  userSelect: "none",
  cursor: clickable ? "pointer" : "default",
  transition: clickable ? "transform 100ms ease, border-color 120ms ease" : undefined,
});

/**
 * Аватар с буквой-заглушкой. Картинка загружается напрямую браузером через
 * <img src=...>: HTTP-кеш используется автоматически, прогрессивное
 * декодирование работает (для progressive JPEG/WebP), память не дублируется
 * в JS-куче.
 */
export function Avatar({
  src,
  label,
  size = 40,
  alt = "",
  onClick,
}: {
  src: string | null;
  /** Подпись и буква-заглушка (например ФИО или имя, не username) */
  label: string;
  size?: number;
  alt?: string;
  onClick?: () => void;
}) {
  const [failed, setFailed] = useState(false);
  const letter = (label.trim()[0] ?? "?").toUpperCase();

  const wrapperStyle = wrap(size, !!onClick);
  const wrapperProps = onClick
    ? {
        role: "button" as const,
        tabIndex: 0,
        onClick,
        onKeyDown: (e: React.KeyboardEvent) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
          }
        },
        title: alt || label,
      }
    : { title: alt || label, "aria-hidden": (!alt) as boolean };

  const showImage = src && !failed;

  return (
    <div style={wrapperStyle} {...(wrapperProps as object)}>
      {showImage ? (
        <img
          src={apiUrl(src)}
          alt={alt || label}
          loading="lazy"
          decoding="async"
          draggable={false}
          onError={() => setFailed(true)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
          }}
        />
      ) : (
        letter
      )}
    </div>
  );
}

/** Путь для apiFetch (без хоста — buildUrl добавит VITE_API_BASE_URL) */
export function userAvatarUrl(userId: number, cacheBust = 0): string {
  const u = `/users/id/${userId}/avatar`;
  return cacheBust ? `${u}?v=${cacheBust}` : u;
}

export function chatAvatarUrl(chatId: number, cacheBust = 0): string {
  const u = `/chats/id/${chatId}/avatar`;
  return cacheBust ? `${u}?v=${cacheBust}` : u;
}
