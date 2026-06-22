import { PropsWithChildren } from "react";
import { Center, Loader } from "@mantine/core";
import { Navigate } from "react-router-dom";

import { useAuthSession } from "../../shared/state/authSession";

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { isAuthenticated, status } = useAuthSession();

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

  return <>{children}</>;
}
