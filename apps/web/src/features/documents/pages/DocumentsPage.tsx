import type { ProcessingStageStatus } from "@contracts";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page, PageHeader } from "@/components/app/page";
import { SelectField } from "@/components/app/select-field";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { ApiProblemError } from "@/shared/api/client";
import {
  formatDateTime,
  formatFileSize,
  humanizeStageStatus
} from "@/shared/lib/formatting";
import { useSpaceScope } from "@/shared/state/spaceScope";
import { listDocuments, uploadDocument, type ListDocumentsQuery } from "../api/documentsApi";

const TERMINAL_STATUSES: ProcessingStageStatus[] = ["completed", "deferred", "failed"];

const fileTypeOptions = [
  { label: "PDF", value: "pdf" },
  { label: "DOCX", value: "docx" },
  { label: "Markdown", value: "md" },
  { label: "Text", value: "txt" }
];

export function DocumentsPage() {
  const navigate = useNavigate();
  const { activeSpace, allSpaces, buildReadScopeParams, isReady, requireConcreteSpace } = useSpaceScope();
  const [page, setPage] = useState(1);
  const [fileTypeFilter, setFileTypeFilter] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const scopeQuery = buildReadScopeParams();
  const documentQuery: ListDocumentsQuery = {
    page,
    page_size: 12,
    file_type: fileTypeFilter || undefined,
    ...scopeQuery
  };

  const documentsQuery = useQuery({
    enabled: isReady,
    queryFn: () => listDocuments(documentQuery),
    queryKey: ["documents", documentQuery],
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      return items.some((item) => !TERMINAL_STATUSES.includes(item.processing_status.overall))
        ? 3000
        : false;
    }
  });

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);

    if (!file) {
      setErrorMessage("Choose a file before uploading.");
      return;
    }

    let concreteSpaceId: string;
    try {
      concreteSpaceId = requireConcreteSpace().id;
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Choose one Space before uploading."
      );
      return;
    }

    setIsUploading(true);
    try {
      const response = await uploadDocument(file, { space_id: concreteSpaceId });
      navigate(`/documents/${response.document_id}`);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to upload the document right now.");
      }
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Library"
        title="Documents"
        description="Upload files, track processing progress, and move between Spaces without leaving the workspace."
      />

      {allSpaces ? (
        <Alert variant="info">
          <AlertTitle>Read scope spans all Spaces</AlertTitle>
          <AlertDescription>
            Upload is disabled until you choose one active Space in the shell selector.
          </AlertDescription>
        </Alert>
      ) : null}

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Document action failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Upload a document</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <p className="text-sm text-muted-foreground">
              Current target: {activeSpace?.name ?? "Choose a Space first"}
            </p>
            <form className="space-y-4" onSubmit={handleUpload}>
              <Input
                accept=".pdf,.docx,.txt,.md,.markdown"
                disabled={isUploading || allSpaces}
                type="file"
                onChange={(event) => setFile(event.currentTarget.files?.[0] ?? null)}
              />
              <Button disabled={allSpaces} type="submit">
                {isUploading ? "Uploading…" : "Upload"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Filter the library</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <SelectField
              emptyLabel="All file types"
              label="File type"
              options={fileTypeOptions}
              placeholder="All file types"
              value={fileTypeFilter}
              onValueChange={(value) => {
                setPage(1);
                setFileTypeFilter(value === "__all__" ? null : value);
              }}
            />
            <p className="text-sm text-muted-foreground">
              Scope-aware reads respect the active Space unless the all-spaces toggle is enabled.
            </p>
          </CardContent>
        </Card>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold tracking-tight">Library</h2>
          <Badge variant="outline">{documentsQuery.data?.total ?? 0} documents</Badge>
        </div>

        {documentsQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Loading documents…</p>
        ) : documentsQuery.error instanceof ApiProblemError ? (
          <Alert variant="destructive">
            <AlertTitle>Unable to load documents</AlertTitle>
            <AlertDescription>{documentsQuery.error.problem.detail}</AlertDescription>
          </Alert>
        ) : documentsQuery.data && documentsQuery.data.items.length > 0 ? (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              {documentsQuery.data.items.map((document) => (
                <Card key={document.id}>
                  <CardContent className="space-y-5 p-6">
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <h3 className="text-lg font-semibold">{document.title}</h3>
                        <p className="text-sm text-muted-foreground">
                          {document.original_filename}
                        </p>
                      </div>
                      <StatusBadge value={document.processing_status.overall} label={humanizeStageStatus(document.processing_status.overall)} />
                    </div>

                    <p className="text-sm text-muted-foreground">
                      {formatFileSize(document.file_size)} · {document.file_type.toUpperCase()} ·{" "}
                      {document.chunk_count} chunks
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Updated {formatDateTime(document.updated_at)}
                    </p>

                    <Button asChild variant="outline">
                      <Link to={`/documents/${document.id}`}>Open detail</Link>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
            <Pagination
              currentPage={page}
              totalPages={Math.max(
                1,
                Math.ceil(documentsQuery.data.total / documentsQuery.data.page_size)
              )}
              onPageChange={setPage}
            />
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            No documents match the current scope and filter yet.
          </p>
        )}
      </section>
    </Page>
  );
}
