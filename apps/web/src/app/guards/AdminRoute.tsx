import { PropsWithChildren } from "react";
import { Navigate } from "react-router-dom";

import { Spinner } from "@/components/ui/spinner";
import { useAuthSession } from "@/shared/state/authSession";
import { AuthUnavailablePanel } from "./AuthUnavailablePanel";

export function AdminRoute({ children }: PropsWithChildren) {
  const { isAuthenticated, isAdmin, status } = useAuthSession();

  if (status === "loading") {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="flex items-center gap-3 rounded-md border bg-background px-4 py-3 text-sm text-muted-foreground">
          <Spinner />
          Loading admin access…
        </div>
      </div>
    );
  }

  if (status === "unavailable") {
    return <AuthUnavailablePanel />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}
