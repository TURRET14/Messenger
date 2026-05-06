import { useEffect, useState } from "react";
import { ApiError, apiJson } from "../api/client";
import type { Message } from "../api/types";
import {
  IconCheck,
  IconCheckDouble,
  IconClock,
  IconEdit,
  IconExternal,
  IconFile,
  IconImage,
  IconMessageCircle,
  IconPaperclip,
  IconReply,
  IconTrash,
  IconX,
} from "../components/Icons";
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

function shortTime(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const sameDay =
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate();
  if (sameDay) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString([], { day: "2-digit", month: "2-digit", year: "2-digit" });
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
  onOpenAuthorProfile,
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
  onOpenAuthorProfile?: (userId: number) => void;
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
          ...(onReply
            ? [{ label: "Ответить", onSelect: onReply, icon: <IconReply size={16} /> }]
            : []),
          ...(onEdit
            ? [{ label: "Изменить", onSelect: onEdit, icon: <IconEdit size={16} /> }]
            : []),
          ...(canOpenComments && onOpenComments
            ? [
                {
                  label: "Комментарии",
                  onSelect: onOpenComments,
                  icon: <IconMessageCircle size={16} />,
                },
              ]
            : []),
          ...(onDelete
            ? [
                {
                  label: "Удалить",
                  onSelect: onDelete,
                  icon: <IconTrash size={16} />,
                  danger: true,
                },
              ]
            : []),
        ];

  const handleAuthorClick =
    m.sender_user_id != null && onOpenAuthorProfile
      ? () => onOpenAuthorProfile(m.sender_user_id as number)
      : undefined;

  return (
    <ActionMenu items={actionItems} label="Действия с сообщением">
      {({ button, onContextMenu }) => (
        <article
          onContextMenu={onContextMenu}
          className="anim-message-pop"
          style={{
            alignSelf: mine ? "flex-end" : "flex-start",
            maxWidth: "min(560px, 94%)",
            padding: "10px 14px",
            borderRadius: 14,
            background: mine ? "var(--bubble-mine)" : "var(--bubble-other)",
            border: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {m.reply_message_id && (replySnippet != null || replySenderLabel) ? (
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--text-muted)",
                borderLeft: "3px solid var(--accent)",
                paddingLeft: 8,
                paddingTop: 2,
                paddingBottom: 2,
              }}
            >
              {replySenderLabel ? (
                <div style={{ color: "var(--text)", fontWeight: 600 }}>
                  {replySenderLabel}
                </div>
              ) : null}
              <span style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                {replySnippet ?? "..."}
              </span>
            </div>
          ) : null}

          <div
            style={{
              fontSize: "0.78rem",
              color: "var(--text-muted)",
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
                size={26}
                alt=""
                onClick={handleAuthorClick}
              />
            ) : null}
            {handleAuthorClick ? (
              <button
                type="button"
                onClick={handleAuthorClick}
                style={{
                  border: "none",
                  background: "none",
                  padding: 0,
                  font: "inherit",
                  color: "var(--text)",
                  cursor: "pointer",
                  fontWeight: 600,
                  textAlign: "left",
                }}
                title="Открыть профиль"
              >
                {displaySender}
              </button>
            ) : (
              <span style={{ color: "var(--text)", fontWeight: 600 }}>
                {displaySender}
              </span>
            )}
            <time
              dateTime={m.date_and_time_sent}
              title={new Date(m.date_and_time_sent).toLocaleString()}
              style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
            >
              <IconClock size={12} />
              {shortTime(m.date_and_time_sent)}
            </time>
            {edited ? (
              <span title={`Изменено: ${new Date(m.date_and_time_edited!).toLocaleString()}`}>
                · изм.
              </span>
            ) : null}
            <span style={{ marginLeft: "auto", display: "inline-flex", alignItems: "center", gap: 6 }}>
              {mine && showReadReceipt && readLabel ? (
                <span
                  className="ui-chip"
                  style={{
                    background: "transparent",
                    border: "none",
                    padding: 0,
                    color: "var(--text-muted)",
                    fontSize: "0.78rem",
                  }}
                  title={readLabel}
                >
                  {m.is_read === true ? (
                    <IconCheckDouble size={14} />
                  ) : (
                    <IconCheck size={14} />
                  )}
                </span>
              ) : null}
              {actionItems.length > 0 ? button : null}
            </span>
          </div>

          {m.message_text ? (
            <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {m.message_text}
            </div>
          ) : null}

          {atts && atts.length > 0 ? (
            <div
              style={{
                marginTop: 6,
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
  const kindIcon =
    kind === "image" ? (
      <IconImage size={14} />
    ) : kind === "video" || kind === "audio" ? (
      <IconPaperclip size={14} />
    ) : (
      <IconFile size={14} />
    );

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
            style={{ maxHeight: 240, width: "100%", objectFit: "contain" }}
          />
        </button>
      ) : null}
      {kind === "video" && url ? (
        <video src={url} controls style={{ maxHeight: 240, width: "100%" }} />
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
        <span
          style={{
            fontSize: "0.8rem",
            color: "var(--text-muted)",
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          {kindIcon}
          Вложение {att.id}
          {att.file_extension ? ` (${att.file_extension})` : ""}
        </span>
        <button type="button" className="ui-btn ui-btn--ghost ui-btn--sm" onClick={onOpen}>
          <IconExternal size={14} />
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
          className="ui-chip"
          style={{ paddingRight: 4 }}
        >
          <IconFile size={14} />
          <span
            style={{
              maxWidth: 180,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={item.file.name}
          >
            {item.file.name}
          </span>
          <button
            type="button"
            aria-label="Убрать вложение"
            title="Убрать"
            onClick={() => onRemove(item.id)}
            className="ui-icon-btn ui-icon-btn--sm ui-icon-btn--danger"
            style={{ width: 22, height: 22 }}
          >
            <IconX size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
