import { useState } from "react";
import { Link } from "react-router-dom";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useAuthSession } from "@/shared/state/authSession";

export function AuthUnavailablePanel() {
  const { refreshSession, sessionErrorMessage } = useAuthSession();
  const [isRetrying, setIsRetrying] = useState(false);

  async function handleRetry() {
    setIsRetrying(true);
    try {
      await refreshSession();
    } catch {
      // The auth provider records the unavailable state and user-facing message.
    } finally {
      setIsRetrying(false);
    }
  }

  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Alert className="max-w-xl" variant="info">
        <AlertTitle>Workspace connection unavailable</AlertTitle>
        <AlertDescription className="space-y-4">
          <p>
            The app could not reach the backend, but your saved session is still present on this
            device.
          </p>
          {sessionErrorMessage ? (
            <p className="text-muted-foreground">{sessionErrorMessage}</p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button disabled={isRetrying} size="sm" onClick={() => void handleRetry()}>
              {isRetrying ? "Retrying..." : "Retry connection"}
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link to="/status">Open status</Link>
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  );
}
