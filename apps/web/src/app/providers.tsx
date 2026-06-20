import { PropsWithChildren, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MantineProvider, createTheme } from "@mantine/core";

import { AuthSessionProvider } from "../shared/state/authSession";
import { SpaceScopeProvider } from "../shared/state/spaceScope";

const appTheme = createTheme({
  fontFamily: "\"Avenir Next\", \"Segoe UI\", sans-serif",
  headings: {
    fontFamily: "\"Avenir Next\", \"Segoe UI\", sans-serif",
    fontWeight: "700"
  },
  primaryColor: "teal",
  defaultRadius: "md"
});

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
      <MantineProvider theme={appTheme}>
        <AuthSessionProvider>
          <SpaceScopeProvider>{children}</SpaceScopeProvider>
        </AuthSessionProvider>
      </MantineProvider>
    </QueryClientProvider>
  );
}
