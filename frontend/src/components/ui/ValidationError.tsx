import type { CSSProperties } from "react";
import { IconAlert } from "../Icons";

const baseStyle: CSSProperties = {
  margin: "4px 0 10px",
  padding: "9px 12px",
  borderRadius: 10,
  border: "1px solid var(--danger)",
  background: "var(--danger-soft)",
  color: "var(--danger)",
  fontSize: "0.86rem",
  lineHeight: 1.35,
  whiteSpace: "pre-wrap",
  display: "flex",
  alignItems: "flex-start",
  gap: 8,
  animation: "slide-down 200ms ease-out both",
};

export function ValidationError({
  message,
  id,
  style,
}: {
  message: string | null | undefined;
  id?: string;
  style?: CSSProperties;
}) {
  if (!message) return null;

  return (
    <div id={id} role="alert" aria-live="polite" style={{ ...baseStyle, ...style }}>
      <IconAlert size={16} />
      <span style={{ flex: 1 }}>{message}</span>
    </div>
  );
}
