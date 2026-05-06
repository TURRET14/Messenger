import { useTheme, type ThemePreference } from "../theme/ThemeContext";
import { IconMonitor, IconMoon, IconSun } from "./Icons";

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
      <IconMonitor title="Тема системы" />
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
      className="ui-icon-btn"
      onClick={cycle}
      title={`${label}. Нажмите, чтобы переключить.`}
      aria-label={label}
    >
      {icon}
    </button>
  );
}
