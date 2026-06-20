import { PropsWithChildren } from "react";
import { Navigate } from "react-router-dom";

import { useAuthSession } from "../../shared/state/authSession";

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { isAuthenticated } = useAuthSession();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
