import { useEffect, useState, type CSSProperties } from "react";
import { getCachedMediaUrl, peekCachedMediaUrl } from "../../media/mediaCache";

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
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!src) {
      setBlobUrl(null);
      return;
    }
    const cached = peekCachedMediaUrl(src);
    if (cached) {
      setBlobUrl(cached);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const url = await getCachedMediaUrl(src);
        if (!cancelled) setBlobUrl(url);
      } catch {
        if (!cancelled) setBlobUrl(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [src]);

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

  if (blobUrl) {
    return (
      <div style={wrapperStyle} {...(wrapperProps as object)}>
        <img
          src={blobUrl}
          alt={alt || label}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
          }}
        />
      </div>
    );
  }

  return (
    <div style={wrapperStyle} {...(wrapperProps as object)}>
      {letter}
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
