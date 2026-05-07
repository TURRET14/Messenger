import { apiJson } from "./client";
import type { UserInList } from "./types";

/**
 * Кросс-компонентный кеш загруженных UserInList с дедупликацией in-flight
 * запросов и батчингом одиночных запросов в bulk POST /users/by-ids.
 *
 * Принцип работы:
 * 1. Запросы одного user_id, поступающие в течение одного microtask-кадра,
 *    собираются в один pending-набор.
 * 2. На следующем microtask один POST /users/by-ids отправляется со всеми ID.
 * 3. Полученные пользователи кешируются и резолвят все ожидающие промисы.
 * 4. Повторные запросы тех же ID моментально берутся из кеша.
 *
 * Это убирает N+1 (50 параллельных GET /users/id/{id}) → 1 POST.
 */

const cache = new Map<number, UserInList>();
const inflight = new Map<number, Promise<UserInList | null>>();

let pending: Set<number> | null = null;
let pendingResolvers: Map<number, (u: UserInList | null) => void> | null = null;
let flushScheduled = false;

const MAX_BATCH_SIZE = 200;

function flush(): void {
  flushScheduled = false;
  if (!pending || pending.size === 0) {
    pending = null;
    pendingResolvers = null;
    return;
  }
  const ids = Array.from(pending);
  const resolvers = pendingResolvers!;
  pending = null;
  pendingResolvers = null;

  // Если ID больше лимита бэкенда — режем на чанки и отправляем параллельно.
  const chunks: number[][] = [];
  for (let i = 0; i < ids.length; i += MAX_BATCH_SIZE) {
    chunks.push(ids.slice(i, i + MAX_BATCH_SIZE));
  }

  void Promise.all(
    chunks.map((chunk) => {
      // GET /users/by-ids?ids=1&ids=2&ids=3 — стандартный repeated-query формат,
      // который FastAPI разбирает как list[int] при объявлении Query(...).
      const params = chunk.map((id) => `ids=${encodeURIComponent(id)}`).join("&");
      return apiJson<UserInList[]>(`/users/by-ids?${params}`).catch(
        () => [] as UserInList[],
      );
    }),
  ).then((batches) => {
    const found = new Map<number, UserInList>();
    for (const batch of batches) {
      for (const u of batch) {
        found.set(u.id, u);
        cache.set(u.id, u);
      }
    }
    for (const id of ids) {
      const resolver = resolvers.get(id);
      if (resolver) resolver(found.get(id) ?? null);
      inflight.delete(id);
    }
  });
}

/**
 * Запрашивает пользователя по ID. Несколько вызовов в течение одного
 * microtask-кадра объединяются в один POST /users/by-ids.
 * Возвращает null если пользователь не найден на сервере.
 */
export function fetchUser(userId: number): Promise<UserInList | null> {
  const cached = cache.get(userId);
  if (cached) return Promise.resolve(cached);

  const existing = inflight.get(userId);
  if (existing) return existing;

  if (!pending) pending = new Set();
  if (!pendingResolvers) pendingResolvers = new Map();
  pending.add(userId);

  const promise = new Promise<UserInList | null>((resolve) => {
    pendingResolvers!.set(userId, resolve);
  });
  inflight.set(userId, promise);

  if (!flushScheduled) {
    flushScheduled = true;
    queueMicrotask(flush);
  }

  return promise;
}

/**
 * Загружает сразу несколько пользователей одним запросом. Уже закешированные
 * исключаются из запроса. Возвращает Map<id, UserInList> для удобной выборки.
 */
export async function fetchUsers(
  userIds: Iterable<number>,
): Promise<Map<number, UserInList>> {
  const result = new Map<number, UserInList>();
  const need: number[] = [];
  for (const id of userIds) {
    const cached = cache.get(id);
    if (cached) {
      result.set(id, cached);
    } else {
      need.push(id);
    }
  }
  if (need.length === 0) return result;

  // Используем тот же batched fetchUser, чтобы дедупились с одиночными
  // вызовами из других компонентов в этом же кадре.
  const fetched = await Promise.all(need.map((id) => fetchUser(id)));
  fetched.forEach((u, idx) => {
    if (u) result.set(need[idx], u);
  });
  return result;
}

/** Синхронно достаёт из кеша если есть. Не делает запросов. */
export function peekUser(userId: number): UserInList | undefined {
  return cache.get(userId);
}

/** Помещает в кеш напрямую (например, после поиска или подгрузки списка). */
export function primeUser(user: UserInList): void {
  cache.set(user.id, user);
}

/** Очистка — на случай logout. */
export function clearUserCache(): void {
  cache.clear();
}
