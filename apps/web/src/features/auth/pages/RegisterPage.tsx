import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { PageHeader } from "@/components/app/page";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiProblemError } from "@/shared/api/client";
import { useAuthSession } from "@/shared/state/authSession";
import { registerUser } from "../api/authApi";

export function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthSession();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
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
      await registerUser({
        email,
        full_name: fullName || null,
        password
      });
      navigate("/login", {
        replace: true,
        state: {
          email,
          message: "Your account is ready. Sign in to continue."
        }
      });
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to create your account right now.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(440px,0.9fr)] lg:items-center">
      <PageHeader
        eyebrow="Get started"
        title="Create an account"
        description="Start with one Space, then grow into all-spaces views and retrieval workflows later."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border bg-muted/30 p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Spaces
            </p>
            <p className="mt-2 text-sm leading-6 text-foreground">
              Create focused work areas for uploads, search, and pinned facts.
            </p>
          </div>
          <div className="rounded-lg border bg-muted/30 p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Retrieval
            </p>
            <p className="mt-2 text-sm leading-6 text-foreground">
              Move from documents to evidence-backed chat without changing tools.
            </p>
          </div>
        </div>
      </PageHeader>

      <Card className="mx-auto w-full max-w-xl">
        <CardContent className="space-y-6 p-8">
          {errorMessage ? (
            <Alert variant="destructive">
              <AlertTitle>Registration failed</AlertTitle>
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          ) : null}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="register-name">Full name</Label>
              <Input
                id="register-name"
                autoComplete="name"
                disabled={isSubmitting}
                placeholder="Ada Lovelace"
                value={fullName}
                onChange={(event) => setFullName(event.currentTarget.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="register-email">Email</Label>
              <Input
                id="register-email"
                required
                autoComplete="email"
                disabled={isSubmitting}
                placeholder="you@example.com"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.currentTarget.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="register-password">Password</Label>
              <Input
                id="register-password"
                required
                autoComplete="new-password"
                disabled={isSubmitting}
                placeholder="Use at least 8 characters"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
              />
            </div>
            <Button className="w-full" type="submit">
              {isSubmitting ? "Creating account…" : "Create account"}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link className="font-semibold text-primary hover:underline" to="/login">
              Sign in
            </Link>
            .
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
