import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, Sparkles, ArrowDown, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { MediaCard } from "@/components/media-card";
import { useAuth } from "@/hooks/useAuth";

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

export default function AIChat({ className }: AIChatProps) {
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
                  setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                      ? { ...m, movies: [...(m.movies || []), event.movie] }
                      : m
                  ));
                  scrollToBottom();
                } else if (event.type === 'done') {
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
      await handleFallbackResponse(userInput, streamingMsgId);
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

  return (
    <Card className={cn("flex flex-col w-full max-w-7xl h-full", className)}>
      <CardHeader className="pb-2 px-3 sm:px-4 pt-2 sm:pt-3 flex-shrink-0">
        <CardTitle className="text-sm sm:text-base flex items-center space-x-2">
          <Bot className="h-4 w-4 text-accent flex-shrink-0" />
          <span>AI Movie Assistant</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-2 sm:p-3 pt-0 sm:pt-0 overflow-hidden">
        <div className="flex-1 relative min-h-0 overflow-hidden mb-2 sm:mb-3">
          <ScrollArea ref={scrollAreaRef} className="h-full max-h-full pr-1 sm:pr-2">
            <div className="space-y-3 sm:space-y-4 pb-2">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "chat-message flex items-start space-x-3",
                    message.type === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  {message.type === "ai" && (
                    <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-lg bg-accent">
                      <Bot className="h-4 w-4 text-accent-foreground" />
                    </div>
                  )}

                  <div
                    className={cn(
                      "rounded-lg p-3",
                      message.type === "user"
                        ? "bg-primary text-primary-foreground max-w-[85%] sm:max-w-[70%]"
                        : "bg-muted text-muted-foreground max-w-full sm:max-w-[95%]"
                    )}
                  >
                    {message.isStreaming && !message.content && !message.statusMessage && (
                      <TypingIndicator />
                    )}

                    {message.statusMessage && !message.content && (
                      <div className="flex items-center space-x-2 text-sm text-muted-foreground" data-testid={`status-message-${message.id}`}>
                        <Sparkles className="h-3.5 w-3.5 animate-pulse text-accent" />
                        <span className="animate-pulse">{message.statusMessage}</span>
                      </div>
                    )}

                    {message.content && (
                      <p className="text-sm whitespace-pre-line">
                        {(() => {
                          const hasMovieCards = message.movies && message.movies.length > 0;
                          if (hasMovieCards && !message.isStreaming) {
                            const lines = message.content.split('\n');
                            const firstNumberedIdx = lines.findIndex(l => /^\s*\d+[\.\)]\s/.test(l));
                            if (firstNumberedIdx > 0) {
                              const intro = lines.slice(0, firstNumberedIdx).join('\n').trim();
                              return intro || message.content;
                            }
                          }
                          return message.content;
                        })()}
                        {message.isStreaming && (
                          <span className="inline-block w-1.5 h-4 bg-accent ml-0.5 animate-pulse align-middle" />
                        )}
                      </p>
                    )}

                    {((message.movies && message.movies.length > 0) || (message.moviesLoading && !message.moviesDone)) && (
                      <div className="mt-3 sm:mt-4 bg-gradient-to-r from-muted/30 to-muted/10 rounded-lg p-2 sm:p-3 md:p-4 border border-border/50" data-testid={`movie-cards-${message.id}`}>
                        <div className="flex flex-wrap items-center gap-2 mb-3 sm:mb-4">
                          <div className="flex items-center gap-1.5 sm:gap-2">
                            <Sparkles className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-yellow-500 flex-shrink-0" />
                            <span className="text-xs sm:text-sm font-semibold text-foreground">
                              AI Movie Recommendations
                            </span>
                          </div>
                          {message.movies && message.movies.length > 0 ? (
                            <Badge variant="secondary" className="text-[10px] sm:text-xs px-1.5 py-0.5 sm:px-2">
                              {message.moviesDone
                                ? `${Math.min(message.movies.length, 8)} movies`
                                : `Loading... ${message.movies.length}/${message.moviesLoading || '?'}`
                              }
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-[10px] sm:text-xs px-1.5 py-0.5 sm:px-2 animate-pulse">
                              Finding movies...
                            </Badge>
                          )}
                        </div>

                        <div className="w-full overflow-hidden">
                          <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 sm:gap-3">
                            {message.movies && message.movies.slice(0, 8).map((movie: any) => (
                              <div key={movie.id} className="w-full min-w-0" data-testid={`movie-card-${movie.id}`}>
                                <MediaCard
                                  item={movie}
                                  mediaType={movie.media_type === 'tv' ? 'tv' : 'movie'}
                                />
                              </div>
                            ))}
                            {message.moviesLoading && !message.moviesDone && (
                              <>
                                {Array.from({ length: Math.max(0, (message.moviesLoading || 4) - (message.movies?.length || 0)) }).map((_, i) => (
                                  <div key={`skeleton-${i}`} className="w-full min-w-0" data-testid={`movie-skeleton-${i}`}>
                                    <div className="rounded-lg overflow-hidden border border-border/50 bg-card animate-pulse">
                                      <div className="aspect-[2/3] bg-muted" />
                                      <div className="p-2 space-y-2">
                                        <div className="h-3 bg-muted rounded w-3/4" />
                                        <div className="h-2 bg-muted rounded w-1/2" />
                                        <div className="flex items-center gap-1">
                                          <Star className="h-3 w-3 text-muted" />
                                          <div className="h-2 bg-muted rounded w-8" />
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {message.type === "user" && (
                    <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-lg bg-primary">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </div>
              ))}

              {isLoading && !messages.some(m => m.isStreaming) && (
                <div className="flex items-start space-x-3" data-testid="loading-indicator">
                  <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-lg bg-accent">
                    <Bot className="h-4 w-4 text-accent-foreground" />
                  </div>
                  <div className="bg-muted rounded-lg p-3">
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
              className="absolute bottom-4 right-4 h-10 w-10 rounded-full shadow-lg z-10 hover:shadow-xl transition-all"
              variant="secondary"
              title="Scroll to bottom"
            >
              <ArrowDown className="h-4 w-4" />
            </Button>
          )}
        </div>

        <div className="flex-shrink-0 mb-2">
          <div className="flex flex-wrap gap-1">
            {quickSuggestions.slice(0, 6).map((suggestion, index) => (
              <Button
                key={index}
                variant="outline"
                size="sm"
                onClick={() => setInputValue(suggestion.query)}
                className="text-[10px] sm:text-xs h-5 sm:h-6 px-1.5 sm:px-2"
                disabled={isLoading}
                data-testid={`button-suggestion-${index}`}
              >
                {suggestion.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex space-x-2 flex-shrink-0">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="What are you looking for? (e.g., 'what's new in theaters?')"
            disabled={isLoading}
            className="flex-1"
            data-testid="input-chat-message"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
            size="sm"
            data-testid="button-send-message"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
