import { Link, Outlet, useLocation } from "react-router-dom";

import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const publicLinks = [
  { label: "Login", to: "/login" },
  { label: "Register", to: "/register" },
  { label: "Status", to: "/status" }
] as const;

export function PublicShell() {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b bg-background">
        <div className="container flex h-14 items-center justify-between gap-4">
          <div className="space-y-0.5">
            <p className="text-sm font-semibold text-foreground">Ragdoll</p>
            <p className="text-xs text-muted-foreground">Workspace foundations</p>
          </div>
          <nav className="flex items-center gap-2">
            {publicLinks.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  buttonVariants({
                    size: "sm",
                    variant: pathname === item.to ? "default" : "ghost"
                  })
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main>
        <div className="container py-8 md:py-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
