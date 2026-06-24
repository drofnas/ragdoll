import { Badge } from "@/components/ui/badge";
import { humanizeLabel } from "@/shared/lib/formatting";

const STATUS_STYLES: Record<string, string> = {
  active: "border-transparent bg-primary/10 text-primary",
  completed: "border-transparent bg-primary/10 text-primary",
  degraded: "border-amber-200 bg-amber-50 text-amber-700",
  failed: "border-transparent bg-destructive/10 text-destructive",
  healthy: "border-transparent bg-primary/10 text-primary",
  inactive: "border-border text-muted-foreground",
  missing: "border-transparent bg-destructive/10 text-destructive",
  ok: "border-transparent bg-primary/10 text-primary",
  pending: "border-amber-200 bg-amber-50 text-amber-700",
  present: "border-transparent bg-primary/10 text-primary",
  processing: "border-sky-200 bg-sky-50 text-sky-700",
  read: "border-border text-muted-foreground",
  rejected: "border-transparent bg-destructive/10 text-destructive",
  unknown: "border-amber-200 bg-amber-50 text-amber-700",
  unread: "border-transparent bg-primary/10 text-primary",
  verified: "border-transparent bg-primary/10 text-primary"
};

export function StatusBadge({
  label,
  value
}: {
  label?: string;
  value: string | null | undefined;
}) {
  const normalized = (value ?? "unknown").toLowerCase();

  return (
    <Badge
      variant="outline"
      className={STATUS_STYLES[normalized] ?? "border-border text-foreground"}
    >
      {label ?? humanizeLabel(normalized)}
    </Badge>
  );
}
