import { useEffect, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ApiProblemError } from "@/shared/api/client";
import { formatDateTime } from "@/shared/lib/formatting";
import { useAuthSession } from "@/shared/state/authSession";
import { updateCurrentUser } from "../../auth/api/authApi";
import { readUsageSummary } from "../api/accountApi";

export function AccountPage() {
  const { currentUser, refreshSession } = useAuthSession();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const usageQuery = useQuery({
    queryFn: readUsageSummary,
    queryKey: ["usage-summary"]
  });

  useEffect(() => {
    setEmail(currentUser?.email ?? "");
    setFullName(currentUser?.full_name ?? "");
  }, [currentUser]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsSaving(true);

    try {
      await updateCurrentUser({
        current_password: currentPassword || null,
        email,
        full_name: fullName || null,
        new_password: newPassword || null
      });
      await refreshSession();
      setCurrentPassword("");
      setNewPassword("");
      setSuccessMessage("Profile updated.");
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to save your account changes right now.");
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Profile"
        title="Account"
        description="Manage your profile, password, and current usage envelope."
      />

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Account update failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      {successMessage ? (
        <Alert variant="success">
          <AlertTitle>Saved</AlertTitle>
          <AlertDescription>{successMessage}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="account-name">
                  Full name
                </label>
                <Input
                  id="account-name"
                  autoComplete="name"
                  value={fullName}
                  onChange={(event) => setFullName(event.currentTarget.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="account-email">
                  Email
                </label>
                <Input
                  id="account-email"
                  autoComplete="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.currentTarget.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="account-current-password">
                  Current password
                </label>
                <Input
                  id="account-current-password"
                  autoComplete="current-password"
                  placeholder="Required only when changing your password"
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.currentTarget.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="account-new-password">
                  New password
                </label>
                <Input
                  id="account-new-password"
                  autoComplete="new-password"
                  placeholder="Leave blank to keep the current password"
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.currentTarget.value)}
                />
              </div>
              <Button type="submit">{isSaving ? "Saving…" : "Save account changes"}</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
            <CardTitle>Profile state</CardTitle>
            <StatusBadge label={currentUser?.is_active ? "Active" : "Disabled"} value={currentUser?.is_active ? "active" : "inactive"} />
          </CardHeader>
          <CardContent className="space-y-3">
            <p>Last login: {formatDateTime(currentUser?.last_login)}</p>
            <p>Admin access: {currentUser?.is_admin ? "Yes" : "No"}</p>
            <p>Password rotation required: {currentUser?.must_change_password ? "Yes" : "No"}</p>
            <Separator />
            <div className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Instance policy
              </h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>Usage limits are controlled by self-hosted instance configuration.</li>
                <li>Administrators can manage access, password rotation, and operator workflows.</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
          <CardTitle>Usage summary</CardTitle>
          <Badge variant="outline">Config-driven</Badge>
        </CardHeader>
        <CardContent>
          {usageQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading usage…</p>
          ) : usageQuery.error instanceof ApiProblemError ? (
            <Alert variant="destructive">
              <AlertTitle>Unable to load usage</AlertTitle>
              <AlertDescription>{usageQuery.error.problem.detail}</AlertDescription>
            </Alert>
          ) : usageQuery.data ? (
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="bg-background/65 shadow-none">
                <CardContent className="space-y-2 p-5">
                  <p className="text-sm font-semibold">Documents</p>
                  <p className="text-3xl font-semibold">{usageQuery.data.usage.documents}</p>
                  <p className="text-sm text-muted-foreground">
                    Limit: {usageQuery.data.limits.documents ?? "unlimited"}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-background/65 shadow-none">
                <CardContent className="space-y-2 p-5">
                  <p className="text-sm font-semibold">Chunks</p>
                  <p className="text-3xl font-semibold">{usageQuery.data.usage.chunks}</p>
                  <p className="text-sm text-muted-foreground">
                    Limit: {usageQuery.data.limits.chunks ?? "unlimited"}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-background/65 shadow-none">
                <CardContent className="space-y-2 p-5">
                  <p className="text-sm font-semibold">Storage</p>
                  <p className="text-3xl font-semibold">{usageQuery.data.usage.storage_bytes}</p>
                  <p className="text-sm text-muted-foreground">
                    Limit: {usageQuery.data.limits.storage_bytes ?? "unlimited"}
                  </p>
                </CardContent>
              </Card>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </Page>
  );
}
