import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { ApiProblemError } from "@/shared/api/client";
import { readRuntimeStatus } from "@/shared/api/runtimeStatus";
import { formatDateTime } from "@/shared/lib/formatting";
import {
  readAdminUser,
  readAdminUsers,
  readEffectiveLimits,
  updateAdminUser
} from "../api/adminApi";

export function AdminHomePage() {
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const usersQuery = useQuery({
    queryFn: () => readAdminUsers(),
    queryKey: ["admin-users"]
  });
  const limitsQuery = useQuery({
    queryFn: readEffectiveLimits,
    queryKey: ["admin-effective-limits"]
  });
  const statusQuery = useQuery({
    queryFn: readRuntimeStatus,
    queryKey: ["admin-runtime-status"]
  });
  const userDetailQuery = useQuery({
    enabled: Boolean(selectedUserId),
    queryFn: () => readAdminUser(selectedUserId!),
    queryKey: ["admin-user", selectedUserId]
  });

  async function toggleUserField(
    field: "is_active" | "is_admin" | "must_change_password",
    value: boolean
  ) {
    if (!selectedUserId) {
      return;
    }
    await updateAdminUser(selectedUserId, { [field]: value });
    await Promise.all([usersQuery.refetch(), userDetailQuery.refetch()]);
    setFeedback("User settings updated.");
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Operations"
        title="Operator admin"
        description="Review runtime readiness, inspect effective instance limits, and manage user access for this self-hosted installation."
      />

      {feedback ? (
        <Alert variant="success">
          <AlertTitle>Saved</AlertTitle>
          <AlertDescription>{feedback}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
            <CardTitle>Runtime status</CardTitle>
            <StatusBadge value={statusQuery.data?.status ?? "loading"} />
          </CardHeader>
          <CardContent>
            {statusQuery.error instanceof ApiProblemError ? (
              <Alert variant="destructive">
                <AlertTitle>Unable to load runtime status</AlertTitle>
                <AlertDescription>{statusQuery.error.problem.detail}</AlertDescription>
              </Alert>
            ) : statusQuery.data ? (
              <div className="space-y-3">
                {Object.entries(statusQuery.data.services).map(([name, service]) => (
                  <div key={name} className="flex items-center justify-between gap-4">
                    <span className="capitalize">{name}</span>
                    <StatusBadge value={service.status} />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Loading runtime status…</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Effective instance limits</CardTitle>
          </CardHeader>
          <CardContent>
            {limitsQuery.error instanceof ApiProblemError ? (
              <Alert variant="destructive">
                <AlertTitle>Unable to load limits</AlertTitle>
                <AlertDescription>{limitsQuery.error.problem.detail}</AlertDescription>
              </Alert>
            ) : limitsQuery.data ? (
              <div className="space-y-3 text-sm">
                <p>Documents: {limitsQuery.data.documents ?? "unlimited"}</p>
                <p>Storage: {limitsQuery.data.storage_bytes ?? "unlimited"}</p>
                <p>Tokens / 5h: {limitsQuery.data.tokens_5h ?? "unlimited"}</p>
                <p>Tokens / week: {limitsQuery.data.tokens_week ?? "unlimited"}</p>
                <p>
                  Max file size: {limitsQuery.data.max_file_size_bytes ?? "unlimited"} bytes
                </p>
                <p>Per-document chunks: {limitsQuery.data.per_document_chunks}</p>
                <p>Retrieval chunks: {limitsQuery.data.retrieval_chunks}</p>
                <p>Output tokens: {limitsQuery.data.output_tokens}</p>
                <p>
                  Upload rate limit:{" "}
                  {limitsQuery.data.upload_rate_limit.enabled
                    ? `${limitsQuery.data.upload_rate_limit.requests} per ${limitsQuery.data.upload_rate_limit.window_seconds}s`
                    : "disabled"}
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Loading limits…</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Selected user</CardTitle>
          </CardHeader>
          <CardContent>
            {userDetailQuery.error instanceof ApiProblemError ? (
              <Alert variant="destructive">
                <AlertTitle>Unable to load user</AlertTitle>
                <AlertDescription>{userDetailQuery.error.problem.detail}</AlertDescription>
              </Alert>
            ) : userDetailQuery.data ? (
              <div className="space-y-5">
                <div className="space-y-1">
                  <p className="font-semibold">
                    {userDetailQuery.data.full_name ?? userDetailQuery.data.email}
                  </p>
                  <p className="text-sm text-muted-foreground">{userDetailQuery.data.email}</p>
                  <p className="text-sm text-muted-foreground">
                    Last login: {formatDateTime(userDetailQuery.data.last_login)}
                  </p>
                </div>

                <label className="flex items-center justify-between gap-4 rounded-md border bg-muted/20 px-3 py-2">
                  <span className="text-sm font-medium">Active account</span>
                  <Switch
                    checked={userDetailQuery.data.is_active}
                    onCheckedChange={(checked) => void toggleUserField("is_active", Boolean(checked))}
                  />
                </label>
                <label className="flex items-center justify-between gap-4 rounded-md border bg-muted/20 px-3 py-2">
                  <span className="text-sm font-medium">Admin access</span>
                  <Switch
                    checked={userDetailQuery.data.is_admin}
                    onCheckedChange={(checked) => void toggleUserField("is_admin", Boolean(checked))}
                  />
                </label>
                <label className="flex items-center justify-between gap-4 rounded-md border bg-muted/20 px-3 py-2">
                  <span className="text-sm font-medium">Require password change</span>
                  <Switch
                    checked={userDetailQuery.data.must_change_password}
                    onCheckedChange={(checked) =>
                      void toggleUserField("must_change_password", Boolean(checked))
                    }
                  />
                </label>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Choose a user from the table to inspect and manage account state.
              </p>
            )}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>User management</CardTitle>
        </CardHeader>
        <CardContent>
          {usersQuery.error instanceof ApiProblemError ? (
            <Alert variant="destructive">
              <AlertTitle>Unable to load users</AlertTitle>
              <AlertDescription>{usersQuery.error.problem.detail}</AlertDescription>
            </Alert>
          ) : usersQuery.data ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Admin</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead>Last login</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {usersQuery.data.items.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-semibold">{user.full_name ?? user.email}</p>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                      </div>
                    </TableCell>
                    <TableCell>{user.is_admin ? "Yes" : "No"}</TableCell>
                    <TableCell>{user.is_active ? "Yes" : "No"}</TableCell>
                    <TableCell>{formatDateTime(user.last_login)}</TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" onClick={() => setSelectedUserId(user.id)}>
                        Inspect
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">Loading users…</p>
          )}
        </CardContent>
      </Card>
    </Page>
  );
}
