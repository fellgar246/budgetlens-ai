"use client";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { copy } from "@/lib/copy";

export function ExportDialog({
  open,
  scope,
  onClose,
  onConfirm,
}: {
  open: boolean;
  scope: string;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <Dialog
      open={open}
      title={copy.exportScopeTitle}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {copy.cancel}
          </Button>
          <Button onClick={onConfirm}>{copy.exportConfirm}</Button>
        </>
      }
    >
      <p className="text-sm text-secondary">{copy.exportScopeHint}</p>
      <p className="mt-3 text-sm text-primary">{scope}</p>
    </Dialog>
  );
}
