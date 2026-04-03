import { useState } from "react";
import { getAuthHeaders } from "@/lib/queryClient";
import { Link } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { usePageMeta } from "@/hooks/usePageMeta";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Search, Plus, Users, ArrowRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface Club {
    id: number;
    title: string;
    description: string;
    cover_image_url?: string;
    member_count: number;
    is_member: boolean;
    created_at: string;
}

export default function ClubsList() {
    usePageMeta({
      title: "Clubs",
      description: "Browse and join movie discussion clubs on CineGraph.",
    });

    const [searchQuery, setSearchQuery] = useState("");
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [newClubTitle, setNewClubTitle] = useState("");
    const [newClubDescription, setNewClubDescription] = useState("");
    const [newClubCover, setNewClubCover] = useState("");

    const { user } = useAuth();
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const { data: clubsResponse, isLoading } = useQuery({
        queryKey: ['/api/clubs', searchQuery],
        queryFn: async () => {
            const url = searchQuery
                ? `/api/clubs?q=${encodeURIComponent(searchQuery)}`
                : '/api/clubs';
            const res = await fetch(url);
            if (!res.ok) throw new Error("Failed to fetch clubs");
            return res.json();
        }
    });

    const createClubMutation = useMutation({
        mutationFn: async (data: { title: string; description: string; cover_image_url: string }) => {
            const res = await fetch('/api/clubs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
                body: JSON.stringify(data),
            });

            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.error || "Failed to create club");
            }

            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['/api/clubs'] });
            setIsCreateOpen(false);
            setNewClubTitle("");
            setNewClubDescription("");
            setNewClubCover("");
            toast({
                title: "Success",
                description: "Club created successfully!",
            });
        },
        onError: (error: Error) => {
            toast({
                title: "Error",
                description: error.message,
                variant: "destructive",
            });
        },
    });

    const handleCreateClub = (e: React.FormEvent) => {
        e.preventDefault();
        if (!newClubTitle.trim()) return;

        createClubMutation.mutate({
            title: newClubTitle,
            description: newClubDescription,
            cover_image_url: newClubCover
        });
    };

    const clubs = clubsResponse?.clubs || [];

    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
                <div>
                    <h1 className="text-3xl font-bold mb-2">Cine-Clubs</h1>
                    <p className="text-muted-foreground">Join communities of film lovers and discuss your favorite topics</p>
                </div>

                {user && (
                    <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                        <DialogTrigger asChild>
                            <Button>
                                <Plus className="h-4 w-4 mr-2" />
                                Create Club
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[500px]">
                            <DialogHeader>
                                <DialogTitle>Create a New Club</DialogTitle>
                                <DialogDescription>
                                    Start a community for a genre, director, franchise, or specific topic.
                                </DialogDescription>
                            </DialogHeader>
                            <form onSubmit={handleCreateClub} className="space-y-4 py-4">
                                <div className="space-y-2">
                                    <Label htmlFor="title">Club Name</Label>
                                    <Input
                                        id="title"
                                        placeholder="e.g. 80s Horror Fans"
                                        value={newClubTitle}
                                        onChange={(e) => setNewClubTitle(e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="description">Description (Optional)</Label>
                                    <Textarea
                                        id="description"
                                        placeholder="What is this club about?"
                                        value={newClubDescription}
                                        onChange={(e) => setNewClubDescription(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="cover">Cover Image URL (Optional)</Label>
                                    <Input
                                        id="cover"
                                        placeholder="https://example.com/image.jpg"
                                        value={newClubCover}
                                        onChange={(e) => setNewClubCover(e.target.value)}
                                    />
                                </div>
                                <DialogFooter>
                                    <Button type="submit" disabled={createClubMutation.isPending}>
                                        {createClubMutation.isPending ? "Creating..." : "Create Club"}
                                    </Button>
                                </DialogFooter>
                            </form>
                        </DialogContent>
                    </Dialog>
                )}
            </div>

            <div className="relative mb-6">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                    className="pl-10"
                    placeholder="Search clubs..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>

            {isLoading ? (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[...Array(6)].map((_, i) => (
                        <Card key={i} className="h-full">
                            <CardHeader>
                                <Skeleton className="h-6 w-3/4 mb-2" />
                                <Skeleton className="h-4 w-full" />
                            </CardHeader>
                            <CardContent>
                                <Skeleton className="h-32 w-full mb-4" />
                                <Skeleton className="h-4 w-1/4" />
                            </CardContent>
                        </Card>
                    ))}
                </div>
            ) : clubs.length > 0 ? (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {clubs.map((club: Club) => (
                        <Card key={club.id} className="h-full flex flex-col hover:shadow-md transition-shadow">
                            <div className="aspect-video w-full overflow-hidden rounded-t-lg bg-muted relative">
                                {club.cover_image_url ? (
                                    <img
                                        src={club.cover_image_url}
                                        alt={club.title}
                                        className="w-full h-full object-cover transition-transform hover:scale-105"
                                    />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center bg-secondary">
                                        <Users className="h-12 w-12 text-muted-foreground opacity-50" />
                                    </div>
                                )}
                                {club.is_member && (
                                    <div className="absolute top-2 right-2 bg-primary text-primary-foreground px-2 py-1 rounded-full text-xs font-medium">
                                        Member
                                    </div>
                                )}
                            </div>
                            <CardHeader>
                                <CardTitle className="line-clamp-1 text-xl">{club.title}</CardTitle>
                                <CardDescription className="flex items-center gap-1">
                                    <Users className="h-3 w-3" />
                                    {club.member_count} {club.member_count === 1 ? 'member' : 'members'}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1">
                                <p className="text-sm text-muted-foreground line-clamp-3">
                                    {club.description || "No description provided."}
                                </p>
                            </CardContent>
                            <CardFooter className="pt-0">
                                <Button asChild className="w-full group">
                                    <Link href={`/community/clubs/${club.id}`}>
                                        View Club
                                        <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                                    </Link>
                                </Button>
                            </CardFooter>
                        </Card>
                    ))}
                </div>
            ) : (
                <div className="text-center py-12">
                    <div className="bg-muted w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Users className="h-8 w-8 text-muted-foreground" />
                    </div>
                    <h3 className="text-lg font-semibold mb-2">No clubs found</h3>
                    <p className="text-muted-foreground max-w-sm mx-auto">
                        {searchQuery ? `No clubs match "${searchQuery}"` : "Get the community started by creating the first club!"}
                    </p>
                    {!searchQuery && user && (
                        <Button variant="outline" className="mt-4" onClick={() => setIsCreateOpen(true)}>
                            Create First Club
                        </Button>
                    )}
                </div>
            )}
        </div>
    );
}
