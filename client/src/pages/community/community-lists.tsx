import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { List, Search, BookOpen, Users } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface PublicList {
  id: number;
  title: string;
  description: string;
  followerCount: number;
  itemCount: number;
  createdAt: string;
  user: {
    id: string;
    firstName: string;
    lastName: string;
  };
}

export default function CommunityListsPage() {
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
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Community Lists</h1>
          <p className="text-muted-foreground">
            Discover curated movie and TV collections created by the CineGraph community
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 mb-8">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              data-testid="input-search-lists"
              placeholder="Search lists..."
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
              <Link
                key={list.id}
                href={`/lists/${list.id}`}
                data-testid={`card-list-${list.id}`}
              >
                <div className="group rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-card/80 transition-all duration-200 p-5 h-full flex flex-col cursor-pointer">
                  <div className="flex items-start gap-3 mb-3">
                    <div className="rounded-lg bg-primary/10 p-2 mt-0.5 flex-shrink-0">
                      <List className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-2 leading-tight">
                        {list.title}
                      </h3>
                    </div>
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
      </div>
    </div>
  );
}
