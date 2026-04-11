import type { CSSProperties, ReactNode } from "react";
import { IconX } from "../Icons";

const overlay: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.5)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 200,
  padding: 16,
};

const panel = (narrow: boolean): CSSProperties => ({
  position: "relative",
  width: narrow ? "min(420px, 100%)" : "min(960px, 100%)",
  maxHeight: "min(90vh, 900px)",
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
  background: "var(--bg-elevated)",
  color: "var(--text)",
  borderRadius: 16,
  border: "1px solid var(--border)",
  boxShadow: "0 16px 48px var(--shadow)",
});

const head: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
  padding: "14px 18px",
  borderBottom: "1px solid var(--border)",
  flexShrink: 0,
};

const closeBtn: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: 40,
  height: 40,
  padding: 0,
  border: "none",
  borderRadius: "50%",
  background: "var(--bg-muted)",
  color: "var(--text)",
  cursor: "pointer",
};

export function ModalChrome({
  title,
  onClose,
  children,
  narrow,
  bodyStyle,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  narrow?: boolean;
  bodyStyle?: CSSProperties;
}) {
  return (
    <div style={overlay} role="presentation" onMouseDown={(e) => e.stopPropagation()}>
      <div
        style={panel(!!narrow)}
        role="dialog"
        aria-modal="true"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div style={head}>
          <h2
            style={{
              margin: 0,
              fontSize: "1.05rem",
              fontWeight: 700,
              flex: 1,
              minWidth: 0,
            }}
          >
            {title}
          </h2>
          <button
            type="button"
            style={closeBtn}
            onClick={onClose}
            aria-label="Закрыть"
            title="Закрыть"
          >
            <IconX size={20} />
          </button>
        </div>
        <div
          style={{
            padding: 18,
            overflow: "auto",
            flex: 1,
            minHeight: 0,
            ...bodyStyle,
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
