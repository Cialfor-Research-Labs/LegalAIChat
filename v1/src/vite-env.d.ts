/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_V1_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
