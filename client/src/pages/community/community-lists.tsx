import { useState } from "react";
import { getAuthHeaders } from "@/lib/queryClient";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation } from "wouter";
import { usePageMeta } from "@/hooks/usePageMeta";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  List,
  Search,
  BookOpen,
  Users,
  Globe,
  Lock,
  Trash2,
  Plus,
  Loader2,
  Film,
  Eye,
  EyeOff,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { CreateListDialog } from "@/components/create-list-dialog";

interface PublicList {
  id: number;
  title: string;
  description: string;
  followerCount: number;
  itemCount: number;
  createdAt: string;
  user: { id: string; firstName: string; lastName: string };
}

interface UserList {
  id: number;
  title: string;
  description: string;
  isPublic: boolean;
  itemCount: number;
  followerCount: number;
  createdAt: string;
}

// ── Community (public) tab ──────────────────────────────────────────────────
function CommunityTab() {
  const [searchQuery, setSearchQuery] = useState("");
  const [sort, setSort] = useState("popular");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  const handleSearch = (val: string) => {
    setSearchQuery(val);
    clearTimeout((window as any).__listSearchTimer);
    (window as any).__listSearchTimer = setTimeout(() => setDebouncedQuery(val), 350);
  };

  const { data, isLoading } = useQuery<{ lists: PublicList[]; total: number }>({
    queryKey: ["/api/community/lists/public", debouncedQuery, sort],
    queryFn: async () => {
      const params = new URLSearchParams({ sort, limit: "24" });
      if (debouncedQuery) params.set("q", debouncedQuery);
      const res = await fetch(`/api/community/lists/public?${params}`);
      if (!res.ok) throw new Error("Failed to load lists");
      return res.json();
    },
  });

  const lists = data?.lists ?? [];

  return (
    <>
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            data-testid="input-search-lists"
            placeholder="Search community lists…"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={sort} onValueChange={setSort}>
          <SelectTrigger className="w-40" data-testid="select-sort-lists">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="popular">Most Popular</SelectItem>
            <SelectItem value="newest">Newest</SelectItem>
            <SelectItem value="most_items">Most Items</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border p-5 space-y-3">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
              <div className="flex gap-2 pt-2">
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-6 w-16" />
              </div>
            </div>
          ))}
        </div>
      ) : lists.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-40" />
          <p className="text-lg font-medium mb-1">No lists found</p>
          <p className="text-sm">
            {debouncedQuery
              ? `No lists match "${debouncedQuery}"`
              : "Be the first to create a curated list!"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {lists.map((list) => (
            <Link key={list.id} href={`/lists/${list.id}`} data-testid={`card-list-${list.id}`}>
              <div className="group rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-card/80 transition-all duration-200 p-5 h-full flex flex-col cursor-pointer">
                <div className="flex items-start gap-3 mb-3">
                  <div className="rounded-lg bg-primary/10 p-2 mt-0.5 flex-shrink-0">
                    <List className="h-4 w-4 text-primary" />
                  </div>
                  <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-2 leading-tight">
                    {list.title}
                  </h3>
                </div>
                {list.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2 mb-4 flex-1">
                    {list.description}
                  </p>
                )}
                <div className="mt-auto flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <Avatar className="h-6 w-6">
                      <AvatarFallback className="text-xs bg-primary/20 text-primary">
                        {list.user.firstName?.[0] ?? "?"}
                      </AvatarFallback>
                    </Avatar>
                    <span className="text-xs text-muted-foreground">
                      {list.user.firstName} {list.user.lastName}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Badge variant="secondary" className="text-xs gap-1">
                      <BookOpen className="h-3 w-3" />
                      {list.itemCount}
                    </Badge>
                    <Badge variant="outline" className="text-xs gap-1">
                      <Users className="h-3 w-3" />
                      {list.followerCount}
                    </Badge>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground/60 mt-3">
                  {formatDistanceToNow(new Date(list.createdAt), { addSuffix: true })}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

// ── My Lists tab ────────────────────────────────────────────────────────────
function MyListsTab() {
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [, setLocation] = useLocation();
  const [deleteTarget, setDeleteTarget] = useState<UserList | null>(null);

  const { data: myLists = [], isLoading } = useQuery<UserList[]>({
    queryKey: ["/api/community/users", user?.id, "lists"],
    queryFn: async () => {
      const res = await fetch(`/api/community/users/${user!.id}/lists`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.lists || (Array.isArray(data) ? data : []);
    },
    enabled: !!user?.id,
  });

  const toggleVisibilityMutation = useMutation({
    mutationFn: async (list: UserList) => {
      const res = await fetch(`/api/community/lists/${list.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ title: list.title, description: list.description, isPublic: !list.isPublic }),
      });
      if (!res.ok) throw new Error("Failed to update list");
      return res.json();
    },
    onSuccess: (_, list) => {
      queryClient.invalidateQueries({ queryKey: ["/api/community/lists/public"] });
      queryClient.invalidateQueries({ queryKey: ["/api/community/users", user?.id, "lists"] });
      toast({
        title: list.isPublic ? "List set to private" : "List made public",
        description: list.isPublic
          ? "This list is now only visible to you."
          : "This list is now visible to the community.",
      });
    },
    onError: () => toast({ title: "Error", description: "Failed to update visibility.", variant: "destructive" }),
  });

  const deleteListMutation = useMutation({
    mutationFn: async (listId: number) => {
      const res = await fetch(`/api/community/lists/${listId}`, { method: "DELETE", headers: { ...getAuthHeaders() } });
      if (!res.ok) throw new Error("Failed to delete list");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/community/lists/public"] });
      queryClient.invalidateQueries({ queryKey: ["/api/community/users", user?.id, "lists"] });
      toast({ title: "List deleted", description: "Your list has been deleted." });
      setDeleteTarget(null);
    },
    onError: () => toast({ title: "Error", description: "Failed to delete list.", variant: "destructive" }),
  });

  if (!user) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <List className="h-12 w-12 mx-auto mb-4 opacity-40" />
        <p className="font-medium mb-1">Sign in to manage your lists</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="rounded-xl border p-4 flex items-center gap-4">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-5 w-16 ml-auto" />
            <Skeleton className="h-8 w-8" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center justify-between mb-5">
        <p className="text-sm text-muted-foreground">
          {myLists.length === 0 ? "You haven't created any lists yet." : `${myLists.length} list${myLists.length !== 1 ? "s" : ""}`}
        </p>
        <CreateListDialog />
      </div>

      {myLists.length === 0 ? (
        <div className="text-center py-16 border rounded-xl text-muted-foreground">
          <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-40" />
          <p className="font-medium mb-3">Create your first curated list</p>
          <CreateListDialog
            trigger={
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create List
              </Button>
            }
          />
        </div>
      ) : (
        <div className="space-y-2.5">
          {myLists.map((list) => (
            <div
              key={list.id}
              className="flex items-center gap-3 rounded-xl border bg-card p-4 hover:border-primary/30 transition-colors"
              data-testid={`my-list-row-${list.id}`}
            >
              {/* Visibility icon */}
              <div className="flex-shrink-0 text-muted-foreground">
                {list.isPublic ? <Globe className="h-4 w-4 text-primary" /> : <Lock className="h-4 w-4" />}
              </div>

              {/* Title + meta */}
              <div className="flex-1 min-w-0">
                <Link href={`/lists/${list.id}`}>
                  <span className="font-medium hover:text-primary transition-colors line-clamp-1 cursor-pointer">
                    {list.title}
                  </span>
                </Link>
                <div className="flex items-center gap-3 mt-0.5">
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Film className="h-3 w-3" />
                    {list.itemCount ?? 0} items
                  </span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Users className="h-3 w-3" />
                    {list.followerCount ?? 0} followers
                  </span>
                  <Badge variant={list.isPublic ? "secondary" : "outline"} className="text-[10px] h-4 px-1.5">
                    {list.isPublic ? "Public" : "Private"}
                  </Badge>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  title={list.isPublic ? "Make private" : "Make public"}
                  onClick={() => toggleVisibilityMutation.mutate(list)}
                  disabled={toggleVisibilityMutation.isPending}
                  data-testid={`button-toggle-visibility-${list.id}`}
                >
                  {toggleVisibilityMutation.isPending
                    ? <Loader2 className="h-4 w-4 animate-spin" />
                    : list.isPublic
                      ? <EyeOff className="h-4 w-4" />
                      : <Eye className="h-4 w-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  title="Delete list"
                  onClick={() => setDeleteTarget(list)}
                  data-testid={`button-delete-my-list-${list.id}`}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete confirmation */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{deleteTarget?.title}"?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The list and all its items will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="button-cancel-delete-list">Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteTarget && deleteListMutation.mutate(deleteTarget.id)}
              disabled={deleteListMutation.isPending}
              data-testid="button-confirm-delete-list"
            >
              {deleteListMutation.isPending ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Deleting…</>
              ) : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

// ── Page ────────────────────────────────────────────────────────────────────
export default function CommunityListsPage() {
  usePageMeta({
    title: "Community Lists",
    description: "Discover curated movie and TV show lists shared by the CineGraph community.",
  });

  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-7">
          <h1 className="text-3xl font-bold mb-1">Community Lists</h1>
          <p className="text-muted-foreground">
            Discover curated collections — or build your own and share them with the community.
          </p>
        </div>

        <Tabs defaultValue="community">
          <TabsList className="mb-6">
            <TabsTrigger value="community" data-testid="tab-community-lists">
              <Globe className="h-4 w-4 mr-2" />
              Community
            </TabsTrigger>
            {isAuthenticated && (
              <TabsTrigger value="mine" data-testid="tab-my-lists">
                <List className="h-4 w-4 mr-2" />
                My Lists
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="community">
            <CommunityTab />
          </TabsContent>

          {isAuthenticated && (
            <TabsContent value="mine">
              <MyListsTab />
            </TabsContent>
          )}
        </Tabs>
      </div>
    </div>
  );
}
