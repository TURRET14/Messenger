export type AttachmentPreviewKind = "image" | "video" | "audio" | "file";

const IMG = new Set([
  ".jpg",
  ".jpeg",
  ".png",
  ".gif",
  ".webp",
  ".bmp",
  ".svg",
]);
const VID = new Set([".mp4", ".webm", ".ogg", ".mov", ".m4v"]);
const AUD = new Set([".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"]);

export function previewKind(ext: string): AttachmentPreviewKind {
  const e = ext.toLowerCase();
  if (IMG.has(e)) return "image";
  if (VID.has(e)) return "video";
  if (AUD.has(e)) return "audio";
  return "file";
}
