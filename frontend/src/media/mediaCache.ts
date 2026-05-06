import { apiFetch } from "../api/client";

const objectUrlCache = new Map<string, string>();
const inflightObjectUrlCache = new Map<string, Promise<string>>();

export function peekCachedMediaUrl(src: string): string | null {
  return objectUrlCache.get(src) ?? null;
}

export async function getCachedMediaUrl(src: string): Promise<string> {
  const cached = objectUrlCache.get(src);
  if (cached) return cached;

  const pending = inflightObjectUrlCache.get(src);
  if (pending) return pending;

  const promise = (async () => {
    const res = await apiFetch(src);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    objectUrlCache.set(src, objectUrl);
    return objectUrl;
  })();

  inflightObjectUrlCache.set(src, promise);

  try {
    return await promise;
  } finally {
    inflightObjectUrlCache.delete(src);
  }
}

export function invalidateCachedMediaUrl(src: string): void {
  const cached = objectUrlCache.get(src);
  if (cached) {
    URL.revokeObjectURL(cached);
    objectUrlCache.delete(src);
  }
  inflightObjectUrlCache.delete(src);
}
