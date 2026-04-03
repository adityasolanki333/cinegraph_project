import React from 'react';
import { getCsrfToken } from '@/lib/queryClient';
import { useQuery } from '@tanstack/react-query';
import { ExplanationVisualizer } from './explanation-visualizer';
import { useAuth } from '@/hooks/useAuth';

export function ExplanationLoader({ movieId, mediaType, initialReason }: { movieId: number | string, mediaType: string, initialReason?: string }) {
    const { user } = useAuth();
    const userId = user?.id || 'demo_user';

    const { data: explanation, isLoading } = useQuery({
        queryKey: ['explanation', userId, movieId],
        queryFn: async () => {
            const res = await fetch(`/api/recommendations/explain/${userId}/${movieId}?media_type=${mediaType}`);
            if (!res.ok) throw new Error('Failed to load explanation');
            return await res.json();
        }
    });

    if (isLoading) return <div className="text-xs text-muted-foreground animate-pulse p-2">Analyzing AI insights...</div>;

    if (!explanation) return <div className="text-xs text-muted-foreground p-2">{initialReason || "No insight available."}</div>;

    const handleFeedback = async (type: 'thumbs_up' | 'thumbs_down') => {
        if (!explanation?.recommendation_id) return;

        try {
            await fetch('/api/ml/recommendations/interaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                credentials: 'include',
                body: JSON.stringify({
                    recommendation_id: explanation.recommendation_id,
                    interaction_type: type,
                    tmdbId: movieId, // Fallback if rec_id missing or for logging
                    mediaType: mediaType,
                    user_id: userId
                })
            });
        } catch (e) {
            console.error("Feedback failed", e);
        }
    };

    return <ExplanationVisualizer explanation={explanation} className="text-xs p-2" onFeedback={handleFeedback} />;
}
