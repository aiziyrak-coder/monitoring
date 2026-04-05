/**
 * REST so'rovlar bazaviy URL.
 * Bo'sh bo'lsa — joriy origin (Vite devda proxy orqali Django).
 * Production: VITE_API_ORIGIN=https://api.kasalxona.uz
 */
const RAW = (import.meta.env.VITE_API_ORIGIN as string | undefined)?.trim() ?? '';

export function apiUrl(path: string): string {
  if (!path.startsWith('/')) {
    path = `/${path}`;
  }
  if (!RAW) {
    return path;
  }
  return `${RAW.replace(/\/$/, '')}${path}`;
}

export function socketIoUrl(): string {
  if (RAW) {
    return RAW.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }
  return '';
}

/** Mindray HL7 server IP:port — monitor «Интернет» menyusida ko'rsatish uchun. */
export function hl7ServerDisplay(): string {
  const explicit = (import.meta.env.VITE_HL7_HOST_PORT as string | undefined)?.trim();
  if (explicit) return explicit;
  if (RAW) {
    try {
      return `${new URL(RAW).hostname}:6006`;
    } catch {
      return 'server-host:6006';
    }
  }
  if (typeof window !== 'undefined') {
    return `${window.location.hostname}:6006`;
  }
  return 'server-IP:6006';
}
