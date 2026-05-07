/**
 * Утилиты форматирования дат для UI. Все функции возвращают значения
 * в локали ru-RU с порядком ДД.ММ.ГГГГ независимо от настроек браузера.
 */

function pad(n: number): string {
  return n.toString().padStart(2, "0");
}

function parseIso(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** «ДД.ММ.ГГГГ» — для дат без времени (например, дата рождения). */
export function formatDate(iso: string | null | undefined, fallback = "—"): string {
  const d = parseIso(iso);
  if (!d) return fallback;
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

/** «ДД.ММ.ГГГГ ЧЧ:ММ» — для дат с временем (регистрация, отправка и т. п.). */
export function formatDateTime(
  iso: string | null | undefined,
  fallback = "—",
): string {
  const d = parseIso(iso);
  if (!d) return fallback;
  return (
    `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

/**
 * Короткий формат для превью в чатах: если сегодня — «ЧЧ:ММ»,
 * иначе «ДД.ММ.ГГ».
 */
export function formatShortTime(iso: string): string {
  const d = parseIso(iso);
  if (!d) return "";
  const today = new Date();
  const sameDay =
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate();
  if (sameDay) {
    return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${pad(
    d.getFullYear() % 100,
  )}`;
}
