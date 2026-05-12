import type { ApiErrorBody } from "./types";

const rawBase = import.meta.env.VITE_API_BASE_URL ?? "";
export const API_BASE_URL = rawBase.replace(/\/$/, "");

export function getWebSocketRoot(): string {
  if (!API_BASE_URL) {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}`;
  }
  try {
    const u = new URL(API_BASE_URL);
    const wsProto = u.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProto}//${u.host}`;
  } catch {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}`;
  }
}

function buildUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${p}`;
}

/**
 * Возвращает абсолютный URL для прямого использования в `<img src>`,
 * `<video src>`, `<audio src>` и `<a href>`. Учитывает VITE_API_BASE_URL,
 * если фронтенд и бэкенд развёрнуты на разных origin'ах.
 *
 * Cookie сессии браузер отправит автоматически: same-origin без вопросов,
 * для cross-origin нужны корректные CORS-заголовки и атрибут
 * crossorigin="use-credentials" на теге.
 */
export function apiUrl(path: string): string {
  return buildUrl(path);
}

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

/**
 * Имя глобального CustomEvent, отправляемого при 401 от API. App.tsx
 * слушает его и инициирует выход из системы — после того, как любой
 * вызов получает «недействительный токен», пользователь автоматически
 * возвращается на экран входа (без необходимости перезагружать страницу).
 */
export const AUTH_EXPIRED_EVENT = "messenger:auth-expired";

let authExpiredFired = false;

/**
 * Срабатывает только на «настоящий» 401 — истёкшую/удалённую сессию.
 * Бэкенд использует 401 и для бизнес-ошибок («Неверный пароль» при
 * подтверждении смены пароля/почты): такие ошибки автологаут вызывать
 * не должны.
 */
function isAuthSessionFailure(body: unknown): boolean {
  if (!body || typeof body !== "object") return false;
  const code = (body as ApiErrorBody).error_code;
  return code === "UNAUTHORIZED_ERROR";
}

function notifyAuthExpired(body: unknown): void {
  if (!isAuthSessionFailure(body)) return;
  // Один 401 может породить десятки параллельных запросов — событие
  // отправляем ровно один раз, пока пользователь не перелогинится.
  if (authExpiredFired) return;
  authExpiredFired = true;
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
}

/**
 * Сбрасывает «защёлку» однократной отправки события — вызывается App.tsx
 * после успешного логина, чтобы следующая истёкшая сессия снова стрельнула.
 */
export function resetAuthExpiredLatch(): void {
  authExpiredFired = false;
}

function parseErrorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const b = body as ApiErrorBody;
    if (typeof b.error_message === "string") return b.error_message;
  }
  return `Ошибка запроса (${status})`;
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  const isForm = init.body instanceof FormData;
  if (!isForm && init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(buildUrl(path), {
    ...init,
    credentials: "include",
    headers,
  });

  if (!res.ok) {
    let body: unknown;
    const ct = res.headers.get("content-type");
    try {
      if (ct?.includes("application/json")) {
        body = await res.json();
      } else {
        body = await res.text();
      }
    } catch {
      body = null;
    }
    if (res.status === 401) notifyAuthExpired(body);
    throw new ApiError(parseErrorMessage(body, res.status), res.status, body);
  }

  return res;
}

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/* ============================================================
 * Загрузка файлов с индикатором прогресса.
 *
 * Fetch API не даёт upload-progress events (только download через ReadableStream
 * без точного %), поэтому для загрузки файлов используем XMLHttpRequest —
 * он умеет XMLHttpRequestUpload.onprogress с loaded/total в байтах.
 * ============================================================ */

export interface UploadProgress {
  /** Сколько байт уже отправлено */
  loaded: number;
  /** Общий размер тела запроса в байтах */
  total: number;
}

export interface UploadOptions {
  /** Колбек прогресса. Вызывается во время отправки многократно. */
  onProgress?: (progress: UploadProgress) => void;
  /** Сигнал отмены. abort() прервёт загрузку и резолвнёт промис ошибкой. */
  signal?: AbortSignal;
  /** HTTP-метод. По умолчанию POST. */
  method?: "POST" | "PUT" | "PATCH";
}

/**
 * Отправляет multipart/form-data с прогрессом и возможностью отмены.
 * Cookie сессии передаётся автоматически (withCredentials = true).
 * При HTTP-ошибке кидает ApiError, при отмене — AbortError.
 */
export function apiUpload(
  path: string,
  body: FormData,
  options: UploadOptions = {},
): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const method = options.method ?? "POST";
    xhr.open(method, buildUrl(path));
    xhr.withCredentials = true;
    xhr.responseType = "text";

    if (options.onProgress) {
      const cb = options.onProgress;
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          cb({ loaded: e.loaded, total: e.total });
        }
      });
    }

    xhr.addEventListener("load", () => {
      const status = xhr.status;
      const text = xhr.responseText;
      const ct = xhr.getResponseHeader("content-type") ?? "";
      let parsed: unknown = null;
      if (text) {
        if (ct.includes("application/json")) {
          try {
            parsed = JSON.parse(text);
          } catch {
            parsed = text;
          }
        } else {
          parsed = text;
        }
      }
      if (status >= 200 && status < 300) {
        resolve(parsed);
      } else {
        if (status === 401) notifyAuthExpired(parsed);
        reject(new ApiError(parseErrorMessage(parsed, status), status, parsed));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new ApiError("Сетевая ошибка при загрузке", 0, null));
    });

    xhr.addEventListener("abort", () => {
      reject(new DOMException("Загрузка отменена", "AbortError"));
    });

    if (options.signal) {
      if (options.signal.aborted) {
        // Уже отменён до отправки — отменяем сразу.
        reject(new DOMException("Загрузка отменена", "AbortError"));
        return;
      }
      options.signal.addEventListener("abort", () => xhr.abort(), { once: true });
    }

    xhr.send(body);
  });
}
