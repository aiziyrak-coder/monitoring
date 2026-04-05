/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_ORIGIN?: string;
  /** Masalan: 167.71.53.238:6006 — bo'sh bo'lsa hostname:6006 */
  readonly VITE_HL7_HOST_PORT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
