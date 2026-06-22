import { useState, type FormEvent } from "react";
import { Alert, Anchor, Button, Card, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiProblemError } from "../../../shared/api/client";
import { useAuthSession } from "../../../shared/state/authSession";

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
    <Card withBorder radius="lg" shadow="sm" maw={480} mx="auto" p="xl">
      <Stack gap="lg">
        <Stack gap={4}>
          <Title order={2}>Sign in</Title>
          <Text c="dimmed" size="sm">
            Use your Ragdoll account to open the workspace experience.
          </Text>
        </Stack>

        {(location.state as LoginLocationState | null)?.message ? (
          <Alert color="teal" title="Account ready">
            {(location.state as LoginLocationState | null)?.message}
          </Alert>
        ) : null}

        {errorMessage ? (
          <Alert color="red" title="Sign-in failed">
            {errorMessage}
          </Alert>
        ) : null}

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              required
              autoComplete="email"
              disabled={isSubmitting || status === "loading"}
              label="Email"
              placeholder="you@example.com"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.currentTarget.value)}
            />
            <PasswordInput
              required
              autoComplete="current-password"
              disabled={isSubmitting || status === "loading"}
              label="Password"
              placeholder="Your password"
              value={password}
              onChange={(event) => setPassword(event.currentTarget.value)}
            />
            <Button loading={isSubmitting} type="submit">
              Sign in
            </Button>
          </Stack>
        </form>

        <Text size="sm">
          Need an account?{" "}
          <Anchor component={Link} to="/register">
            Register here
          </Anchor>
          .
        </Text>
      </Stack>
    </Card>
  );
}
