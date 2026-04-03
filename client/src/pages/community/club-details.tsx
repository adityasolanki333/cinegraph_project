import { useState } from "react";
import { getAuthHeaders } from "@/lib/queryClient";
import { useRoute, Link } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { usePageMeta } from "@/hooks/usePageMeta";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { Users, MessageSquare, Plus, ArrowLeft, Pin, Calendar } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { formatDistanceToNow } from "date-fns";

export default function ClubDetails() {
    usePageMeta({
      title: "Club Details",
      description: "View club discussions and members on CineGraph.",
    });

    const [match, params] = useRoute("/community/clubs/:id");
    const clubId = params?.id;
    const { user } = useAuth();
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const [isCreateThreadOpen, setIsCreateThreadOpen] = useState(false);
    const [newThreadTitle, setNewThreadTitle] = useState("");
    const [newThreadContent, setNewThreadContent] = useState("");

    const { data: club, isLoading: clubLoading } = useQuery({
        queryKey: ['/api/clubs', clubId],
        enabled: !!clubId,
        queryFn: async () => {
            const res = await fetch(`/api/clubs/${clubId}`);
            if (!res.ok) throw new Error("Failed to fetch club details");
            return res.json();
        }
    });

    const { data: threadsResponse, isLoading: threadsLoading } = useQuery({
        queryKey: ['/api/clubs', clubId, 'threads'],
        enabled: !!clubId,
        queryFn: async () => {
            const res = await fetch(`/api/clubs/${clubId}/threads`);
            if (!res.ok) throw new Error("Failed to fetch threads");
            return res.json();
        }
    });

    const joinMutation = useMutation({
        mutationFn: async () => {
            const res = await fetch(`/api/clubs/${clubId}/join`, {
                method: 'POST',
                headers: {
                    ...getAuthHeaders(),
                },
            });
            if (!res.ok) throw new Error("Failed to join/leave club");
            return res.json();
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['/api/clubs', clubId] });
            toast({
                title: data.joined ? "Joined Club" : "Left Club",
                description: data.message,
            });
        }
    });

    const createThreadMutation = useMutation({
        mutationFn: async (data: { title: string; content: string }) => {
            const res = await fetch(`/api/clubs/${clubId}/threads`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
                body: JSON.stringify(data),
            });
            if (!res.ok) throw new Error("Failed to create thread");
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['/api/clubs', clubId, 'threads'] });
            setIsCreateThreadOpen(false);
            setNewThreadTitle("");
            setNewThreadContent("");
            toast({
                title: "Success",
                description: "Discussion thread started!",
            });
        },
        onError: (error: Error) => {
            toast({
                title: "Error",
                description: error.message,
                variant: "destructive",
            });
        }
    });

    const handleCreateThread = (e: React.FormEvent) => {
        e.preventDefault();
        if (!newThreadTitle.trim() || !newThreadContent.trim()) return;

        createThreadMutation.mutate({
            title: newThreadTitle,
            content: newThreadContent
        });
    };

    if (clubLoading) {
        return (
            <div className="container mx-auto px-4 py-8 max-w-7xl">
                <Skeleton className="h-8 w-1/4 mb-6" />
                <Skeleton className="h-64 w-full rounded-xl mb-8" />
                <div className="grid grid-cols-3 gap-8">
                    <div className="col-span-2 space-y-4">
                        <Skeleton className="h-12 w-full" />
                        <Skeleton className="h-32 w-full" />
                    </div>
                    <Skeleton className="h-64 w-full" />
                </div>
            </div>
        );
    }

    if (!club) return <div className="p-8 text-center">Club not found</div>;

    const threads = threadsResponse?.threads || [];

    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl">
            <Button variant="ghost" className="mb-4 pl-0 hover:pl-2 transition-all" asChild>
                <Link href="/community/clubs">
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Clubs
                </Link>
            </Button>

            {/* Header / Cover */}
            <div className="relative rounded-xl overflow-hidden mb-8 bg-muted group">
                <div className="absolute inset-0 bg-black/40 z-10 transition-opacity group-hover:bg-black/50" />
                {club.cover_image_url ? (
                    <img
                        src={club.cover_image_url}
                        alt={club.title}
                        className="w-full h-56 sm:h-72 object-contain"
                    />
                ) : (
                    <div className="w-full h-56 sm:h-72 bg-gradient-to-r from-primary/20 to-primary/10" />
                )}

                <div className="absolute bottom-0 left-0 right-0 p-6 z-20 text-white">
                    <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                        <div>
                            <h1 className="text-3xl sm:text-4xl font-bold mb-2">{club.title}</h1>
                            <div className="flex items-center gap-4 text-sm sm:text-base">
                                <span className="flex items-center gap-1">
                                    <Users className="h-4 w-4" />
                                    {club.member_count} members
                                </span>
                                <span>•</span>
                                <span>Created {new Date(club.created_at).toLocaleDateString()}</span>
                            </div>
                        </div>

                        {user && (
                            <Button
                                size="lg"
                                variant={club.is_member ? "outline" : "default"}
                                className={club.is_member ? "bg-white/10 hover:bg-white/20 text-white border-white/20" : ""}
                                onClick={() => joinMutation.mutate()}
                                disabled={joinMutation.isPending}
                            >
                                {club.is_member ? "Leave Club" : "Join Club"}
                            </Button>
                        )}
                    </div>
                </div>
            </div>

            <div className="grid lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2">
                    <Tabs defaultValue="discussions" className="w-full">
                        <TabsList className="mb-6 w-full sm:w-auto">
                            <TabsTrigger value="discussions">Discussions</TabsTrigger>
                            <TabsTrigger value="about">About</TabsTrigger>
                            <TabsTrigger value="members">Members</TabsTrigger>
                        </TabsList>

                        <TabsContent value="discussions" className="space-y-4">
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-xl font-semibold">Discussion Threads</h3>
                                {club.is_member && (
                                    <Dialog open={isCreateThreadOpen} onOpenChange={setIsCreateThreadOpen}>
                                        <DialogTrigger asChild>
                                            <Button size="sm">
                                                <Plus className="h-4 w-4 mr-2" />
                                                New Thread
                                            </Button>
                                        </DialogTrigger>
                                        <DialogContent>
                                            <DialogHeader>
                                                <DialogTitle>Start a Discussion</DialogTitle>
                                            </DialogHeader>
                                            <form onSubmit={handleCreateThread} className="space-y-4 py-4">
                                                <div className="space-y-2">
                                                    <Label htmlFor="thread-title">Title</Label>
                                                    <Input
                                                        id="thread-title"
                                                        placeholder="Topic title..."
                                                        value={newThreadTitle}
                                                        onChange={(e) => setNewThreadTitle(e.target.value)}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label htmlFor="thread-content">Content</Label>
                                                    <Textarea
                                                        id="thread-content"
                                                        placeholder="What's on your mind?"
                                                        className="min-h-[150px]"
                                                        value={newThreadContent}
                                                        onChange={(e) => setNewThreadContent(e.target.value)}
                                                    />
                                                </div>
                                                <DialogFooter>
                                                    <Button type="submit" disabled={createThreadMutation.isPending}>
                                                        Post Thread
                                                    </Button>
                                                </DialogFooter>
                                            </form>
                                        </DialogContent>
                                    </Dialog>
                                )}
                            </div>

                            {threadsLoading ? (
                                <div className="space-y-4">
                                    {[...Array(3)].map((_, i) => (
                                        <Card key={i}>
                                            <CardHeader><Skeleton className="h-6 w-3/4" /></CardHeader>
                                            <CardContent><Skeleton className="h-16 w-full" /></CardContent>
                                        </Card>
                                    ))}
                                </div>
                            ) : threads.length > 0 ? (
                                <div className="space-y-4">
                                    {threads.map((thread: any) => (
                                        <Link key={thread.id} href={`/community/clubs/threads/${thread.id}`}>
                                            <Card className="hover:shadow-md transition-all cursor-pointer group border-l-4 border-l-transparent hover:border-l-primary">
                                                <CardHeader className="pb-2">
                                                    <div className="flex justify-between items-start">
                                                        <div className="space-y-1">
                                                            <CardTitle className="text-lg flex items-center gap-2 group-hover:text-primary transition-colors">
                                                                {thread.pinned && <Pin className="h-4 w-4 text-primary fill-primary rotate-45" />}
                                                                {thread.title}
                                                            </CardTitle>
                                                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                                <span>Posted by {thread.author.username}</span>
                                                                <span>•</span>
                                                                <span>{formatDistanceToNow(new Date(thread.created_at), { addSuffix: true })}</span>
                                                            </div>
                                                        </div>
                                                        <Badge variant="secondary" className="flex items-center gap-1">
                                                            <MessageSquare className="h-3 w-3" />
                                                            {thread.post_count}
                                                        </Badge>
                                                    </div>
                                                </CardHeader>
                                            </Card>
                                        </Link>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-12 border rounded-lg bg-muted/20">
                                    <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                                    <h3 className="text-lg font-medium mb-1">No discussions yet</h3>
                                    <p className="text-muted-foreground mb-4">Be the first to start a conversation!</p>
                                    {club.is_member && (
                                        <Button onClick={() => setIsCreateThreadOpen(true)}>Start Discussion</Button>
                                    )}
                                </div>
                            )}
                        </TabsContent>

                        <TabsContent value="about">
                            <Card>
                                <CardHeader>
                                    <CardTitle>About this Club</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <p className="whitespace-pre-wrap leading-relaxed">
                                        {club.description || "No description provided."}
                                    </p>
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground pt-4 border-t">
                                        <Calendar className="h-4 w-4" />
                                        Created on {new Date(club.created_at).toLocaleDateString()}
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="members">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Club Members</CardTitle>
                                    <CardDescription>
                                        {club.member_count} member{club.member_count !== 1 ? 's' : ''}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                                        <div className="h-10 w-10 bg-primary/20 rounded-full flex items-center justify-center text-primary font-bold">
                                            {club.owner.username[0].toUpperCase()}
                                        </div>
                                        <div>
                                            <p className="font-medium">{club.owner.username}</p>
                                            <Badge variant="outline" className="text-xs">Owner</Badge>
                                        </div>
                                    </div>
                                    {/* Additional member list would ideally be fetched here */}
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </div>

                <div className="lg:col-span-1 space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">Stats</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex justify-between items-center">
                                <span className="text-muted-foreground">Members</span>
                                <span className="font-semibold">{club.member_count}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-muted-foreground">Discussions</span>
                                <span className="font-semibold">{threads.length}</span>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
