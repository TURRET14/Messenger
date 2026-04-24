import { useEffect, useState, type CSSProperties } from "react";
import { getCachedMediaUrl, peekCachedMediaUrl } from "../../media/mediaCache";

const wrap = (size: number): CSSProperties => ({
  width: size,
  height: size,
  borderRadius: "50%",
  overflow: "hidden",
  flexShrink: 0,
  background: "var(--bg-muted)",
  border: "1px solid var(--border)",
  display: "grid",
  placeItems: "center",
  fontWeight: 700,
  fontSize: size * 0.38,
  color: "var(--accent)",
  userSelect: "none",
});

export function Avatar({
  src,
  label,
  size = 40,
  alt = "",
}: {
  src: string | null;
  /** Подпись и буква-заглушка (например ФИО или имя, не username) */
  label: string;
  size?: number;
  alt?: string;
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

  if (blobUrl) {
    return (
      <div style={wrap(size)} title={alt || label}>
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
    <div style={wrap(size)} title={alt || label} aria-hidden={!alt}>
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
