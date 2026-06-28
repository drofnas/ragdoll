import { Shield } from "lucide-react";
import { Link, Outlet, useLocation } from "react-router-dom";

import { StatusBadge } from "@/components/app/status-badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuthSession } from "@/shared/state/authSession";

const adminLinks = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Admin", to: "/admin" }
] as const;

export function AdminShell() {
  const { logout } = useAuthSession();
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b bg-background">
        <div className="container flex h-14 items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Shield className="h-5 w-5" />
            </div>
            <div className="space-y-0.5">
              <p className="text-sm font-semibold">Ragdoll</p>
              <p className="text-xs text-muted-foreground">Operator admin surface</p>
            </div>
          </div>
          <nav className="hidden items-center gap-2 sm:flex">
            {adminLinks.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "inline-flex h-9 items-center justify-center rounded-md px-4 text-sm font-medium transition-colors",
                  pathname === item.to
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                {item.label}
              </Link>
            ))}
            <StatusBadge label="Admin" value="active" />
            <Button variant="outline" onClick={logout}>
              Log out
            </Button>
          </nav>
        </div>
      </header>
      <main className="container py-8 md:py-10">
        <Outlet />
      </main>
    </div>
  );
}
