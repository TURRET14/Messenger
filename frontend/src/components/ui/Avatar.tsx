import { useEffect, useState, type CSSProperties } from "react";
import { API_BASE_URL, apiFetch } from "../../api/client";

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
    let revoked = false;
    let url: string | null = null;
    (async () => {
      try {
        const res = await apiFetch(src);
        const b = await res.blob();
        if (revoked) return;
        url = URL.createObjectURL(b);
        setBlobUrl(url);
      } catch {
        if (!revoked) setBlobUrl(null);
      }
    })();
    return () => {
      revoked = true;
      if (url) URL.revokeObjectURL(url);
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

export function userAvatarUrl(userId: number): string {
  return `${API_BASE_URL}/users/id/${userId}/avatar`;
}

export function chatAvatarUrl(chatId: number): string {
  return `${API_BASE_URL}/chats/id/${chatId}/avatar`;
}
