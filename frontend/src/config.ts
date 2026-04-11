export const SERVICE_NAME = import.meta.env.VITE_SERVICE_PUBLIC_NAME ?? 'Мессенджер';
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? API_BASE_URL.replace(/^http/i, 'ws');

export const PAGE_SIZE = 50;
export const AVATAR_MAX_SIZE_BYTES = 50 * 1024 * 1024;
export const ATTACHMENT_MAX_SIZE_BYTES = 5 * 1024 * 1024 * 1024;
export const ALLOWED_IMAGE_TYPES = ['image/png', 'image/jpg', 'image/jpeg', 'image/webp'];
export const ALLOWED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp'];

export const THEME_STORAGE_KEY = 'messenger-theme-mode';
