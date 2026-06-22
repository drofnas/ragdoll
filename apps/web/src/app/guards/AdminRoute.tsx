import { PropsWithChildren } from "react";
import { Center, Loader } from "@mantine/core";
import { Navigate } from "react-router-dom";

import { useAuthSession } from "../../shared/state/authSession";

export function AdminRoute({ children }: PropsWithChildren) {
  const { isAuthenticated, isAdmin, status } = useAuthSession();

  if (status === "loading") {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}
