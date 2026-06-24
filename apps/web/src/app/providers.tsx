import { PropsWithChildren, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AuthSessionProvider } from "../shared/state/authSession";
import { SpaceScopeProvider } from "../shared/state/spaceScope";

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            staleTime: 30_000
          }
        }
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthSessionProvider>
        <SpaceScopeProvider>{children}</SpaceScopeProvider>
      </AuthSessionProvider>
    </QueryClientProvider>
  );
}
