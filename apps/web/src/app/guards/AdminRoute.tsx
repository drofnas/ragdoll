import { PropsWithChildren } from "react";
import { Navigate } from "react-router-dom";

import { useAuthSession } from "../../shared/state/authSession";

export function AdminRoute({ children }: PropsWithChildren) {
  const { isAuthenticated, isAdmin } = useAuthSession();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}
