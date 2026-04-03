import { useState, useRef, useEffect } from "react";
import { useRoute, Link } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { usePageMeta } from "@/hooks/usePageMeta";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { ArrowLeft, MessageSquare, Pin, Send, CornerDownRight } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export default function DiscussionThread() {
    usePageMeta({
      title: "Discussion",
      description: "Join the conversation in this CineGraph community discussion.",
    });

    const [match, params] = useRoute("/community/clubs/threads/:id");
    const threadId = params?.id;
    const { user } = useAuth();
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [replyContent, setReplyContent] = useState("");
    const replyInputRef = useRef<HTMLTextAreaElement>(null);

    const { data: thread, isLoading } = useQuery({
        queryKey: ['/api/clubs/threads', threadId],
        enabled: !!threadId,
        queryFn: async () => {
            const res = await fetch(`/api/clubs/threads/${threadId}`);
            if (!res.ok) throw new Error("Failed to fetch thread");
            return res.json();
        }
    });

    const replyMutation = useMutation({
        mutationFn: async (data: { content: string }) => {
            const res = await fetch(`/api/clubs/threads/${threadId}/posts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.error || "Failed to post reply");
            }
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['/api/clubs/threads', threadId] });
            setReplyContent("");
            toast({
                title: "Reply posted",
                description: "Your reply has been added to the discussion.",
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

    const handleReply = (e: React.FormEvent) => {
        e.preventDefault();
        if (!replyContent.trim()) return;
        replyMutation.mutate({ content: replyContent });
    };

    if (isLoading) {
        return (
            <div className="container mx-auto px-4 py-8 max-w-4xl">
                <Skeleton className="h-4 w-24 mb-6" />
                <Card className="mb-6">
                    <CardHeader><Skeleton className="h-8 w-3/4" /></CardHeader>
                    <CardContent><Skeleton className="h-32 w-full" /></CardContent>
                </Card>
                <div className="space-y-4">
                    {[...Array(3)].map((_, i) => (
                        <Skeleton key={i} className="h-24 w-full rounded-lg" />
                    ))}
                </div>
            </div>
        );
    }

    if (!thread) return <div className="p-8 text-center">Thread not found</div>;

    return (
        <div className="container mx-auto px-4 py-8 max-w-4xl">
            <Button variant="ghost" className="mb-4 pl-0 hover:pl-2 transition-all" asChild>
                <Link href={`/community/clubs/${thread.club?.id}`}>
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to {thread.club?.title || "Club"}
                </Link>
            </Button>

            {/* Main Post (OP) */}
            <Card className="mb-8 border-primary/20 shadow-sm">
                <CardHeader className="pb-3">
                    <div className="flex justify-between items-start gap-4">
                        <div>
                            <CardTitle className="text-2xl sm:text-3xl font-bold flex items-center gap-2">
                                {thread.pinned && <Pin className="h-5 w-5 text-primary fill-primary rotate-45" />}
                                {thread.title}
                            </CardTitle>
                            <div className="flex items-center gap-3 mt-3 text-sm text-muted-foreground">
                                <div className="flex items-center gap-2">
                                    <Avatar className="h-6 w-6">
                                        <AvatarImage src={thread.author.avatar} />
                                        <AvatarFallback>{thread.author.username[0].toUpperCase()}</AvatarFallback>
                                    </Avatar>
                                    <span className="font-medium text-foreground">{thread.author.username}</span>
                                </div>
                                <span>•</span>
                                <span>{formatDistanceToNow(new Date(thread.created_at), { addSuffix: true })}</span>
                            </div>
                        </div>
                        <Badge variant="secondary" className="hidden sm:flex items-center gap-1">
                            <MessageSquare className="h-3 w-3" />
                            {thread.posts?.length || 0} replies
                        </Badge>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="prose dark:prose-invert max-w-none text-base leading-relaxed whitespace-pre-wrap">
                        {thread.content}
                    </div>
                </CardContent>
            </Card>

            {/* Replies */}
            <div className="space-y-6">
                <h3 className="text-xl font-semibold flex items-center gap-2">
                    Replies
                    <span className="text-muted-foreground font-normal text-base">({thread.posts?.length || 0})</span>
                </h3>

                {thread.posts?.length > 0 ? (
                    <div className="space-y-4">
                        {thread.posts.map((post: any) => (
                            <Card key={post.id} className="bg-muted/30">
                                <CardContent className="pt-6">
                                    <div className="flex gap-4">
                                        <Avatar className="h-10 w-10 border-2 border-background">
                                            <AvatarImage src={post.author.avatar} />
                                            <AvatarFallback>{post.author.username[0].toUpperCase()}</AvatarFallback>
                                        </Avatar>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="font-semibold text-sm">{post.author.username}</span>
                                                <span className="text-xs text-muted-foreground">{formatDistanceToNow(new Date(post.created_at), { addSuffix: true })}</span>
                                            </div>
                                            <p className="text-sm sm:text-base whitespace-pre-wrap leading-relaxed">
                                                {post.content}
                                            </p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8 text-muted-foreground italic">
                        No replies yet. Be the first to join the conversation!
                    </div>
                )}
            </div>

            {/* Reply Box */}
            {user ? (
                <div className="mt-8 sticky bottom-4">
                    <Card className="shadow-lg border-primary/20">
                        <CardContent className="pt-6">
                            <form onSubmit={handleReply} className="flex gap-4">
                                <Textarea
                                    ref={replyInputRef}
                                    value={replyContent}
                                    onChange={(e) => setReplyContent(e.target.value)}
                                    placeholder="Write a reply..."
                                    className="min-h-[60px] resize-none"
                                />
                                <Button
                                    type="submit"
                                    size="icon"
                                    disabled={replyMutation.isPending || !replyContent.trim()}
                                    className="h-auto w-12 shrink-0 aspect-square"
                                >
                                    <Send className="h-5 w-5" />
                                </Button>
                            </form>
                        </CardContent>
                    </Card>
                </div>
            ) : (
                <Card className="mt-8 bg-muted/50">
                    <CardContent className="py-6 text-center">
                        <p className="text-muted-foreground mb-4">Log in to join the discussion</p>
                        <Button asChild variant="outline">
                            <Link href="/login">Log In</Link>
                        </Button>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
