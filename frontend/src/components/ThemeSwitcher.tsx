import type { CSSProperties } from "react";
import { useTheme, type ThemePreference } from "../theme/ThemeContext";
import { IconMonitor, IconMoon, IconSun } from "./Icons";

const btnStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: 40,
  height: 40,
  padding: 0,
  border: "1px solid var(--border)",
  borderRadius: 10,
  background: "var(--bg-elevated)",
  color: "var(--text)",
};

export function ThemeSwitcher() {
  const { preference, setPreference } = useTheme();

  const cycle = () => {
    const order: ThemePreference[] = ["system", "light", "dark"];
    const i = order.indexOf(preference);
    setPreference(order[(i + 1) % order.length]);
  };

  const icon =
    preference === "light" ? (
      <IconSun title="Светлая тема" />
    ) : preference === "dark" ? (
      <IconMoon title="Тёмная тема" />
    ) : (
      <IconMonitor title="Как в системе" />
    );

  const label =
    preference === "light"
      ? "Светлая тема"
      : preference === "dark"
        ? "Тёмная тема"
        : "Тема системы";

  return (
    <button
      type="button"
      style={btnStyle}
      onClick={cycle}
      title={`${label}. Нажмите, чтобы переключить.`}
      aria-label={label}
    >
      {icon}
    </button>
  );
}
