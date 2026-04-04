import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Plus, Loader2, Globe, Lock } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";

interface CreateListDialogProps {
  onSuccess?: (listId: string) => void;
  trigger?: React.ReactNode;
}

export function CreateListDialog({ onSuccess, trigger }: CreateListDialogProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const { user, isAuthenticated } = useAuth();
  const { toast } = useToast();

  const createListMutation = useMutation({
    mutationFn: async () => {
      if (!isAuthenticated || !user?.id) throw new Error("Must be logged in to create a list");
      const response = await apiRequest("POST", `/api/users/${user.id}/lists/create`, {
        title: title.trim(),
        description: description.trim(),
        isPublic,
      });
      return response.json() as Promise<{ id: string }>;
    },
    onSuccess: (data) => {
      // Invalidate both community public feed AND user's own list cache
      queryClient.invalidateQueries({ queryKey: ["/api/community/lists/public"] });
      if (user?.id) {
        queryClient.invalidateQueries({ queryKey: ["/api/community/users", user.id, "lists"] });
      }
      toast({ title: "List created", description: "Your list has been created." });
      setTitle("");
      setDescription("");
      setIsPublic(true);
      setOpen(false);
      if (onSuccess && data.id) onSuccess(data.id);
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error?.message || "Failed to create list. Please try again.",
        variant: "destructive",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      toast({ title: "Title required", description: "Please enter a title for your list.", variant: "destructive" });
      return;
    }
    createListMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button data-testid="button-create-list">
            <Plus className="h-4 w-4 mr-2" />
            Create List
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[480px]" data-testid="dialog-create-list">
        <DialogHeader>
          <DialogTitle>Create New List</DialogTitle>
          <DialogDescription>
            Create a curated collection of movies and TV shows.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <div className="space-y-1.5">
            <Label htmlFor="list-title">Title</Label>
            <Input
              id="list-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="My Favourite Action Movies"
              maxLength={100}
              disabled={createListMutation.isPending}
              data-testid="input-list-title"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="list-desc">Description <span className="text-muted-foreground">(optional)</span></Label>
            <Textarea
              id="list-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A collection of must-watch films..."
              rows={3}
              maxLength={500}
              disabled={createListMutation.isPending}
              data-testid="textarea-list-description"
            />
          </div>

          {/* Public / Private toggle */}
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="flex items-center gap-3">
              {isPublic
                ? <Globe className="h-5 w-5 text-primary" />
                : <Lock className="h-5 w-5 text-muted-foreground" />}
              <div>
                <p className="text-sm font-medium">{isPublic ? "Public" : "Private"}</p>
                <p className="text-xs text-muted-foreground">
                  {isPublic ? "Anyone can find and follow this list" : "Only you can see this list"}
                </p>
              </div>
            </div>
            <Switch
              id="list-public"
              checked={isPublic}
              onCheckedChange={setIsPublic}
              disabled={createListMutation.isPending}
              data-testid="switch-list-public"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={createListMutation.isPending}
              data-testid="button-cancel-create-list"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!title.trim() || createListMutation.isPending}
              data-testid="button-submit-create-list"
            >
              {createListMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating…
                </>
              ) : "Create List"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
