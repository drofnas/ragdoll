import type { SpaceResponse, SpaceUpdateRequest } from "@contracts";
import { Archive, Check, Pencil } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { Page, PageHeader } from "@/components/app/page";
import { StatusBadge } from "@/components/app/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Toggle } from "@/components/ui/toggle";
import { ApiProblemError } from "@/shared/api/client";
import { useSpaceScope } from "@/shared/state/spaceScope";
import { archiveSpace, createSpace, updateSpace } from "../api/spacesApi";

interface SpaceDraft {
  description: string;
  isDefault: boolean;
  name: string;
}

function draftFromSpace(space: SpaceResponse): SpaceDraft {
  return {
    description: space.description ?? "",
    isDefault: space.is_default,
    name: space.name
  };
}

function formatCount(value: number) {
  return String(value);
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
  const [drafts, setDrafts] = useState<Record<string, SpaceDraft>>({});
  const [editingSpaceId, setEditingSpaceId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [savingSpaceId, setSavingSpaceId] = useState<string | null>(null);

  useEffect(() => {
    setDrafts((currentDrafts) => {
      const nextDrafts: Record<string, SpaceDraft> = {};
      for (const space of [...spaces, ...archivedSpaces]) {
        nextDrafts[space.id] =
          editingSpaceId === space.id && currentDrafts[space.id]
            ? currentDrafts[space.id]
            : draftFromSpace(space);
      }
      return nextDrafts;
    });
  }, [archivedSpaces, editingSpaceId, spaces]);

  async function handleCreateSpace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = createName.trim();
    if (!name) {
      return;
    }

    setIsCreating(true);
    setErrorMessage(null);
    try {
      await createSpace({ name });
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

  async function handleSpaceUpdate(spaceId: string, payload: SpaceUpdateRequest) {
    setSavingSpaceId(spaceId);
    setErrorMessage(null);
    try {
      const updated = await updateSpace(spaceId, payload);
      await refreshSpaces();
      if (updated.archived_at === null && updated.id === activeSpace?.id) {
        setActiveSpace(updated);
      }
      return true;
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setErrorMessage(error.problem.detail);
      } else {
        setErrorMessage("Unable to update the Space right now.");
      }
      return false;
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

  function updateDraft(spaceId: string, patch: Partial<SpaceDraft>) {
    const space = [...spaces, ...archivedSpaces].find((item) => item.id === spaceId);
    if (!space) {
      return;
    }

    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      [spaceId]: {
        ...(currentDrafts[spaceId] ?? draftFromSpace(space)),
        ...patch
      }
    }));
  }

  function handleEditOpen(space: SpaceResponse, open: boolean) {
    if (open) {
      setDrafts((currentDrafts) => ({
        ...currentDrafts,
        [space.id]: draftFromSpace(space)
      }));
      setEditingSpaceId(space.id);
      return;
    }

    if (editingSpaceId === space.id) {
      setEditingSpaceId(null);
    }
  }

  async function handleSaveSpace(event: FormEvent<HTMLFormElement>, space: SpaceResponse) {
    event.preventDefault();
    const draft = drafts[space.id] ?? draftFromSpace(space);
    const payload: SpaceUpdateRequest = {
      description: draft.description || null,
      name: draft.name
    };

    if (!space.is_default && draft.isDefault) {
      payload.is_default = true;
    }

    const saved = await handleSpaceUpdate(space.id, payload);
    if (saved) {
      setEditingSpaceId(null);
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
        <CardContent className="p-4">
          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleCreateSpace}>
            <div className="grid flex-1 gap-2">
              <Label htmlFor="space-name">Name</Label>
              <Input
                id="space-name"
                required
                disabled={isCreating}
                placeholder="Research workspace"
                value={createName}
                onChange={(event) => setCreateName(event.currentTarget.value)}
              />
            </div>
            <Button disabled={isCreating || createName.trim().length === 0} type="submit">
              {isCreating ? "Creating Space..." : "Create Space"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold tracking-tight">Active Spaces</h2>
          <Badge variant="outline">{isReady ? `${spaces.length} active` : "Loading"}</Badge>
        </div>

        {spaces.length === 0 ? (
          <p className="text-sm text-muted-foreground">No active Spaces yet.</p>
        ) : (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-28">Documents</TableHead>
                    <TableHead className="w-24">Pins</TableHead>
                    <TableHead className="w-48 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {spaces.map((space) => {
                    const draft = drafts[space.id] ?? draftFromSpace(space);
                    const isSaving = savingSpaceId === space.id;
                    const nameInputId = `space-${space.id}-name`;
                    const descriptionInputId = `space-${space.id}-description`;
                    const defaultToggleId = `space-${space.id}-default`;

                    return (
                      <TableRow key={space.id}>
                        <TableCell>
                          <div className="flex flex-col gap-2">
                            <span className="font-medium">{space.name}</span>
                            <span className="flex flex-wrap gap-2">
                              {space.id === activeSpace?.id ? <StatusBadge label="Active" value="active" /> : null}
                              {space.is_default ? <Badge variant="outline">Default</Badge> : null}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="max-w-md text-muted-foreground">
                          {space.description || "No description"}
                        </TableCell>
                        <TableCell>{formatCount(space.document_count)}</TableCell>
                        <TableCell>{formatCount(space.tracked_field_count)}</TableCell>
                        <TableCell>
                          <div className="flex justify-end gap-2">
                            <Popover
                              modal
                              open={editingSpaceId === space.id}
                              onOpenChange={(open) => handleEditOpen(space, open)}
                            >
                              <PopoverTrigger asChild>
                                <Button size="sm" variant="outline">
                                  <Pencil aria-hidden="true" />
                                  Edit
                                </Button>
                              </PopoverTrigger>
                              <PopoverContent
                                align="end"
                                className="w-[min(22rem,calc(100vw-2rem))]"
                              >
                                <form className="space-y-4" onSubmit={(event) => void handleSaveSpace(event, space)}>
                                  <div className="space-y-1">
                                    <p className="text-sm font-semibold">Edit Space</p>
                                    <p className="text-xs text-muted-foreground">{space.name}</p>
                                  </div>

                                  <div className="space-y-2">
                                    <Label htmlFor={nameInputId}>Name</Label>
                                    <Input
                                      id={nameInputId}
                                      required
                                      disabled={isSaving}
                                      value={draft.name}
                                      onChange={(event) =>
                                        updateDraft(space.id, { name: event.currentTarget.value })
                                      }
                                    />
                                  </div>

                                  <div className="space-y-2">
                                    <Label htmlFor={descriptionInputId}>Description</Label>
                                    <Textarea
                                      id={descriptionInputId}
                                      disabled={isSaving}
                                      value={draft.description}
                                      onChange={(event) =>
                                        updateDraft(space.id, { description: event.currentTarget.value })
                                      }
                                    />
                                  </div>

                                  <div className="flex items-center justify-between gap-3 rounded-md border p-3">
                                    <Label htmlFor={defaultToggleId}>Default</Label>
                                    <Toggle
                                      id={defaultToggleId}
                                      disabled={space.is_default || isSaving}
                                      pressed={draft.isDefault}
                                      size="sm"
                                      variant="outline"
                                      onPressedChange={(isDefault) =>
                                        updateDraft(space.id, { isDefault })
                                      }
                                    >
                                      {draft.isDefault ? <Check aria-hidden="true" /> : null}
                                      Default
                                    </Toggle>
                                  </div>

                                  <div className="flex justify-end gap-2">
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      onClick={() => setEditingSpaceId(null)}
                                    >
                                      Cancel
                                    </Button>
                                    <Button disabled={isSaving || draft.name.trim().length === 0} type="submit">
                                      {isSaving ? "Saving..." : "Save"}
                                    </Button>
                                  </div>
                                </form>
                              </PopoverContent>
                            </Popover>
                            <Button
                              className="text-destructive hover:text-destructive"
                              disabled={space.is_default || isSaving}
                              size="sm"
                              variant="ghost"
                              onClick={() => void handleArchiveSpace(space.id)}
                            >
                              <Archive aria-hidden="true" />
                              Archive
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
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
