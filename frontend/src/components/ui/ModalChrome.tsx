import { useEffect, type CSSProperties, type ReactNode } from "react";
import { IconX } from "../Icons";

const overlay: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "var(--overlay)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 200,
  padding: 16,
  animation: "overlay-in 160ms ease-out both",
};

const panel = (narrow: boolean): CSSProperties => ({
  position: "relative",
  width: narrow ? "min(440px, 100%)" : "min(960px, 100%)",
  maxHeight: "min(92dvh, 920px)",
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
  background: "var(--bg-elevated)",
  color: "var(--text)",
  borderRadius: 16,
  border: "1px solid var(--border)",
  animation: "modal-in 220ms ease-out both",
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

export function ModalChrome({
  title,
  onClose,
  children,
  narrow,
  bodyStyle,
  hideHeader,
  closeOnBackdrop = true,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  narrow?: boolean;
  bodyStyle?: CSSProperties;
  hideHeader?: boolean;
  closeOnBackdrop?: boolean;
}) {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      style={overlay}
      role="presentation"
      onMouseDown={(e) => {
        if (!closeOnBackdrop) return;
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={panel(!!narrow)}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {!hideHeader ? (
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
              className="ui-icon-btn"
              onClick={onClose}
              aria-label="Закрыть"
              title="Закрыть"
            >
              <IconX size={20} />
            </button>
          </div>
        ) : null}
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
