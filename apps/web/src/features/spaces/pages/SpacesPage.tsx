import { useEffect, useState, type FormEvent } from "react";

import { Page, PageHeader } from "@/components/app/page";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ApiProblemError } from "@/shared/api/client";
import { useSpaceScope } from "@/shared/state/spaceScope";
import { archiveSpace, createSpace, updateSpace } from "../api/spacesApi";

interface SpaceDraft {
  description: string;
  name: string;
}

export function SpacesPage() {
  const {
    activeSpace,
    allSpaces,
    archivedSpaces,
    isReady,
    refreshSpaces,
    setActiveSpace,
    spaces
  } = useSpaceScope();
  const [createName, setCreateName] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [drafts, setDrafts] = useState<Record<string, SpaceDraft>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [savingSpaceId, setSavingSpaceId] = useState<string | null>(null);

  useEffect(() => {
    setDrafts((currentDrafts) => {
      const nextDrafts: Record<string, SpaceDraft> = {};
      for (const space of [...spaces, ...archivedSpaces]) {
        nextDrafts[space.id] = currentDrafts[space.id] ?? {
          description: space.description ?? "",
          name: space.name
        };
      }
      return nextDrafts;
    });
  }, [archivedSpaces, spaces]);

  async function handleCreateSpace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsCreating(true);
    setErrorMessage(null);
    try {
      await createSpace({
        description: createDescription || null,
        name: createName
      });
      setCreateDescription("");
      setCreateName("");
      await refreshSpaces();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to create the Space right now.");
      }
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSpaceUpdate(spaceId: string, payload: Record<string, unknown>) {
    setSavingSpaceId(spaceId);
    setErrorMessage(null);
    try {
      const updated = await updateSpace(spaceId, payload);
      await refreshSpaces();
      if (updated.archived_at === null) {
        setActiveSpace(updated);
      }
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to update the Space right now.");
      }
    } finally {
      setSavingSpaceId(null);
    }
  }

  async function handleArchiveSpace(spaceId: string) {
    setSavingSpaceId(spaceId);
    setErrorMessage(null);
    try {
      await archiveSpace(spaceId);
      await refreshSpaces();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to archive the Space right now.");
      }
    } finally {
      setSavingSpaceId(null);
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Workspace scope"
        title="Spaces"
        description="Organize documents by workspace and keep the current read scope explicit."
      />

      {allSpaces ? (
        <Alert variant="info">
          <AlertTitle>All-spaces mode is on</AlertTitle>
          <AlertDescription>
            Read views can span every Space right now. Actions that need one target Space should ask you to pick it explicitly.
          </AlertDescription>
        </Alert>
      ) : null}

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Space action failed</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Create a Space</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleCreateSpace}>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="space-name">
                Name
              </label>
              <Input
                id="space-name"
                required
                disabled={isCreating}
                placeholder="Research workspace"
                value={createName}
                onChange={(event) => setCreateName(event.currentTarget.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="space-description">
                Description
              </label>
              <Input
                id="space-description"
                disabled={isCreating}
                placeholder="Optional note for the team"
                value={createDescription}
                onChange={(event) => setCreateDescription(event.currentTarget.value)}
              />
            </div>
            <Button type="submit">{isCreating ? "Creating Space…" : "Create Space"}</Button>
          </form>
        </CardContent>
      </Card>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold tracking-tight">Active Spaces</h2>
          <Badge variant="outline">{isReady ? `${spaces.length} active` : "Loading"}</Badge>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {spaces.map((space) => {
            const draft = drafts[space.id] ?? {
              description: space.description ?? "",
              name: space.name
            };

            return (
              <Card key={space.id}>
                <CardContent className="space-y-5 p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <h3 className="text-lg font-semibold">{space.name}</h3>
                      <p className="text-sm text-muted-foreground">
                        {space.description || "No description"}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {space.id === activeSpace?.id ? <StatusBadge label="Active" value="active" /> : null}
                      {space.is_default ? <Badge variant="outline">Default</Badge> : null}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Name</label>
                    <Input
                      value={draft.name}
                      onChange={(event) =>
                        setDrafts((currentDrafts) => ({
                          ...currentDrafts,
                          [space.id]: {
                            ...draft,
                            name: event.currentTarget.value
                          }
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Description</label>
                    <Input
                      value={draft.description}
                      onChange={(event) =>
                        setDrafts((currentDrafts) => ({
                          ...currentDrafts,
                          [space.id]: {
                            ...draft,
                            description: event.currentTarget.value
                          }
                        }))
                      }
                    />
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <Button
                      variant="outline"
                      onClick={() =>
                        void handleSpaceUpdate(space.id, {
                          description: draft.description || null,
                          name: draft.name
                        })
                      }
                    >
                      {savingSpaceId === space.id ? "Saving…" : "Save"}
                    </Button>
                    <Button variant="ghost" onClick={() => setActiveSpace(space)}>
                      Use as active Space
                    </Button>
                    {!space.is_default ? (
                      <Button
                        variant="ghost"
                        onClick={() => void handleSpaceUpdate(space.id, { is_default: true })}
                      >
                        Set as default
                      </Button>
                    ) : null}
                    {!space.is_default ? (
                      <Button
                        variant="ghost"
                        className="text-destructive hover:text-destructive"
                        onClick={() => void handleArchiveSpace(space.id)}
                      >
                        Archive
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <Separator />

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold tracking-tight">Archived Spaces</h2>
          <Badge variant="outline">{archivedSpaces.length} archived</Badge>
        </div>
        {archivedSpaces.length === 0 ? (
          <p className="text-sm text-muted-foreground">No archived Spaces yet.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {archivedSpaces.map((space) => (
              <Card key={space.id}>
                <CardContent className="space-y-3 p-6">
                  <div className="flex items-center justify-between gap-4">
                    <h3 className="text-lg font-semibold">{space.name}</h3>
                    <StatusBadge label="Archived" value="inactive" />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {space.description || "No description"}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Archived Spaces stay visible for read history but are not active upload targets.
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
    </Page>
  );
}
