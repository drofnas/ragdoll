/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_SCAFFOLD_AUTH_MODE?: "anonymous" | "user" | "admin";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare global {
  var __RAGDOLL_SCAFFOLD_AUTH_MODE__: "anonymous" | "user" | "admin" | undefined;
}

export {};
