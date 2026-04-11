export function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ');
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }

  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function formatTimeOnly(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }

  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function formatDateOnly(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }

  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'medium',
  }).format(new Date(value));
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) {
    return '0 Б';
  }

  const units = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

export function getInitials(name: string): string {
  return name.trim().charAt(0).toUpperCase() || '?';
}

export function getFullUserName(user: {
  name: string;
  surname: string | null;
  second_name: string | null;
}): string {
  return [user.surname, user.name, user.second_name].filter(Boolean).join(' ');
}

export function buildArrayKey(parts: Array<string | number | null | undefined>): string {
  return parts.map((part) => String(part ?? '')).join(':');
}

export function isImageType(type: string): boolean {
  return type.startsWith('image/');
}

export function isAudioType(type: string): boolean {
  return type.startsWith('audio/');
}

export function isVideoType(type: string): boolean {
  return type.startsWith('video/');
}
