import { Link } from "react-router-dom";

import { Page, PageHeader } from "@/components/app/page";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function HomePage() {
  return (
    <Page>
      <Card className="overflow-hidden">
        <CardContent className="grid gap-8 p-8 lg:grid-cols-[minmax(0,1fr)_340px] lg:p-10">
          <PageHeader
            eyebrow="Workspace"
            title="Ragdoll Workspace"
            description="The clean-room rebuild now has a live web workspace for auth, Spaces, document upload, processing, and account usage on top of the typed API contracts."
          />
          <div className="flex flex-col justify-between gap-5 rounded-lg border bg-muted/30 p-6">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Ready to explore
              </p>
              <p className="text-sm leading-6 text-foreground">
                Sign in to open the scoped workspace shell, or create an account to begin with a fresh Space.
              </p>
            </div>
            <div className="flex flex-col gap-3">
              <Button asChild>
                <Link to="/login">Sign in</Link>
              </Button>
              <Button asChild variant="outline">
                <Link to="/register">Create account</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </Page>
  );
}
