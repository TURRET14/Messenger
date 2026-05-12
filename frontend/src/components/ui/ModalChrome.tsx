import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";
import { IconX } from "../Icons";

// Стек активных ModalChrome — нужен, чтобы Escape закрывал только самый
// верхний модал. Иначе при открытом профиле поверх меню одно нажатие
// Escape закрывало бы и профиль, и меню одновременно (раньше каждый
// ModalChrome вешал свой собственный document keydown-листенер).
type EscCloser = () => void;
const escStack: EscCloser[] = [];
let escListenerInstalled = false;

function ensureEscListener(): void {
  if (escListenerInstalled) return;
  escListenerInstalled = true;
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const top = escStack[escStack.length - 1];
    if (top) top();
  });
}

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
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    ensureEscListener();
    const closer: EscCloser = () => onCloseRef.current();
    escStack.push(closer);
    return () => {
      const idx = escStack.lastIndexOf(closer);
      if (idx >= 0) escStack.splice(idx, 1);
    };
  }, []);

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
