import React from 'react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Brain, TrendingUp, ThumbsUp, Activity, Target } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ExplanationFeature {
    feature_name: string;
    importance: number;
    percentage_contribution: number;
    human_readable: string;
}

export interface VisualBreakdownItem {
    feature_name: string;
    percentage: number;
    color: string;
}

export interface ExplanationData {
    primary_reason: string;
    contributing_factors: ExplanationFeature[];
    visual_breakdown: VisualBreakdownItem[];
    confidence_score: number;
    explanation_text: string;
    recommendation_id?: string;
    user_feedback?: 'liked' | 'disliked' | null;
}

interface ExplanationVisualizerProps {
    explanation: ExplanationData;
    className?: string;
    onFeedback?: (type: 'thumbs_up' | 'thumbs_down') => void;
}

export function ExplanationVisualizer({ explanation, className, onFeedback }: ExplanationVisualizerProps) {
    const {
        primary_reason,
        visual_breakdown,
        confidence_score,
        explanation_text,
        contributing_factors
    } = explanation;

    // Local state for optimistic UI updates
    const [feedback, setFeedback] = React.useState<'liked' | 'disliked' | null>(explanation.user_feedback || null);

    // Format confidence as percentage
    const confidencePercent = Math.round(confidence_score * 100);

    const handleVote = (type: 'thumbs_up' | 'thumbs_down') => {
        const newState = type === 'thumbs_up' ? 'liked' : 'disliked';
        if (feedback === newState) return;

        setFeedback(newState);
        if (onFeedback) {
            onFeedback(type);
        }
    };

    return (
        <div className={cn("space-y-4", className)}>
            {/* Header with Confidence */}
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h4 className="font-semibold text-lg flex items-center gap-2">
                        <Brain className="h-5 w-5 text-primary" />
                        AI Insight
                    </h4>
                    <p className="text-sm text-foreground/80 font-medium mt-1">
                        {primary_reason}
                    </p>
                </div>
                <div className="flex flex-col items-end">
                    <Badge
                        variant={confidencePercent > 80 ? "default" : "secondary"}
                        className="text-xs font-bold"
                    >
                        {confidencePercent}% Match Confidence
                    </Badge>
                </div>
            </div>

            {/* Visual Breakdown Bar */}
            <div className="space-y-2">
                <div className="h-4 w-full flex rounded-full overflow-hidden bg-muted">
                    {visual_breakdown.map((item, idx) => (
                        <div
                            key={idx}
                            style={{ width: `${item.percentage}%`, backgroundColor: item.color }}
                            className="h-full transition-all duration-500 hover:opacity-80"
                            title={`${item.feature_name}: ${Math.round(item.percentage)}%`}
                        />
                    ))}
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-foreground">
                    {visual_breakdown.map((item, idx) => (
                        <div key={idx} className="flex items-center gap-1.5">
                            <div
                                className="w-2.5 h-2.5 rounded-full"
                                style={{ backgroundColor: item.color }}
                            />
                            <span>{item.feature_name}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Detailed Factors List */}
            <div className="grid gap-3 pt-2">
                <h5 className="text-sm font-semibold flex items-center gap-2">
                    <Activity className="h-4 w-4" />
                    Key Factors
                </h5>
                <div className="space-y-3">
                    {contributing_factors.slice(0, 3).map((factor, idx) => (
                        <div key={idx} className="flex items-center gap-3 text-sm">
                            <div className="bg-primary/10 p-2 rounded-full text-primary shrink-0">
                                {idx === 0 ? <Target className="h-4 w-4" /> :
                                    idx === 1 ? <TrendingUp className="h-4 w-4" /> :
                                        <ThumbsUp className="h-4 w-4" />}
                            </div>
                            <div className="flex-1">
                                <p className="font-medium text-foreground">{factor.human_readable}</p>
                                <div className="flex items-center gap-2 mt-1">
                                    <Progress value={factor.percentage_contribution} className="h-1.5" />
                                    <span className="text-xs text-muted-foreground w-8 text-right">
                                        {Math.round(factor.percentage_contribution)}%
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Full Text Explanation */}
            <div className="bg-muted/30 p-3 rounded-lg text-sm italic text-muted-foreground border border-border/50">
                "{explanation_text}"
            </div>

            {/* Feedback Section */}
            <div className="border-t pt-3 flex items-center justify-between">
                <span className="text-xs text-muted-foreground font-medium">Was this comparison helpful?</span>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => handleVote('thumbs_up')}
                        className={cn(
                            "p-1.5 rounded-full transition-colors hover:bg-muted",
                            feedback === 'liked' ? "text-green-500 bg-green-500/10" : "text-muted-foreground hover:text-green-500"
                        )}
                        title="Yes, this was helpful"
                    >
                        <ThumbsUp className="h-4 w-4" />
                    </button>
                    <button
                        onClick={() => handleVote('thumbs_down')}
                        className={cn(
                            "p-1.5 rounded-full transition-colors hover:bg-muted",
                            feedback === 'disliked' ? "text-red-500 bg-red-500/10" : "text-muted-foreground hover:text-red-500"
                        )}
                        title="No, not helpful"
                    >
                        <ThumbsUp className="h-4 w-4 rotate-180" />
                    </button>
                </div>
            </div>
        </div>
    );
}
