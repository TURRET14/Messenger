import { useEffect, useState } from "react";
import { apiJson, apiUrl } from "../api/client";
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
import { previewKind } from "./attachmentUtils";
import { formatDateTime, formatShortTime } from "../dateFormat";

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
  senderAvatarLetter,
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
  /** Первая буква username отправителя для аватара-заглушки. */
  senderAvatarLetter?: string;
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
  const cid = m.chat_id;
  const [atts, setAtts] = useState<AttachmentMeta[] | null>(null);

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

  /**
   * Прямой URL до файла-вложения. Используется в src у <img>/<video>/<audio>
   * и href у кнопки «Открыть». Браузер сам обрабатывает HTTP Range,
   * прогрессивную загрузку и кеширование (см. backend/routers/media_streaming.py).
   */
  const attachmentUrl = (att: AttachmentMeta): string =>
    apiUrl(`/chats/id/${cid}/messages/id/${m.id}/attachments/id/${att.id}`);

  const openInNewTab = (att: AttachmentMeta) => {
    window.open(attachmentUrl(att), "_blank", "noopener,noreferrer");
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
          data-msg-id={m.id}
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
                letter={senderAvatarLetter}
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
              title={formatDateTime(m.date_and_time_sent)}
              style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
            >
              <IconClock size={12} />
              {formatShortTime(m.date_and_time_sent)}
            </time>
            {edited ? (
              <span title={`Изменено: ${formatDateTime(m.date_and_time_edited)}`}>
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
                  url={attachmentUrl(att)}
                  onOpen={() => openInNewTab(att)}
                />
              ))}
            </div>
          ) : null}
        </article>
      )}
    </ActionMenu>
  );
}

/**
 * Видео-превью со скрытием плеера, если браузер не поддерживает кодек.
 * preload="metadata" заставляет браузер скачать только заголовки —
 * если декодер не находит подходящий codec, сработает onError и плеер
 * пропадёт; ниже останется только карточка с расширением и кнопкой
 * «открыть». Иначе пустой чёрный плеер вводил пользователя в заблуждение.
 */
function VideoPreview({ url }: { url: string }) {
  const [unsupported, setUnsupported] = useState(false);
  if (unsupported) return null;
  return (
    <video
      src={url}
      controls
      preload="metadata"
      playsInline
      onError={(e) => {
        const v = e.currentTarget;
        // MEDIA_ERR_SRC_NOT_SUPPORTED = 4 — неподдерживаемый формат/кодек.
        // Прочие ошибки (сеть, прерывание) тоже скрывают плеер, чтобы не
        // оставлять пустой чёрный прямоугольник.
        if (v.error) setUnsupported(true);
      }}
      style={{ maxHeight: 240, width: "100%", display: "block" }}
    />
  );
}

function AudioPreview({ url }: { url: string }) {
  const [unsupported, setUnsupported] = useState(false);
  if (unsupported) return null;
  return (
    <audio
      src={url}
      controls
      preload="metadata"
      onError={(e) => {
        if (e.currentTarget.error) setUnsupported(true);
      }}
      style={{ width: "100%" }}
    />
  );
}

function AttachmentPreview({
  att,
  url,
  onOpen,
}: {
  att: AttachmentMeta;
  /** Прямой URL до файла-вложения. Браузер сам обрабатывает HTTP Range для
   *  видео/аудио (мгновенный старт + перемотка) и прогрессивную декодировку
   *  для изображений. См. backend/routers/media_streaming.py. */
  url: string;
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
      {kind === "image" ? (
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
            loading="lazy"
            decoding="async"
            draggable={false}
            style={{ maxHeight: 240, width: "100%", objectFit: "contain" }}
          />
        </button>
      ) : null}
      {kind === "video" ? <VideoPreview url={url} /> : null}
      {kind === "audio" ? <AudioPreview url={url} /> : null}
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
