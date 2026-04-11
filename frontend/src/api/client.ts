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
    throw new ApiError(parseErrorMessage(body, res.status), res.status, body);
  }

  return res;
}

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
