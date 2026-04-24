import { useEffect, useState } from "react";
import { ApiError, apiJson } from "../api/client";
import type { Message } from "../api/types";
import { IconPaperclip, IconX } from "../components/Icons";
import { ActionMenu, type ActionMenuItem } from "../components/ui/ActionMenu";
import { Avatar, userAvatarUrl } from "../components/ui/Avatar";
import { useDialogs } from "../context/DialogsContext";
import { getCachedMediaUrl, peekCachedMediaUrl } from "../media/mediaCache";
import { previewKind } from "./attachmentUtils";

export interface AttachmentMeta {
  id: number;
  message_id: number;
  chat_id: number;
  file_extension: string;
}

export interface PickedFileItem {
  id: number;
  file: File;
}

const attachmentListCache = new Map<string, AttachmentMeta[]>();
const attachmentListPromiseCache = new Map<string, Promise<AttachmentMeta[]>>();

async function getCachedAttachmentList(chatId: number, messageId: number): Promise<AttachmentMeta[]> {
  const key = `${chatId}:${messageId}`;
  const cached = attachmentListCache.get(key);
  if (cached) return cached;

  const pending = attachmentListPromiseCache.get(key);
  if (pending) return pending;

  const promise = apiJson<AttachmentMeta[]>(
    `/chats/id/${chatId}/messages/id/${messageId}/attachments`,
  );
  attachmentListPromiseCache.set(key, promise);

  try {
    const list = await promise;
    attachmentListCache.set(key, list);
    return list;
  } finally {
    attachmentListPromiseCache.delete(key);
  }
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
        const list = await getCachedAttachmentList(cid, m.id);
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
    setBlobMap({});
  }, [cid, m.id]);

  const ensureBlob = async (att: AttachmentMeta) => {
    const path = `/chats/id/${cid}/messages/id/${m.id}/attachments/id/${att.id}`;
    const cachedBlob = peekCachedMediaUrl(path);
    if (cachedBlob) return cachedBlob;
    return await getCachedMediaUrl(path);
  };

  useEffect(() => {
    if (!atts) return;

    for (const att of atts) {
      if (previewKind(att.file_extension || "") === "file") continue;
      void ensureBlob(att).then((url) => {
        setBlobMap((prev) => (prev[att.id] === url ? prev : { ...prev, [att.id]: url }));
      });
    }
  }, [atts]);

  const openBlob = async (att: AttachmentMeta) => {
    try {
      const url = await ensureBlob(att);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (e) {
      void alert(e instanceof ApiError ? e.message : "Не удалось открыть файл");
    }
  };

  const mine = m.sender_user_id === currentUserId;
  const edited =
    m.date_and_time_edited &&
    m.date_and_time_edited !== m.date_and_time_sent;
  const actionItems: ActionMenuItem[] =
    interactive === false
      ? []
      : [
          ...(onReply ? [{ label: "Ответить", onSelect: onReply }] : []),
          ...(onEdit ? [{ label: "Изменить", onSelect: onEdit }] : []),
          ...(canOpenComments && onOpenComments
            ? [{ label: "Комментарии", onSelect: onOpenComments }]
            : []),
          ...(onDelete
            ? [{ label: "Удалить", onSelect: onDelete, danger: true }]
            : []),
        ];

  return (
    <ActionMenu items={actionItems} label="Действия с сообщением">
      {({ button, onContextMenu }) => (
        <article
          onContextMenu={onContextMenu}
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
                <strong style={{ color: "var(--text)" }}>
                  {replySenderLabel}
                </strong>
              ) : null}
              {replySenderLabel ? <br /> : null}
              <span style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                {replySnippet ?? "..."}
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
              <span style={{ marginLeft: "auto", fontWeight: 600 }}>
                {readLabel}
              </span>
            ) : null}
            {actionItems.length > 0 ? button : null}
          </div>

          {m.message_text ? (
            <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {m.message_text}
            </div>
          ) : null}

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
                  url={blobMap[att.id] ?? null}
                  onOpen={() => void openBlob(att)}
                />
              ))}
            </div>
          ) : null}
        </article>
      )}
    </ActionMenu>
  );
}

function AttachmentPreview({
  att,
  url,
  onOpen,
}: {
  att: AttachmentMeta;
  url: string | null;
  onOpen: () => void;
}) {
  const kind = previewKind(att.file_extension || "");

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
        <video src={url} controls style={{ maxHeight: 220, width: "100%" }} />
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
  files: PickedFileItem[];
  onRemove: (id: number) => void;
}) {
  if (files.length === 0) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
      {files.map((item) => (
        <div
          key={item.id}
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
          {item.file.name}
          <button
            type="button"
            aria-label="Убрать вложение"
            title="Убрать"
            onClick={() => onRemove(item.id)}
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
