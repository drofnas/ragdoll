import { Menu, Shield, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

import { SelectField } from "@/components/app/select-field";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { useAuthSession } from "@/shared/state/authSession";
import { useSpaceScope } from "@/shared/state/spaceScope";

const primaryLinks = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Spaces", to: "/spaces" },
  { label: "Documents", to: "/documents" },
  { label: "Search", to: "/search" },
  { label: "Chat", to: "/chat" },
  { label: "Entities", to: "/entities" },
  { label: "Pinned facts", to: "/pinned-facts" },
  { label: "Changes", to: "/changes" },
  { label: "Account", to: "/account" }
] as const;

function isActivePath(currentPath: string, targetPath: string) {
  return currentPath === targetPath || currentPath.startsWith(`${targetPath}/`);
}

function NavRail({
  currentPath,
  isAdmin,
  onNavigate
}: {
  currentPath: string;
  isAdmin: boolean;
  onNavigate?: () => void;
}) {
  return (
    <nav className="grid gap-1">
      {primaryLinks.map((item) => (
        <Link
          key={item.to}
          to={item.to}
          className={cn(
            "flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors",
            isActivePath(currentPath, item.to)
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          )}
          onClick={onNavigate}
        >
          <span>{item.label}</span>
          {isActivePath(currentPath, item.to) ? <Sparkles className="h-4 w-4" /> : null}
        </Link>
      ))}
      {isAdmin ? (
        <Link
          to="/admin"
          className={cn(
            "flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors",
            isActivePath(currentPath, "/admin")
              ? "bg-destructive text-destructive-foreground"
              : "text-destructive hover:bg-destructive/10"
          )}
          onClick={onNavigate}
        >
          <span>Admin</span>
          <Shield className="h-4 w-4" />
        </Link>
      ) : null}
    </nav>
  );
}

function ScopeSelect({
  activeSpaceId,
  allSpaces,
  disabled,
  onValueChange,
  options
}: {
  activeSpaceId: string | null;
  allSpaces: boolean;
  disabled: boolean;
  onValueChange: (value: string) => void;
  options: Array<{ label: string; value: string }>;
}) {
  return (
    <SelectField
      disabled={disabled}
      emptyLabel="All Spaces"
      label="Space"
      options={options}
      placeholder="Choose a Space"
      value={allSpaces ? "__all__" : activeSpaceId}
      onValueChange={onValueChange}
    />
  );
}

export function AuthenticatedShell() {
  const { currentUser, isAdmin, logout } = useAuthSession();
  const { activeSpace, allSpaces, isReady, setActiveSpace, setAllSpaces, spaces } = useSpaceScope();
  const { pathname } = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isChatRoute = isActivePath(pathname, "/chat");

  const spaceOptions = spaces.map((space) => ({ label: space.name, value: space.id }));

  function handleScopeChange(value: string) {
    if (value === "__all__") {
      setAllSpaces(true);
      return;
    }

    setAllSpaces(false);
    setActiveSpace(spaces.find((space) => space.id === value) ?? null);
  }

  return (
    <div
      className={cn(
        "flex min-h-screen flex-col bg-background",
        isChatRoute && "lg:h-[100dvh] lg:min-h-0 lg:overflow-hidden"
      )}
    >
      <header className="sticky top-0 z-40 shrink-0 border-b bg-background">
        <div className="container flex min-h-14 items-center justify-between gap-4 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Sparkles className="h-4 w-4" />
              </div>
              <div className="space-y-0.5">
                <p className="text-sm font-semibold">Ragdoll</p>
                <p className="text-xs text-muted-foreground">Web workspace foundations</p>
              </div>
            </div>
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon" className="lg:hidden">
                  <Menu className="h-5 w-5" />
                  <span className="sr-only">Open navigation</span>
                </Button>
              </SheetTrigger>
              {mobileOpen ? (
                <SheetContent side="left" className="w-[20rem]">
                  <SheetHeader>
                    <SheetTitle>Workspace navigation</SheetTitle>
                    <SheetDescription>
                      Move between retrieval, document, and account surfaces.
                    </SheetDescription>
                  </SheetHeader>
                  <div className="mt-6 space-y-6">
                    <ScopeSelect
                      activeSpaceId={activeSpace?.id ?? null}
                      allSpaces={allSpaces}
                      disabled={!isReady}
                      options={spaceOptions}
                      onValueChange={handleScopeChange}
                    />
                    <NavRail currentPath={pathname} isAdmin={isAdmin} onNavigate={() => setMobileOpen(false)} />
                  </div>
                </SheetContent>
              ) : null}
            </Sheet>
          </div>

          <div className="flex items-center justify-between gap-3 lg:justify-end">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-foreground">
                {currentUser?.full_name ?? currentUser?.email}
              </p>
              <p className="text-xs text-muted-foreground">{currentUser?.email}</p>
            </div>
            <Button variant="outline" onClick={logout}>
              Log out
            </Button>
          </div>
        </div>
      </header>

      <div
        className={cn(
          "container grid min-h-0 flex-1 gap-6 py-6 lg:grid-cols-[240px_minmax(0,1fr)] lg:py-8",
          isChatRoute && "lg:overflow-hidden"
        )}
      >
        <aside className="hidden lg:block">
          <div
            className={cn(
              "sticky rounded-lg border bg-card p-4 shadow-sm",
              isChatRoute ? "top-0" : "top-[6.5rem]"
            )}
          >
            <div className="mb-4">
              <ScopeSelect
                activeSpaceId={activeSpace?.id ?? null}
                allSpaces={allSpaces}
                disabled={!isReady}
                options={spaceOptions}
                onValueChange={handleScopeChange}
              />
            </div>
            <NavRail currentPath={pathname} isAdmin={isAdmin} />
          </div>
        </aside>

        <main
          className={cn(
            "flex min-h-0 min-w-0 flex-col",
            isChatRoute && "lg:overflow-hidden"
          )}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
