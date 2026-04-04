import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, Sparkles, ArrowDown, Star, X, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";
import { Link } from "wouter";

const TMDB_GENRE_MAP: Record<number, string> = {
  28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime',
  99: 'Documentary', 18: 'Drama', 10751: 'Family', 14: 'Fantasy', 36: 'History',
  27: 'Horror', 10402: 'Music', 9648: 'Mystery', 10749: 'Romance',
  878: 'Sci-Fi', 10770: 'TV Movie', 53: 'Thriller', 10752: 'War', 37: 'Western',
  10759: 'Action & Adventure', 10762: 'Kids', 10763: 'News', 10764: 'Reality',
  10765: 'Sci-Fi & Fantasy', 10766: 'Soap', 10767: 'Talk', 10768: 'War & Politics',
};

interface ChatMessage {
  id: string;
  type: "user" | "ai";
  content: string;
  recommendations?: Array<{ title: string; rating: number; reason: string }>;
  movies?: any[];
  queryInsights?: {
    detectedMood?: string;
    detectedGenres: string[];
    detectedKeywords: string[];
    yearPreference?: number;
    decadePreference?: string;
  };
  suggestions?: string[];
  source?: string;
  timestamp: Date;
  isStreaming?: boolean;
  statusMessage?: string;
  moviesLoading?: number;
  moviesDone?: boolean;
}

interface AIChatProps {
  className?: string;
  isOpen?: boolean;
  onToggle?: () => void;
}

const quickSuggestions = [
  { label: "😂 Something Funny", query: "I want something funny to laugh at" },
  { label: "🔥 Exciting Action", query: "show me thrilling action movies" },
  { label: "💕 Romantic Tonight", query: "romantic movies for date night" },
  { label: "😱 Scary Films", query: "I'm in the mood for something scary" },
  { label: "🆕 What's New", query: "what movies are in theaters right now?" },
  { label: "😊 Feel-Good Movies", query: "uplifting feel-good movies" },
  { label: "🤯 Mind-Bending", query: "thought-provoking intellectual films" },
  { label: "💎 Hidden Gems", query: "underrated movies I should watch" },
];

import { getAuthHeaders } from "@/lib/queryClient";

const typingMessages = [
  "Thinking...",
  "Analyzing your request...",
  "Searching for movies...",
  "Browsing the catalog...",
  "Finding the best picks...",
  "Almost there...",
];

function TypingIndicator() {
  const [messageIndex, setMessageIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState("");
  const [charIndex, setCharIndex] = useState(0);

  const currentMessage = typingMessages[messageIndex];

  useEffect(() => {
    if (charIndex < currentMessage.length) {
      const timer = setTimeout(() => {
        setDisplayedText(currentMessage.slice(0, charIndex + 1));
        setCharIndex(charIndex + 1);
      }, 40);
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        setMessageIndex((messageIndex + 1) % typingMessages.length);
        setCharIndex(0);
        setDisplayedText("");
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [charIndex, currentMessage, messageIndex]);

  return (
    <div className="flex items-center space-x-2 text-sm text-muted-foreground" data-testid="typing-indicator">
      <Sparkles className="h-3.5 w-3.5 text-accent animate-pulse flex-shrink-0" />
      <span>{displayedText}</span>
      <span className="inline-block w-0.5 h-4 bg-accent animate-[blink_1s_steps(2)_infinite]" />
    </div>
  );
}

export default function AIChat({ className, isOpen: controlledOpen, onToggle }: AIChatProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const stableToggle = useCallback(() => setInternalOpen(prev => !prev), []);
  const toggleOpen = onToggle || stableToggle;
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const saved = sessionStorage.getItem('aiChat_messages');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
          isStreaming: false,
        }));
      } catch {
      }
    }
    return [
      {
        id: "1",
        type: "ai",
        content: "👋 Hi! I'm your MovieVanders AI assistant! 🎬✨ I know what's currently in theaters, trending this week, and coming soon. Ask me things like 'what's new in theaters?', 'something scary to watch', or 'movies similar to Inception'. I remember our conversation, so feel free to follow up! 🍿",
        timestamp: new Date(),
      },
    ];
  });
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [fabPos, setFabPos] = useState<{ x: number; y: number }>(() => {
    const saved = localStorage.getItem('aiChat_fabPos');
    if (saved) {
      try { return JSON.parse(saved); } catch {}
    }
    return { x: -1, y: -1 };
  });
  const fabRef = useRef<HTMLButtonElement>(null);
  const wasDragged = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, posX: 0, posY: 0 });

  const clampPos = useCallback((x: number, y: number) => {
    const size = 56;
    const pad = 4;
    return {
      x: Math.max(pad, Math.min(x, window.innerWidth - size - pad)),
      y: Math.max(pad, Math.min(y, window.innerHeight - size - pad)),
    };
  }, []);

  useEffect(() => {
    if (fabPos.x === -1 && fabPos.y === -1) {
      setFabPos({ x: window.innerWidth - 56 - 16, y: window.innerHeight - 56 - 80 });
    }
  }, [fabPos]);

  useEffect(() => {
    if (fabPos.x >= 0 && fabPos.y >= 0) {
      localStorage.setItem('aiChat_fabPos', JSON.stringify(fabPos));
    }
  }, [fabPos]);

  useEffect(() => {
    const onResize = () => setFabPos(prev => prev.x < 0 ? prev : clampPos(prev.x, prev.y));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [clampPos]);

  const handleFabClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (wasDragged.current) {
      wasDragged.current = false;
      return;
    }
    toggleOpen();
  }, [toggleOpen]);

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    wasDragged.current = false;
    dragStart.current = { x: e.clientX, y: e.clientY, posX: fabPos.x, posY: fabPos.y };
  }, [fabPos]);

  const onPointerMove = useCallback((e: React.PointerEvent<HTMLButtonElement>) => {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) wasDragged.current = true;
    if (wasDragged.current) setFabPos(clampPos(dragStart.current.posX + dx, dragStart.current.posY + dy));
  }, [clampPos]);

  const onPointerUp = useCallback((e: React.PointerEvent<HTMLButtonElement>) => {
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
    if (wasDragged.current) {
      const size = 56;
      setFabPos(prev => {
        const snappedX = (prev.x + size / 2) < window.innerWidth / 2 ? 4 : window.innerWidth - size - 4;
        return clampPos(snappedX, prev.y);
      });
    }
  }, [clampPos]);

  useEffect(() => {
    const toSave = messages.map(m => ({
      ...m,
      isStreaming: false,
      statusMessage: undefined,
      moviesLoading: undefined,
      moviesDone: true,
    }));
    sessionStorage.setItem('aiChat_messages', JSON.stringify(toSave));
  }, [messages]);

  const scrollToBottom = useCallback((smooth = false) => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight,
          behavior: smooth ? 'smooth' : 'auto'
        });
      }
    }
  }, []);

  const handleScroll = useCallback(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
        const isNearBottom = scrollHeight - scrollTop - clientHeight < 150;
        setShowScrollButton(!isNearBottom && scrollHeight > clientHeight);
      }
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    const scrollContainer = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (scrollContainer) {
      scrollContainer.addEventListener('scroll', handleScroll);
      handleScroll();
      return () => scrollContainer.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  useEffect(() => {
    if (messages.length > 1) {
      const scrollContainer = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
        const wasNearBottom = scrollHeight - scrollTop - clientHeight < 150;
        if (wasNearBottom) {
          setTimeout(() => scrollToBottom(), 100);
        }
      }
    }
  }, [messages.length, scrollToBottom]);

  const getConversationHistory = useCallback(() => {
    return messages
      .filter(m => m.type === 'user' || (m.type === 'ai' && m.id !== '1'))
      .slice(-6)
      .map(m => ({
        type: m.type,
        content: m.content,
      }));
  }, [messages]);

  const handleStreamingResponse = useCallback(async (userInput: string) => {
    const history = getConversationHistory();
    const streamingMsgId = Date.now().toString();
    let streamingReceivedContent = false;

    setMessages(prev => [...prev, {
      id: streamingMsgId,
      type: "ai",
      content: "",
      movies: [],
      timestamp: new Date(),
      isStreaming: true,
    }]);

    try {
      const response = await fetch('/api/ai/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },

        body: JSON.stringify({
          message: userInput,
          userId: user?.id ? String(user.id) : undefined,
          history,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const contentType = response.headers.get('content-type') || '';

      if (contentType.includes('text/event-stream')) {
        const reader = response.body?.getReader();
        if (!reader) throw new Error('No reader');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.slice(6));

                if (event.type === 'status') {
                  setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                      ? { ...m, statusMessage: event.message }
                      : m
                  ));
                } else if (event.type === 'chunk') {
                  streamingReceivedContent = true;
                  setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                      ? { ...m, content: m.content + event.content, statusMessage: undefined }
                      : m
                  ));
                  scrollToBottom();
                } else if (event.type === 'movies_loading') {
                  setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                      ? { ...m, moviesLoading: event.count, moviesDone: false, movies: [] }
                      : m
                  ));
                  scrollToBottom();
                } else if (event.type === 'movie') {
                  streamingReceivedContent = true;
                  setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                      ? { ...m, movies: [...(m.movies || []), event.movie] }
                      : m
                  ));
                  scrollToBottom();
                } else if (event.type === 'done') {
                  streamingReceivedContent = true;
                  setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                      ? {
                          ...m,
                          movies: event.movies || m.movies || [],
                          isStreaming: false,
                          moviesDone: true,
                          moviesLoading: undefined,
                        }
                      : m
                  ));
                } else if (event.type === 'fallback') {
                  streamingReceivedContent = true;
                  setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                      ? {
                          ...m,
                          content: event.response || m.content,
                          movies: event.movies || m.movies || [],
                          source: 'fallback',
                          isStreaming: false,
                          moviesDone: true,
                        }
                      : m
                  ));
                } else if (event.type === 'error') {
                  setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                      ? {
                          ...m,
                          content: event.message || 'Something went wrong. Please try again.',
                          isStreaming: false,
                          moviesDone: true,
                          moviesLoading: undefined,
                          statusMessage: undefined,
                        }
                      : m
                  ));
                }
              } catch {
              }
            }
          }
        }

        setMessages(prev => prev.map(m =>
          m.id === streamingMsgId
            ? {
                ...m,
                isStreaming: false,
                moviesDone: true,
                moviesLoading: undefined,
                statusMessage: undefined,
              }
            : m
        ));

      } else {
        const data = await response.json();

        if (data.type === 'fallback') {
          setMessages(prev => prev.map(m =>
            m.id === streamingMsgId
              ? {
                  ...m,
                  content: data.response,
                  movies: data.movies || [],
                  source: 'fallback',
                  isStreaming: false,
                  moviesDone: true,
                }
              : m
          ));
        } else {
          setMessages(prev => prev.map(m =>
            m.id === streamingMsgId
              ? {
                  ...m,
                  content: data.response || data.error || 'No response received.',
                  movies: data.movies || [],
                  isStreaming: false,
                  moviesDone: true,
                }
              : m
          ));
        }
      }

    } catch (error) {
      if (!streamingReceivedContent) {
        await handleFallbackResponse(userInput, streamingMsgId);
      } else {
        setMessages(prev => prev.map(m =>
          m.id === streamingMsgId
            ? {
                ...m,
                isStreaming: false,
                moviesDone: true,
                moviesLoading: undefined,
                statusMessage: undefined,
              }
            : m
        ));
      }
    }
  }, [user, getConversationHistory, scrollToBottom]);

  const handleFallbackResponse = useCallback(async (userInput: string, existingMsgId?: string) => {
    const history = getConversationHistory();

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },

        body: JSON.stringify({
          message: userInput,
          userId: user?.id ? String(user.id) : undefined,
          history,
        }),
      });

      const data = await response.json();

      if (existingMsgId) {
        setMessages(prev => prev.map(m =>
          m.id === existingMsgId
            ? {
                ...m,
                content: data.response || data.error || "I'd love to help! Tell me what kind of movies you're in the mood for.",
                movies: data.movies || [],
                source: data.source,
                isStreaming: false,
                moviesDone: true,
                moviesLoading: undefined,
                statusMessage: undefined,
              }
            : m
        ));
      } else {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          type: "ai",
          content: data.response || data.error || "I'd love to help! Tell me what kind of movies you're in the mood for.",
          movies: data.movies || [],
          source: data.source,
          timestamp: new Date(),
          moviesDone: true,
        }]);
      }
    } catch {
      const fallbackContent = "I'm having trouble connecting right now. Please try asking again in a moment!";
      if (existingMsgId) {
        setMessages(prev => prev.map(m =>
          m.id === existingMsgId
            ? {
                ...m,
                content: fallbackContent,
                isStreaming: false,
                moviesDone: true,
                moviesLoading: undefined,
                statusMessage: undefined,
              }
            : m
        ));
      } else {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          type: "ai",
          content: fallbackContent,
          timestamp: new Date(),
        }]);
      }
    }
  }, [user, getConversationHistory]);

  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: "user",
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = inputValue;
    setInputValue("");
    setIsLoading(true);

    try {
      await handleStreamingResponse(currentInput);
    } catch {
    } finally {
      setIsLoading(false);
    }
  }, [inputValue, isLoading, handleStreamingResponse]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  if (!user) {
    return null;
  }

  return (
    <>
      {isOpen && (
        <div className={cn("fixed z-[60] inset-0 md:inset-auto md:bottom-4 md:right-4 md:flex md:flex-col md:items-end", className)} data-testid="ai-chat-widget">
        <div className="w-full h-full md:mb-3 md:w-[480px] md:h-[600px] bg-background md:border md:border-border md:rounded-2xl md:shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom-5 md:slide-in-from-bottom-5 fade-in duration-300">
          <div className="flex items-center justify-between px-4 py-3 md:py-2.5 border-b border-border bg-card shrink-0 safe-area-top">
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 md:h-8 md:w-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                <Bot className="h-5 w-5 md:h-4 md:w-4 text-primary-foreground" />
              </div>
              <div className="min-w-0">
                <h3 className="text-base md:text-sm font-semibold text-foreground">AI Movie Assistant</h3>
                <p className="text-xs md:text-[10px] text-muted-foreground">Ask me for recommendations</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleOpen}
              className="h-9 w-9 md:h-8 md:w-8 p-0 rounded-full hover:bg-muted shrink-0"
              data-testid="button-close-chat"
            >
              <X className="h-5 w-5 md:h-4 md:w-4" />
            </Button>
          </div>

          <div className="flex-1 relative min-h-0 overflow-hidden">
            <ScrollArea ref={scrollAreaRef} className="h-full px-3 md:px-3 py-2">
              <div className="space-y-3 pb-2">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      "chat-message flex items-start gap-2",
                      message.type === "user" ? "justify-end" : "justify-start"
                    )}
                  >
                    {message.type === "ai" && (
                      <div className="flex h-6 w-6 shrink-0 select-none items-center justify-center rounded-full bg-primary/10 mt-0.5">
                        <Bot className="h-3 w-3 text-primary" />
                      </div>
                    )}

                    <div
                      className={cn(
                        "rounded-2xl px-3 py-2",
                        message.type === "user"
                          ? "bg-primary text-primary-foreground max-w-[80%] rounded-br-md"
                          : "bg-muted text-foreground max-w-[95%] rounded-bl-md"
                      )}
                    >
                      {message.isStreaming && !message.content && !message.statusMessage && (
                        <TypingIndicator />
                      )}

                      {message.statusMessage && !message.content && (
                        <div className="flex items-center space-x-2 text-xs text-muted-foreground" data-testid={`status-message-${message.id}`}>
                          <Sparkles className="h-3 w-3 animate-pulse text-primary" />
                          <span className="animate-pulse">{message.statusMessage}</span>
                        </div>
                      )}

                      {(() => {
                        if (!message.content) return null;
                        const hasMovieCards = message.movies && message.movies.length > 0;
                        let displayText = message.content;
                        if (hasMovieCards && !message.isStreaming) {
                          const lines = message.content.split('\n');
                          const introLines: string[] = [];
                          for (const line of lines) {
                            if (/^\s*(\d+[\.\)\-:]|\*\*\d+|[-•*]\s)/.test(line)) break;
                            introLines.push(line);
                          }
                          displayText = introLines.join('\n').trim();
                        }
                        if (!displayText && !message.isStreaming) return null;
                        return (
                          <p className="text-sm md:text-[13px] leading-relaxed whitespace-pre-line">
                            {displayText}
                            {message.isStreaming && (
                              <span className="inline-block w-1 h-3.5 bg-primary ml-0.5 animate-pulse align-middle rounded-full" />
                            )}
                          </p>
                        );
                      })()}

                      {((message.movies && message.movies.length > 0) || (message.moviesLoading && !message.moviesDone)) && (
                        <div className="mt-2 pt-2 border-t border-border/30" data-testid={`movie-cards-${message.id}`}>
                          {message.movies && message.movies.length > 0 && !message.moviesDone === false && (
                            <div className="flex items-center gap-1.5 mb-2">
                              <Sparkles className="h-3 w-3 text-yellow-500" />
                              <span className="text-[11px] font-medium text-foreground">
                                {Math.min(message.movies.length, 4)} picks for you
                              </span>
                            </div>
                          )}

                          <div className="grid grid-cols-2 gap-2.5 md:gap-2">
                            {message.movies && message.movies.slice(0, 4).map((movie: any) => {
                              const mediaType = movie.media_type === 'tv' ? 'tv' : 'movie';
                              const title = movie.title || movie.name || 'Untitled';
                              const posterUrl = movie.poster_path
                                ? `https://image.tmdb.org/t/p/w342${movie.poster_path}`
                                : null;
                              const rating = movie.vote_average || 0;
                              const year = movie.release_date
                                ? new Date(movie.release_date).getFullYear()
                                : movie.first_air_date
                                  ? new Date(movie.first_air_date).getFullYear()
                                  : '';
                              const genre = movie.genre_ids?.length
                                ? TMDB_GENRE_MAP[movie.genre_ids[0]] || ''
                                : '';
                              const detailPath = mediaType === 'tv' ? `/tv/${movie.id}` : `/movie/${movie.id}`;

                              return (
                                <Link key={movie.id} href={detailPath} onClick={toggleOpen}>
                                  <div
                                    className="group rounded-lg overflow-hidden border border-border/40 bg-card hover:border-primary/50 transition-all duration-200 cursor-pointer"
                                    data-testid={`movie-card-${movie.id}`}
                                  >
                                    <div className="relative aspect-[2/3] overflow-hidden bg-muted">
                                      {posterUrl ? (
                                        <img
                                          src={posterUrl}
                                          alt={title}
                                          loading="lazy"
                                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                                        />
                                      ) : (
                                        <div className="w-full h-full flex items-center justify-center text-muted-foreground text-xs">
                                          No Poster
                                        </div>
                                      )}
                                      <div className="absolute top-1 right-1 flex items-center gap-0.5 bg-black/70 text-yellow-400 text-[11px] md:text-[10px] font-semibold px-1.5 py-0.5 rounded">
                                        <Star className="h-3 w-3 md:h-2.5 md:w-2.5 fill-yellow-400" />
                                        {rating.toFixed(1)}
                                      </div>
                                    </div>
                                    <div className="px-2 py-1.5 md:px-1.5 md:py-1">
                                      <p className="font-medium text-xs md:text-[11px] leading-tight text-foreground line-clamp-2 group-hover:text-primary transition-colors">
                                        {title}
                                      </p>
                                      <p className="text-[11px] md:text-[10px] text-muted-foreground mt-0.5 truncate">
                                        {[year, genre].filter(Boolean).join(' \u2022 ')}
                                      </p>
                                    </div>
                                  </div>
                                </Link>
                              );
                            })}
                            {message.moviesLoading && !message.moviesDone && (
                              <>
                                {Array.from({ length: Math.max(0, (message.moviesLoading || 4) - (message.movies?.length || 0)) }).map((_, i) => (
                                  <div key={`skeleton-${i}`} data-testid={`movie-skeleton-${i}`}>
                                    <div className="rounded-lg overflow-hidden border border-border/40 bg-card animate-pulse">
                                      <div className="aspect-[2/3] bg-muted" />
                                      <div className="px-1 py-0.5">
                                        <div className="h-2 bg-muted rounded w-3/4" />
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {isLoading && !messages.some(m => m.isStreaming) && (
                  <div className="flex items-start gap-2" data-testid="loading-indicator">
                    <div className="flex h-6 w-6 shrink-0 select-none items-center justify-center rounded-full bg-primary/10">
                      <Bot className="h-3 w-3 text-primary" />
                    </div>
                    <div className="bg-muted rounded-2xl rounded-bl-md px-3 py-2">
                      <TypingIndicator />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {showScrollButton && (
              <Button
                onClick={() => scrollToBottom(true)}
                size="sm"
                className="absolute bottom-2 right-3 h-7 w-7 rounded-full shadow-md z-10"
                variant="secondary"
                title="Scroll to bottom"
              >
                <ArrowDown className="h-3 w-3" />
              </Button>
            )}
          </div>

          <div className="border-t border-border bg-card px-3 md:px-3 py-2.5 md:py-2 space-y-2 shrink-0 safe-area-bottom">
            <div className="flex flex-wrap gap-1.5 md:gap-1">
              {quickSuggestions.slice(0, 4).map((suggestion, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => setInputValue(suggestion.query)}
                  className="text-xs md:text-[10px] h-7 md:h-5 px-2.5 md:px-1.5 rounded-full"
                  disabled={isLoading}
                  data-testid={`button-suggestion-${index}`}
                >
                  {suggestion.label}
                </Button>
              ))}
            </div>

            <div className="flex gap-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask for movie recommendations..."
                disabled={isLoading}
                className="flex-1 h-11 md:h-9 text-base md:text-sm rounded-full bg-muted border-0 focus-visible:ring-1"
                data-testid="input-chat-message"
              />
              <Button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                size="sm"
                className="h-11 w-11 md:h-9 md:w-9 rounded-full p-0"
                data-testid="button-send-message"
              >
                <Send className="h-5 w-5 md:h-4 md:w-4" />
              </Button>
            </div>
          </div>
         </div>
        </div>
      )}

      {!isOpen && fabPos.x >= 0 && fabPos.y >= 0 && (
        <button
          ref={fabRef}
          onClick={handleFabClick}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          className="fixed h-14 w-14 rounded-full shadow-lg hover:shadow-xl transition-shadow duration-300 p-0 bg-primary text-primary-foreground hover:bg-primary/90 flex items-center justify-center select-none cursor-grab active:cursor-grabbing z-[60]"
          style={{ left: fabPos.x, top: fabPos.y, touchAction: 'none' }}
          data-testid="button-toggle-chat"
        >
          <MessageSquare className="h-6 w-6 pointer-events-none" />
        </button>
      )}
    </>
  );
}
