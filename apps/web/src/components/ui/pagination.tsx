import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function buildPages(currentPage: number, totalPages: number) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const pages = new Set<number>([1, totalPages, currentPage - 1, currentPage, currentPage + 1]);
  return Array.from(pages)
    .filter((page) => page >= 1 && page <= totalPages)
    .sort((a, b) => a - b);
}

interface PaginationProps {
  className?: string;
  currentPage: number;
  onPageChange: (page: number) => void;
  totalPages: number;
}

export function Pagination({ className, currentPage, onPageChange, totalPages }: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  const pages = buildPages(currentPage, totalPages);

  return (
    <nav
      className={cn("flex items-center justify-center gap-2", className)}
      aria-label="Pagination"
    >
      <Button
        type="button"
        size="icon"
        variant="outline"
        aria-label="Go to previous page"
        disabled={currentPage <= 1}
        onClick={() => onPageChange(currentPage - 1)}
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
      {pages.map((page, index) => {
        const previous = pages[index - 1];
        const showGap = previous !== undefined && page - previous > 1;

        return (
          <span key={page} className="flex items-center gap-2">
            {showGap ? (
              <span className="inline-flex h-10 w-10 items-center justify-center text-muted-foreground">
                <MoreHorizontal className="h-4 w-4" />
              </span>
            ) : null}
            <Button
              type="button"
              variant={page === currentPage ? "default" : "outline"}
              size="icon"
              aria-current={page === currentPage ? "page" : undefined}
              onClick={() => onPageChange(page)}
            >
              {page}
            </Button>
          </span>
        );
      })}
      <Button
        type="button"
        size="icon"
        variant="outline"
        aria-label="Go to next page"
        disabled={currentPage >= totalPages}
        onClick={() => onPageChange(currentPage + 1)}
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    </nav>
  );
}
