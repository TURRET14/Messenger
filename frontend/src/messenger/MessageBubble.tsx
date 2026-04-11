import { useEffect, useState } from "react";
import { ApiError, apiFetch, apiJson } from "../api/client";
import type { Message } from "../api/types";
import { IconPaperclip, IconX } from "../components/Icons";
import { Avatar, userAvatarUrl } from "../components/ui/Avatar";
import { useDialogs } from "../context/DialogsContext";
import { previewKind } from "./attachmentUtils";

export interface AttachmentMeta {
  id: number;
  message_id: number;
  chat_id: number;
  file_extension: string;
}

export function MessageBubble({
  m,
  chatId: _chatId,
  currentUserId,
  displaySender,
  replySnippet,
  replySenderLabel,
  onReply,
  onEdit,
  onDelete,
  onOpenComments,
  canOpenComments,
  showReadReceipt,
  readLabel,
  interactive,
  avatarEpoch = 0,
}: {
  m: Message;
  /** @deprecated Используется m.chat_id для API */
  chatId: number;
  currentUserId: number;
  displaySender: string;
  replySnippet?: string | null;
  replySenderLabel?: string | null;
  onReply?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onOpenComments?: () => void;
  canOpenComments?: boolean;
  showReadReceipt?: boolean;
  readLabel?: string;
  interactive?: boolean;
  avatarEpoch?: number;
}) {
  const { alert } = useDialogs();
  const cid = m.chat_id;
  const [atts, setAtts] = useState<AttachmentMeta[] | null>(null);
  const [blobMap, setBlobMap] = useState<Record<number, string>>({});

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await apiJson<AttachmentMeta[]>(
          `/chats/id/${cid}/messages/id/${m.id}/attachments`,
        );
        if (!cancelled) setAtts(list);
      } catch {
        if (!cancelled) setAtts([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cid, m.id]);

  useEffect(() => {
    return () => {
      for (const u of Object.values(blobMap)) URL.revokeObjectURL(u);
    };
  }, []);

  const openBlob = async (att: AttachmentMeta) => {
    try {
      const res = await apiFetch(
        `/chats/id/${cid}/messages/id/${m.id}/attachments/id/${att.id}`,
      );
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалось открыть файл");
    }
  };

  const ensureBlob = async (att: AttachmentMeta) => {
    if (blobMap[att.id]) return blobMap[att.id];
    const res = await apiFetch(
      `/chats/id/${cid}/messages/id/${m.id}/attachments/id/${att.id}`,
    );
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    setBlobMap((prev) => ({ ...prev, [att.id]: url }));
    return url;
  };

  const mine = m.sender_user_id === currentUserId;
  const edited =
    m.date_and_time_edited &&
    m.date_and_time_edited !== m.date_and_time_sent;

  return (
    <article
      style={{
        alignSelf: mine ? "flex-end" : "flex-start",
        maxWidth: "min(560px, 94%)",
        padding: "10px 14px",
        borderRadius: 14,
        background: "var(--bg-elevated)",
        border: "1px solid var(--border)",
        boxShadow: "0 1px 2px var(--shadow)",
      }}
    >
      {m.reply_message_id && (replySnippet != null || replySenderLabel) ? (
        <div
          style={{
            fontSize: "0.8rem",
            color: "var(--text-muted)",
            borderLeft: "3px solid var(--accent)",
            paddingLeft: 8,
            marginBottom: 8,
          }}
        >
          {replySenderLabel ? (
            <strong style={{ color: "var(--text)" }}>{replySenderLabel}</strong>
          ) : null}
          {replySenderLabel ? <br /> : null}
          <span style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {replySnippet ?? "…"}
          </span>
        </div>
      ) : null}

      <div
        style={{
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          marginBottom: 6,
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        {m.sender_user_id != null ? (
          <Avatar
            src={userAvatarUrl(m.sender_user_id, avatarEpoch)}
            label={displaySender}
            size={28}
            alt=""
          />
        ) : null}
        <span>{displaySender}</span>
        <time dateTime={m.date_and_time_sent}>
          {new Date(m.date_and_time_sent).toLocaleString()}
        </time>
        {edited ? (
          <span title="Изменено">
            · изм. {new Date(m.date_and_time_edited!).toLocaleString()}
          </span>
        ) : null}
        {mine && showReadReceipt && readLabel ? (
          <span style={{ marginLeft: "auto", fontWeight: 600 }}>{readLabel}</span>
        ) : null}
      </div>

      <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
        {m.message_text ?? (
          <em style={{ color: "var(--text-muted)" }}>без текста</em>
        )}
      </div>

      {atts && atts.length > 0 ? (
        <div
          style={{
            marginTop: 10,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {atts.map((att) => (
            <AttachmentPreview
              key={att.id}
              att={att}
              getBlob={() => ensureBlob(att)}
              onOpen={() => void openBlob(att)}
            />
          ))}
        </div>
      ) : null}

      {interactive !== false ? (
        <div
          style={{
            marginTop: 8,
            display: "flex",
            flexWrap: "wrap",
            gap: 6,
          }}
        >
          {onReply ? (
            <button type="button" className="ui-btn ui-btn--ghost" onClick={onReply}>
              Ответить
            </button>
          ) : null}
          {onEdit ? (
            <button type="button" className="ui-btn ui-btn--ghost" onClick={onEdit}>
              Изменить
            </button>
          ) : null}
          {onDelete ? (
            <button type="button" className="ui-btn ui-btn--ghost" onClick={onDelete}>
              Удалить
            </button>
          ) : null}
          {canOpenComments && onOpenComments ? (
            <button
              type="button"
              className="ui-btn ui-btn--ghost"
              onClick={onOpenComments}
            >
              Комментарии
            </button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function AttachmentPreview({
  att,
  getBlob,
  onOpen,
}: {
  att: AttachmentMeta;
  getBlob: () => Promise<string>;
  onOpen: () => void;
}) {
  const kind = previewKind(att.file_extension || "");
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (kind === "file") return;
    let alive = true;
    void (async () => {
      try {
        const u = await getBlob();
        if (alive) setUrl(u);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      alive = false;
    };
  }, [att.id, kind, getBlob]);

  return (
    <div
      style={{
        borderRadius: 10,
        border: "1px solid var(--border)",
        overflow: "hidden",
        background: "var(--bg-muted)",
      }}
    >
      {kind === "image" && url ? (
        <button
          type="button"
          onClick={onOpen}
          style={{
            padding: 0,
            border: "none",
            background: "none",
            cursor: "pointer",
            display: "block",
            width: "100%",
          }}
        >
          <img
            src={url}
            alt=""
            style={{ maxHeight: 220, width: "100%", objectFit: "contain" }}
          />
        </button>
      ) : null}
      {kind === "video" && url ? (
        <video
          src={url}
          controls
          style={{ maxHeight: 220, width: "100%" }}
        />
      ) : null}
      {kind === "audio" && url ? (
        <audio src={url} controls style={{ width: "100%" }} />
      ) : null}
      <div
        style={{
          padding: 8,
          display: "flex",
          alignItems: "center",
          gap: 8,
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          <IconPaperclip size={14} /> Вложение {att.id}
          {att.file_extension ? ` (${att.file_extension})` : ""}
        </span>
        <button type="button" className="ui-btn ui-btn--ghost" onClick={onOpen}>
          Открыть
        </button>
      </div>
    </div>
  );
}

export function PickedFilesStrip({
  files,
  onRemove,
}: {
  files: File[];
  onRemove: (index: number) => void;
}) {
  if (files.length === 0) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
      {files.map((f, i) => (
        <div
          key={`${f.name}-${f.size}-${i}-${f.lastModified}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "6px 10px",
            borderRadius: 20,
            background: "var(--bg-muted)",
            border: "1px solid var(--border)",
            fontSize: "0.8rem",
          }}
        >
          <span className="sr-only">Файл</span>
          {f.name}
          <button
            type="button"
            aria-label="Убрать вложение"
            title="Убрать"
            onClick={() => onRemove(i)}
            style={{
              border: "none",
              background: "none",
              padding: 2,
              cursor: "pointer",
              color: "var(--danger)",
              display: "inline-flex",
            }}
          >
            <IconX size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
