export type ScaffoldAuthMode = "anonymous" | "user" | "admin";
export type PlanTier = "free" | "pro" | "internal";

export interface FeatureFlags {
  [key: string]: boolean;
}

export interface SessionUser {
  id: string;
  email: string;
  fullName: string | null;
  isAdmin: boolean;
  planTier: PlanTier;
  featureFlags: FeatureFlags;
}

export interface SpaceSummary {
  id: string;
  name: string;
}

export interface ProblemResponse {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  code?: string | null;
}
