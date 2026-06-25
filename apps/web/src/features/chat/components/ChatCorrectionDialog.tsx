import type { ChatMessageRecord } from "@contracts";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type ChatCorrectionDialogProps = {
  isSubmitting: boolean;
  message: ChatMessageRecord | null;
  onOpenChange: (open: boolean) => void;
  onProposedValueChange: (value: string) => void;
  onRationaleChange: (value: string) => void;
  onSubmit: (message: ChatMessageRecord) => void;
  proposedValue: string;
  rationale: string;
};

export function ChatCorrectionDialog({
  isSubmitting,
  message,
  onOpenChange,
  onProposedValueChange,
  onRationaleChange,
  onSubmit,
  proposedValue,
  rationale
}: ChatCorrectionDialogProps) {
  const canSubmit = Boolean(message && proposedValue.trim()) && !isSubmitting;

  return (
    <Dialog open={Boolean(message)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Submit correction</DialogTitle>
          <DialogDescription className="sr-only">
            Send a targeted correction for this assistant answer.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="proposed-correction">Proposed correction</Label>
            <Textarea
              id="proposed-correction"
              rows={4}
              value={proposedValue}
              onChange={(event) => onProposedValueChange(event.currentTarget.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="correction-rationale">Rationale</Label>
            <Textarea
              id="correction-rationale"
              rows={3}
              value={rationale}
              onChange={(event) => onRationaleChange(event.currentTarget.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            type="button"
            onClick={() => {
              if (message) {
                onSubmit(message);
              }
            }}
          >
            {isSubmitting ? "Submitting..." : "Submit for review"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
