import { useState, type FormEvent } from "react";
import { Alert, Anchor, Button, Card, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { ApiProblemError } from "../../../shared/api/client";
import { useAuthSession } from "../../../shared/state/authSession";
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
    <Card withBorder radius="lg" shadow="sm" maw={520} mx="auto" p="xl">
      <Stack gap="lg">
        <Stack gap={4}>
          <Title order={2}>Create an account</Title>
          <Text c="dimmed" size="sm">
            Start with one Space, then grow into all-spaces views and retrieval workflows later.
          </Text>
        </Stack>

        {errorMessage ? (
          <Alert color="red" title="Registration failed">
            {errorMessage}
          </Alert>
        ) : null}

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              autoComplete="name"
              disabled={isSubmitting}
              label="Full name"
              placeholder="Ada Lovelace"
              value={fullName}
              onChange={(event) => setFullName(event.currentTarget.value)}
            />
            <TextInput
              required
              autoComplete="email"
              disabled={isSubmitting}
              label="Email"
              placeholder="you@example.com"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.currentTarget.value)}
            />
            <PasswordInput
              required
              autoComplete="new-password"
              disabled={isSubmitting}
              label="Password"
              placeholder="Use at least 8 characters"
              value={password}
              onChange={(event) => setPassword(event.currentTarget.value)}
            />
            <Button loading={isSubmitting} type="submit">
              Create account
            </Button>
          </Stack>
        </form>

        <Text size="sm">
          Already have an account?{" "}
          <Anchor component={Link} to="/login">
            Sign in
          </Anchor>
          .
        </Text>
      </Stack>
    </Card>
  );
}
