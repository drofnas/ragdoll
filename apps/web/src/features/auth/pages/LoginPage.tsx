import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { PageHeader } from "@/components/app/page";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiProblemError } from "@/shared/api/client";
import { useAuthSession } from "@/shared/state/authSession";

interface LoginLocationState {
  email?: string;
  message?: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, login, status } = useAuthSession();
  const [email, setEmail] = useState((location.state as LoginLocationState | null)?.email ?? "");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await login({ password, username: email });
      navigate("/dashboard", { replace: true });
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to sign in right now.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(420px,0.9fr)] lg:items-center">
      <PageHeader
        eyebrow="Welcome back"
        title="Sign in"
        description="Use your Ragdoll account to open the workspace experience."
      >
        <div className="rounded-lg border bg-muted/30 p-5 text-sm leading-6 text-muted-foreground">
          Workspaces, retrieval, document operations, and scoped state tools all open from the same signed-in shell.
        </div>
      </PageHeader>

      <Card className="mx-auto w-full max-w-xl">
        <CardContent className="space-y-6 p-8">
          {(location.state as LoginLocationState | null)?.message ? (
            <Alert variant="success">
              <AlertTitle>Account ready</AlertTitle>
              <AlertDescription>
                {(location.state as LoginLocationState | null)?.message}
              </AlertDescription>
            </Alert>
          ) : null}

          {errorMessage ? (
            <Alert variant="destructive">
              <AlertTitle>Sign-in failed</AlertTitle>
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          ) : null}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="login-email">Email</Label>
              <Input
                id="login-email"
                required
                autoComplete="email"
                disabled={isSubmitting || status === "loading"}
                placeholder="you@example.com"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.currentTarget.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="login-password">Password</Label>
              <Input
                id="login-password"
                required
                autoComplete="current-password"
                disabled={isSubmitting || status === "loading"}
                placeholder="Your password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
              />
            </div>
            <Button className="w-full" disabled={status === "loading"} type="submit">
              {isSubmitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground">
            Need an account?{" "}
            <Link className="font-semibold text-primary hover:underline" to="/register">
              Register here
            </Link>
            .
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
