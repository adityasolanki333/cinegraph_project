import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useTranslation } from "react-i18next";

export function RecommendationComments({ recommendationId, currentUserId, reason }: { recommendationId: string; currentUserId?: string; reason?: string }) {
  const { t } = useTranslation();
  const [commentText, setCommentText] = useState("");
  const { toast } = useToast();

  const { data: comments = [], isLoading } = useQuery({
    queryKey: ['/api/users/recommendations/comments', recommendationId],
    queryFn: async () => {
      const response = await fetch(`/api/users/recommendations/${recommendationId}/comments`);
      if (!response.ok) return [];
      const data = await response.json();
      return Array.isArray(data) ? data : (data.comments || []);
    }
  });

  const addCommentMutation = useMutation({
    mutationFn: async (comment: string) => {
      if (!currentUserId) throw new Error("User not authenticated");
      return apiRequest('POST', `/api/users/${currentUserId}/recommendations/${recommendationId}/comments`, { comment });
    },
    onSuccess: () => {
      toast({ title: t('recommendations.commentAdded') });
      setCommentText("");
      queryClient.invalidateQueries({ queryKey: ['/api/users/recommendations/comments', recommendationId] });
      queryClient.invalidateQueries({ queryKey: ['/api/users/recommendations/for'] });
    }
  });

  return (
    <div className="mt-4 space-y-3 animate-in slide-in-from-top-2 duration-200">
      {reason && (
        <div className="bg-primary/5 border border-primary/20 rounded-md p-3 flex items-start gap-2">
          <span className="text-lg">💡</span>
          <div className="flex-1">
            <p className="text-xs font-semibold text-primary mb-1">{t('recommendations.whyRecommendation')}</p>
            <p className="text-sm">{reason}</p>
          </div>
        </div>
      )}
      {currentUserId && (
        <div className="flex gap-2">
          <input
            type="text"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder={t('recommendations.addCommentPlaceholder')}
            className="flex-1 px-3 py-2 text-sm border rounded-md bg-background text-foreground"
            data-testid={`input-comment-${recommendationId}`}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && commentText.trim()) {
                addCommentMutation.mutate(commentText.trim());
              }
            }}
          />
          <Button
            size="sm"
            onClick={() => commentText.trim() && addCommentMutation.mutate(commentText.trim())}
            disabled={!commentText.trim() || addCommentMutation.isPending}
            data-testid={`button-add-comment-${recommendationId}`}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      )}
      {isLoading ? (
        <p className="text-xs text-muted-foreground">{t('recommendations.loadingComments')}</p>
      ) : comments.length > 0 ? (
        <div className="space-y-2">
          {comments.map((comment: any) => (
            <div key={comment.id} className="bg-muted/50 rounded-md p-2 animate-in slide-in-from-left-1 duration-150" data-testid={`comment-${comment.id}`}>
              <p className="text-xs font-medium flex items-center gap-1">
                <span>👤</span>
                {comment.userFirstName && comment.userLastName
                  ? `${comment.userFirstName} ${comment.userLastName}`
                  : comment.userEmail || t('recommendations.anonymous')}
              </p>
              <p className="text-sm mt-1">{comment.comment}</p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
