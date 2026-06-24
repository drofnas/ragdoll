import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { ApiProblemError, resolveApiBaseUrl } from "@/shared/api/client";
import { readRuntimeStatus } from "@/shared/api/runtimeStatus";
import { formatDateTime, humanizeLabel } from "@/shared/lib/formatting";

export function StatusPage() {
  const statusQuery = useQuery({
    queryFn: readRuntimeStatus,
    queryKey: ["public-runtime-status"],
    refetchInterval: 30000
  });
  const backendStatusUrl = `${resolveApiBaseUrl()}/status`;
  const backendStatusJsonUrl = `${backendStatusUrl}?type=json`;

  return (
    <Page>
      <PageHeader
        eyebrow="Public Runtime Status"
        title="Workspace status"
        description="Review live backend readiness, storage and model availability, and the current service posture for this self-hosted workspace."
        actions={<StatusBadge value={statusQuery.data?.status ?? "unknown"} />}
      >
        <div className="flex flex-wrap gap-4 text-sm font-medium">
          <a
            className="text-primary underline-offset-4 hover:underline"
            href={backendStatusUrl}
            target="_blank"
            rel="noreferrer"
          >
            Raw backend status page
          </a>
          <a
            className="text-primary underline-offset-4 hover:underline"
            href={backendStatusJsonUrl}
            target="_blank"
            rel="noreferrer"
          >
            Runtime JSON
          </a>
        </div>
      </PageHeader>

      {statusQuery.error instanceof ApiProblemError ? (
        <Alert variant="destructive">
          <AlertTitle>Unable to load runtime status</AlertTitle>
          <AlertDescription>{statusQuery.error.problem.detail}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Application</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-2xl font-semibold">
              {statusQuery.data?.application.name ?? "Loading…"}
            </p>
            <p>Environment: {statusQuery.data?.application.environment ?? "Loading…"}</p>
            <p>Version: {statusQuery.data?.application.version ?? "Loading…"}</p>
            <p>Generated: {formatDateTime(statusQuery.data?.application.generated_at)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Supabase-backed services</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <span>Overall</span>
              <StatusBadge value={statusQuery.data?.supabase.status ?? "unknown"} />
            </div>
            <p>{statusQuery.data?.supabase.detail ?? "Checking runtime dependencies…"}</p>
            <p className="text-sm text-muted-foreground">
              Backend: {statusQuery.data?.supabase.backend ?? "unknown"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Ollama</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <span>Overall</span>
              <StatusBadge value={statusQuery.data?.ollama.status ?? "unknown"} />
            </div>
            <p>{statusQuery.data?.ollama.detail ?? "Checking model catalog…"}</p>
            <p className="text-sm text-muted-foreground">
              Catalog reachable: {statusQuery.data?.ollama.catalog_reachable ? "Yes" : "No"}
            </p>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
          <CardTitle>Service overview</CardTitle>
          {statusQuery.data ? <StatusBadge value={statusQuery.data.status} /> : null}
        </CardHeader>
        <CardContent>
          {statusQuery.data ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Service</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Detail</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(statusQuery.data.services).map(([name, service]) => (
                  <TableRow key={name}>
                    <TableCell>{humanizeLabel(name)}</TableCell>
                    <TableCell>
                      <StatusBadge value={service.status} />
                    </TableCell>
                    <TableCell>{service.detail}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">Loading service overview…</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Configured models</CardTitle>
        </CardHeader>
        <CardContent>
          {statusQuery.data?.ollama.configured_models.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Roles</TableHead>
                  <TableHead>Detail</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {statusQuery.data.ollama.configured_models.map((model) => (
                  <TableRow key={model.name}>
                    <TableCell>{model.name}</TableCell>
                    <TableCell>
                      <StatusBadge value={model.status} />
                    </TableCell>
                    <TableCell>{model.roles.length ? model.roles.join(", ") : "none"}</TableCell>
                    <TableCell>{model.detail}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">
              No configured models were reported.
            </p>
          )}
        </CardContent>
      </Card>
    </Page>
  );
}
