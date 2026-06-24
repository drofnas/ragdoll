import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Page({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("space-y-6", className)} {...props} />;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  children
}: {
  actions?: ReactNode;
  children?: ReactNode;
  description?: ReactNode;
  eyebrow?: string;
  title: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div className="space-y-2">
        {eyebrow ? (
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {eyebrow}
          </p>
        ) : null}
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            {title}
          </h1>
          {description ? (
            <div className="max-w-2xl text-sm text-muted-foreground sm:text-base">
              {description}
            </div>
          ) : null}
        </div>
        {children}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function FieldGroup({
  className,
  label,
  description,
  children
}: {
  children: ReactNode;
  className?: string;
  description?: ReactNode;
  label: ReactNode;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      <label className="text-sm font-medium text-foreground">{label}</label>
      {children}
      {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
    </div>
  );
}
