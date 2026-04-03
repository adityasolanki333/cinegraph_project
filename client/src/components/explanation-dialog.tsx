import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { ExplanationLoader } from "./explanation-loader";
import { Brain } from "lucide-react";

import type { Movie } from "@shared/schema";
import { Star } from "lucide-react";

interface ExplanationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  movie: Movie; // Pass full movie object
  initialReason?: string;
}

export function ExplanationDialog({
  isOpen,
  onClose,
  movie,
  initialReason,
}: ExplanationDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            AI Recommendation Analysis
          </DialogTitle>
          <DialogDescription>
            Why we recommended this for you
          </DialogDescription>
        </DialogHeader>

        <div className="grid sm:grid-cols-[1fr,1.5fr] gap-6 py-4">
          {/* Movie Metadata Column */}
          <div className="hidden sm:block space-y-3">
            <div className="aspect-[2/3] rounded-lg overflow-hidden relative shadow-md">
              <img
                src={movie.posterUrl || "https://images.unsplash.com/photo-1489599558473-7636b88d6e6a?ixlib=rb-4.0.3&w=400&h=600&fit=crop"}
                alt={movie.title}
                className="w-full h-full object-cover"
              />
            </div>
            <div>
              <h3 className="font-bold text-lg leading-tight">{movie.title}</h3>
              <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                <span>{movie.year}</span>
                <span>•</span>
                <div className="flex items-center text-yellow-500">
                  <Star className="h-3 w-3 fill-current mr-1" />
                  <span className="font-medium">{movie.rating > 0 ? movie.rating : "NR"}</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2 line-clamp-4">
                {movie.synopsis}
              </p>
            </div>
          </div>

          {/* Mobile Metadata (Header style) */}
          <div className="flex sm:hidden gap-3 mb-2">
            <img
              src={movie.posterUrl || "https://images.unsplash.com/photo-1489599558473-7636b88d6e6a?ixlib=rb-4.0.3&w=400&h=600&fit=crop"}
              alt={movie.title}
              className="w-16 h-24 object-cover rounded shadow-sm"
            />

            <div>
              <h3 className="font-bold text-base">{movie.title}</h3>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{movie.year}</span>
                <div className="flex items-center text-yellow-500">
                  <Star className="h-3 w-3 fill-current mr-1" />
                  <span>{movie.rating > 0 ? movie.rating : "NR"}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="min-w-0">
            <ExplanationLoader
              movieId={movie.id}
              mediaType={movie.type}
              initialReason={initialReason}
            />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
