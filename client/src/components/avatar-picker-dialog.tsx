import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { DEFAULT_AVATARS } from "@/lib/defaultAvatars";
import { Check, Loader2 } from "lucide-react";

interface AvatarPickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentAvatarUrl?: string;
  onSelect: (avatarUrl: string) => void;
  isPending?: boolean;
}

export function AvatarPickerDialog({
  open,
  onOpenChange,
  currentAvatarUrl,
  onSelect,
  isPending,
}: AvatarPickerDialogProps) {
  const [selectedAvatar, setSelectedAvatar] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setSelectedAvatar(currentAvatarUrl || null);
    }
  }, [open, currentAvatarUrl]);

  const handleOpen = (isOpen: boolean) => {
    onOpenChange(isOpen);
  };

  const handleConfirm = () => {
    if (selectedAvatar) {
      onSelect(selectedAvatar);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogContent className="max-w-md sm:max-w-lg" data-testid="dialog-avatar-picker">
        <DialogHeader>
          <DialogTitle>Choose an Avatar</DialogTitle>
          <DialogDescription>
            Pick a default avatar for your profile picture.
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-4 gap-3 py-4 max-h-[360px] overflow-y-auto">
          {DEFAULT_AVATARS.map((avatar) => {
            const isSelected = selectedAvatar === avatar.url;
            return (
              <button
                key={avatar.id}
                type="button"
                onClick={() => setSelectedAvatar(avatar.url)}
                className={cn(
                  "relative flex flex-col items-center gap-1 p-2 rounded-lg transition-all",
                  "hover:bg-muted/60 focus:outline-none focus:ring-2 focus:ring-ring",
                  isSelected && "bg-primary/10 ring-2 ring-primary"
                )}
                data-testid={`avatar-option-${avatar.id}`}
                aria-label={avatar.label}
              >
                <div className="relative">
                  <img
                    src={avatar.url}
                    alt={avatar.label}
                    className="h-14 w-14 sm:h-16 sm:w-16 rounded-full"
                  />
                  {isSelected && (
                    <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                      <Check className="h-3 w-3 text-primary-foreground" />
                    </div>
                  )}
                </div>
                <span className="text-xs text-muted-foreground truncate w-full text-center">
                  {avatar.label}
                </span>
              </button>
            );
          })}
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            data-testid="button-cancel-avatar"
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={!selectedAvatar || isPending}
            data-testid="button-confirm-avatar"
          >
            {isPending ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...</>
            ) : (
              "Save Avatar"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
