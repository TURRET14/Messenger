import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { IconMoreVertical } from "../Icons";

export type ActionMenuItem = {
  label: string;
  onSelect: () => void;
  icon?: ReactNode;
  danger?: boolean;
  disabled?: boolean;
};

type ActionMenuControls = {
  button: ReactNode;
  onContextMenu: (event: React.MouseEvent) => void;
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(value, max));
}

export function ActionMenu({
  items,
  label = "Действия",
  children,
}: {
  items: ActionMenuItem[];
  label?: string;
  children?: (controls: ActionMenuControls) => ReactNode;
}) {
  const activeItems = useMemo(
    () => items.filter((item) => !item.disabled),
    [items],
  );
  const [point, setPoint] = useState<{ x: number; y: number } | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const close = () => setPoint(null);

  const openAt = (x: number, y: number) => {
    if (activeItems.length === 0) return;
    const width = 240;
    const height = Math.min(420, activeItems.length * 42 + 12);
    setPoint({
      x: clamp(x, 8, window.innerWidth - width - 8),
      y: clamp(y, 8, window.innerHeight - height - 8),
    });
  };

  const onContextMenu = (event: React.MouseEvent) => {
    if (activeItems.length === 0) return;
    event.preventDefault();
    openAt(event.clientX, event.clientY);
  };

  useEffect(() => {
    if (!point) return;

    const onPointerDown = (event: PointerEvent) => {
      if (menuRef.current?.contains(event.target as Node)) return;
      close();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    const onScroll = () => close();

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("scroll", onScroll, true);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [point]);

  const button = (
    <button
      ref={buttonRef}
      type="button"
      aria-label={label}
      title={label}
      disabled={activeItems.length === 0}
      onClick={(event) => {
        event.stopPropagation();
        const rect = buttonRef.current?.getBoundingClientRect();
        openAt(rect?.right ?? event.clientX, rect?.bottom ?? event.clientY);
      }}
      className="ui-icon-btn ui-icon-btn--sm"
    >
      <IconMoreVertical size={18} />
    </button>
  );

  return (
    <>
      {children ? children({ button, onContextMenu }) : button}
      {point ? (
        <div
          ref={menuRef}
          role="menu"
          className="ui-menu anim-scale-in"
          style={{
            position: "fixed",
            left: point.x,
            top: point.y,
            zIndex: 1000,
            transformOrigin: "top left",
          }}
        >
          {activeItems.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              onClick={() => {
                close();
                item.onSelect();
              }}
              className={
                item.danger
                  ? "ui-menu-item ui-menu-item--danger"
                  : "ui-menu-item"
              }
            >
              {item.icon ? (
                <span
                  aria-hidden="true"
                  style={{
                    display: "inline-flex",
                    width: 18,
                    height: 18,
                    flexShrink: 0,
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {item.icon}
                </span>
              ) : null}
              <span style={{ flex: 1 }}>{item.label}</span>
            </button>
          ))}
        </div>
      ) : null}
    </>
  );
}
