import type { CurrentUser } from "./api/types";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+\d{10,15}$/;

const IMAGE_TYPES = new Set([
  "image/png",
  "image/jpg",
  "image/jpeg",
  "image/webp",
]);

const IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".webp"]);

const MAX_FIELD = 100;
const MAX_EMAIL = 254;
const MAX_ABOUT = 5000;
const MAX_CODE = 100;
const MAX_AVATAR_SIZE = 50 * 1024 * 1024;
const MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024 * 1024;
const MIN_PASSWORD = 5;

function extensionOf(fileName: string): string {
  const dot = fileName.lastIndexOf(".");
  return dot >= 0 ? fileName.slice(dot).toLowerCase() : "";
}

function requiredLimit(
  label: string,
  value: string,
  maxLength: number,
  minLength = 1,
): string | null {
  if (value.length === 0) {
    return `${label}: заполните поле.`;
  }
  if (value.length < minLength) {
    return `${label}: минимум ${minLength} символов.`;
  }
  if (value.length > maxLength) {
    return `${label}: максимум ${maxLength} символов.`;
  }
  return null;
}

function optionalLimit(
  label: string,
  value: string | null | undefined,
  maxLength: number,
): string | null {
  if (!value) return null;
  if (value.length > maxLength) {
    return `${label}: максимум ${maxLength} символов.`;
  }
  return null;
}

function trimOrNull(value: string | null | undefined): string | null {
  const trimmed = value?.trim() ?? "";
  return trimmed ? trimmed : null;
}

export function validateEmailAddress(
  email: string,
  label = "Email",
): string | null {
  const trimmed = email.trim();
  const requiredError = requiredLimit(label, trimmed, MAX_EMAIL);
  if (requiredError) return requiredError;
  if (!EMAIL_RE.test(trimmed)) {
    return `${label}: некорректный адрес электронной почты.`;
  }
  return null;
}

export function validateCode(code: string, label = "Код"): string | null {
  return requiredLimit(label, code.trim(), MAX_CODE);
}

export function validateLogin(login: string, label = "Логин"): string | null {
  return requiredLimit(label, login.trim(), MAX_FIELD);
}

export function validatePassword(
  password: string,
  label = "Пароль",
): string | null {
  return requiredLimit(label, password, MAX_FIELD, MIN_PASSWORD);
}

export function validateRegisterForm(data: {
  username: string;
  name: string;
  surname: string;
  secondName: string;
  email: string;
  login: string;
  password: string;
}): string | null {
  return (
    requiredLimit("Имя пользователя", data.username.trim(), MAX_FIELD) ??
    requiredLimit("Имя", data.name.trim(), MAX_FIELD) ??
    optionalLimit("Фамилия", trimOrNull(data.surname), MAX_FIELD) ??
    optionalLimit("Отчество", trimOrNull(data.secondName), MAX_FIELD) ??
    validateEmailAddress(data.email, "Электронная почта") ??
    validateLogin(data.login) ??
    validatePassword(data.password)
  );
}

export function validateProfileForm(user: CurrentUser): string | null {
  const usernameError = requiredLimit(
    "Имя пользователя",
    user.username.trim(),
    MAX_FIELD,
  );
  if (usernameError) return usernameError;

  const nameError = requiredLimit("Имя", user.name.trim(), MAX_FIELD);
  if (nameError) return nameError;

  const surnameError = optionalLimit("Фамилия", trimOrNull(user.surname), MAX_FIELD);
  if (surnameError) return surnameError;

  const secondNameError = optionalLimit(
    "Отчество",
    trimOrNull(user.second_name),
    MAX_FIELD,
  );
  if (secondNameError) return secondNameError;

  const emailError = validateEmailAddress(
    user.email_address,
    "Электронная почта",
  );
  if (emailError) return emailError;

  const phone = trimOrNull(user.phone_number);
  if (phone && !PHONE_RE.test(phone)) {
    return "Телефон: используйте формат +1234567890.";
  }

  const aboutError = optionalLimit("О себе", user.about, MAX_ABOUT);
  if (aboutError) return aboutError;

  if (user.date_of_birth) {
    const valueDate = new Date(`${user.date_of_birth}T00:00:00`);
    if (Number.isNaN(valueDate.getTime())) {
      return "Дата рождения: некорректная дата.";
    }
    const today = new Date();
    today.setHours(23, 59, 59, 999);
    if (valueDate > today) {
      return "Дата рождения не может быть в будущем.";
    }
  }

  return null;
}

export function validateChatName(
  name: string,
  label = "Название чата",
): string | null {
  return requiredLimit(label, name.trim(), MAX_FIELD);
}

export function validateMessageForSend(
  text: string,
  hasFiles: boolean,
): string | null {
  if (!text.trim() && !hasFiles) {
    return "Введите текст сообщения или прикрепите файл.";
  }
  return null;
}

export function validateMessageSearch(
  value: string,
  label = "Поиск",
): string | null {
  if (!value.trim()) {
    return `${label}: введите текст для поиска.`;
  }
  return null;
}

export function validateImageFile(file: File, label: string): string | null {
  const extension = extensionOf(file.name);
  if (!IMAGE_TYPES.has(file.type) || !IMAGE_EXTENSIONS.has(extension)) {
    return `${label}: поддерживаются только PNG, JPG, JPEG и WEBP.`;
  }
  if (file.size > MAX_AVATAR_SIZE) {
    return `${label}: файл превышает 50 МБ.`;
  }
  return null;
}

export function validateAttachmentFiles(files: FileList | File[]): string | null {
  for (const file of Array.from(files)) {
    if (file.size > MAX_ATTACHMENT_SIZE) {
      return `Файл ${file.name} превышает 5 ГБ.`;
    }
  }
  return null;
}

export function validateUsernameSearch(
  value: string,
  label = "Имя пользователя",
): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return `${label}: заполните поле поиска.`;
  }
  if (trimmed.length > MAX_FIELD) {
    return `${label}: максимум ${MAX_FIELD} символов.`;
  }
  return null;
}

export function validateNamesSearch(values: {
  name?: string;
  surname?: string;
  secondName?: string;
}): string | null {
  const name = trimOrNull(values.name) ?? "";
  const surname = trimOrNull(values.surname) ?? "";
  const secondName = trimOrNull(values.secondName) ?? "";

  if (!name && !surname && !secondName) {
    return "Укажите хотя бы одно поле поиска.";
  }

  return (
    optionalLimit("Имя", name, MAX_FIELD) ??
    optionalLimit("Фамилия", surname, MAX_FIELD) ??
    optionalLimit("Отчество", secondName, MAX_FIELD)
  );
}
