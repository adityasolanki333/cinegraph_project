import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, Sparkles, ArrowDown, Star, X, MessageSquare, Mic, MicOff, Volume2, VolumeX, Trash2, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";
import { Link } from "wouter";
import { getAuthHeaders } from "@/lib/queryClient";

const TMDB_GENRE_MAP: Record<number, string> = {
  28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime',
  99: 'Documentary', 18: 'Drama', 10751: 'Family', 14: 'Fantasy', 36: 'History',
  27: 'Horror', 10402: 'Music', 9648: 'Mystery', 10749: 'Romance',
  878: 'Sci-Fi', 10770: 'TV Movie', 53: 'Thriller', 10752: 'War', 37: 'Western',
  10759: 'Action & Adventure', 10762: 'Kids', 10765: 'Sci-Fi & Fantasy',
};

interface ChatMessage {
  id: string;
  type: "user" | "ai";
  content: string;
  movies?: any[];
  source?: string;
  timestamp: Date;
  isStreaming?: boolean;
  statusMessage?: string;
  moviesLoading?: number;
  moviesDone?: boolean;
  isVoice?: boolean;
  fromCache?: boolean;
}

interface AIChatProps {
  className?: string;
  isOpen?: boolean;
  onToggle?: () => void;
}

const ALL_SUGGESTIONS = [
  { label: "😂 Something Funny", query: "I want something funny to laugh at tonight" },
  { label: "🔥 Thrilling Action", query: "show me thrilling action movies" },
  { label: "💕 Date Night", query: "romantic movies for a cozy date night" },
  { label: "😱 Scary Films", query: "I'm in the mood for something scary" },
  { label: "🆕 In Theaters", query: "what movies are in theaters right now?" },
  { label: "😊 Feel-Good", query: "uplifting feel-good movies that make you smile" },
  { label: "🤯 Mind-Bending", query: "thought-provoking mind-bending films" },
  { label: "💎 Hidden Gems", query: "underrated movies I probably haven't seen" },
  { label: "🚀 Sci-Fi", query: "best science fiction movies" },
  { label: "🎭 Oscar Winners", query: "critically acclaimed award-winning dramas" },
  { label: "👨‍👩‍👧 Family Fun", query: "great family movies everyone will enjoy" },
  { label: "🕵️ Mystery", query: "gripping mystery and thriller movies" },
];

const WELCOME_MSG: ChatMessage = {
  id: "welcome",
  type: "ai",
  content: "Hi! I'm CineBot, your AI movie companion. Ask me for recommendations, ask about any movie, or just tap the mic and speak — I'm listening! 🎬",
  timestamp: new Date(),
  moviesDone: true,
};

const THINKING_STEPS = [
  { icon: "🎬", text: "Searching the catalog…" },
  { icon: "🧠", text: "Thinking it through…" },
  { icon: "✨", text: "Finding your picks…" },
  { icon: "🍿", text: "Almost ready…" },
  { icon: "🎥", text: "Curating results…" },
  { icon: "⭐", text: "Personalizing for you…" },
];

function TypingIndicator() {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const fade = setInterval(() => {
      setVisible(false);
      setTimeout(() => {
        setStep(s => (s + 1) % THINKING_STEPS.length);
        setVisible(true);
      }, 300);
    }, 2200);
    return () => clearInterval(fade);
  }, []);

  const { icon, text } = THINKING_STEPS[step];

  return (
    <div className="flex flex-col gap-2 py-0.5 min-w-[160px]">
      {/* Animated orb row */}
      <div className="flex items-center gap-2">
        <div className="relative flex items-center justify-center w-7 h-7">
          {/* pulsing rings */}
          <span className="absolute inset-0 rounded-full bg-violet-500/20" style={{ animation: 'orbRing 1.4s ease-in-out infinite' }} />
          <span className="absolute inset-1 rounded-full bg-violet-500/30" style={{ animation: 'orbRing 1.4s ease-in-out 0.3s infinite' }} />
          {/* bars */}
          <span className="relative flex items-end gap-[2px] h-3.5">
            {[0,1,2,3].map(i => (
              <span key={i} className="w-[3px] rounded-full bg-gradient-to-t from-violet-500 to-blue-400"
                style={{ animation: `thinkBar 0.8s ease-in-out ${i * 0.15}s infinite alternate`, height: '6px' }} />
            ))}
          </span>
        </div>
        <div
          className="text-xs text-muted-foreground font-medium transition-all duration-300"
          style={{ opacity: visible ? 1 : 0, transform: visible ? 'translateY(0)' : 'translateY(4px)' }}
        >
          {icon} {text}
        </div>
      </div>
      {/* Progress shimmer */}
      <div className="h-0.5 w-full rounded-full bg-border/40 overflow-hidden">
        <div className="h-full rounded-full bg-gradient-to-r from-violet-500 via-blue-400 to-violet-500"
          style={{ animation: 'shimmerBar 1.8s ease-in-out infinite', backgroundSize: '200% 100%' }} />
      </div>
    </div>
  );
}

function WaveformBars({ active }: { active: boolean }) {
  return (
    <div className="flex items-center gap-0.5 h-5">
      {Array.from({ length: 7 }).map((_, i) => (
        <span
          key={i}
          className="w-0.5 rounded-full bg-red-400"
          style={{
            height: active ? `${8 + Math.sin(i * 1.3) * 6}px` : '3px',
            animation: active ? `waveBar 0.6s ease-in-out ${i * 0.08}s infinite alternate` : 'none',
            transition: 'height 0.3s',
          }}
        />
      ))}
    </div>
  );
}

function buildFollowUps(msg: ChatMessage): string[] {
  const chips: string[] = [];
  const movies = msg.movies || [];
  if (movies.length > 0) {
    const t1 = movies[0]?.title || movies[0]?.name;
    if (t1) {
      chips.push(`More movies like "${t1}"`);
      chips.push(`Tell me about "${t1}"`);
    }
  }
  if (movies.length > 1) {
    const t2 = movies[1]?.title || movies[1]?.name;
    if (t2) chips.push(`Who directed "${t2}"?`);
  }
  chips.push("Show me something different");
  chips.push("Any hidden gems in this genre?");
  chips.push("What's trending this week?");
  return chips.slice(0, 3);
}

export default function AIChat({ className, isOpen: controlledOpen, onToggle }: AIChatProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const stableToggle = useCallback(() => setInternalOpen(prev => !prev), []);
  const toggleOpen = onToggle || stableToggle;
  const { user } = useAuth();

  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const saved = sessionStorage.getItem('aiChat_messages_v2');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.map((msg: any) => ({ ...msg, timestamp: new Date(msg.timestamp), isStreaming: false }));
      } catch {}
    }
    return [WELCOME_MSG];
  });

  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [suggestionPage, setSuggestionPage] = useState(0);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [isSpeaking, setIsSpeaking] = useState(false);

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sendInFlightRef = useRef(false);
  const recognitionRef = useRef<any>(null);
  const finalTranscriptRef = useRef("");
  const handleSendRef = useRef<(text: string) => void>(() => {});
  const speechRef = useRef<SpeechSynthesisUtterance | null>(null);

  const [fabPos, setFabPos] = useState<{ x: number; y: number }>(() => {
    const saved = localStorage.getItem('aiChat_fabPos');
    if (saved) { try { return JSON.parse(saved); } catch {} }
    return { x: -1, y: -1 };
  });
  const fabRef = useRef<HTMLButtonElement>(null);
  const wasDragged = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, posX: 0, posY: 0 });

  const clampPos = useCallback((x: number, y: number) => {
    const size = 56, pad = 4;
    return { x: Math.max(pad, Math.min(x, window.innerWidth - size - pad)), y: Math.max(pad, Math.min(y, window.innerHeight - size - pad)) };
  }, []);

  useEffect(() => {
    if (fabPos.x === -1 && fabPos.y === -1)
      setFabPos({ x: window.innerWidth - 56 - 16, y: window.innerHeight - 56 - 80 });
  }, [fabPos]);

  useEffect(() => {
    if (fabPos.x >= 0) localStorage.setItem('aiChat_fabPos', JSON.stringify(fabPos));
  }, [fabPos]);

  useEffect(() => {
    const onResize = () => setFabPos(prev => prev.x < 0 ? prev : clampPos(prev.x, prev.y));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [clampPos]);

  const handleFabClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault(); e.stopPropagation();
    if (wasDragged.current) { wasDragged.current = false; return; }
    setUnreadCount(0);
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
    const dx = e.clientX - dragStart.current.x, dy = e.clientY - dragStart.current.y;
    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) wasDragged.current = true;
    if (wasDragged.current) setFabPos(clampPos(dragStart.current.posX + dx, dragStart.current.posY + dy));
  }, [clampPos]);

  const onPointerUp = useCallback((e: React.PointerEvent<HTMLButtonElement>) => {
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
    if (wasDragged.current) {
      const size = 56;
      setFabPos(prev => { const sx = (prev.x + size / 2) < window.innerWidth / 2 ? 4 : window.innerWidth - size - 4; return clampPos(sx, prev.y); });
    }
  }, [clampPos]);

  useEffect(() => {
    const toSave = messages.map(m => ({ ...m, isStreaming: false, statusMessage: undefined, moviesLoading: undefined, moviesDone: true }));
    sessionStorage.setItem('aiChat_messages_v2', JSON.stringify(toSave));
  }, [messages]);

  const scrollToBottom = useCallback((smooth = false) => {
    const sc = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (sc) sc.scrollTo({ top: sc.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  }, []);

  const handleScroll = useCallback(() => {
    const sc = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (sc) {
      const { scrollTop, scrollHeight, clientHeight } = sc;
      setShowScrollButton(scrollHeight - scrollTop - clientHeight > 150 && scrollHeight > clientHeight);
    }
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  useEffect(() => {
    const sc = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (sc) { sc.addEventListener('scroll', handleScroll); handleScroll(); return () => sc.removeEventListener('scroll', handleScroll); }
  }, [handleScroll]);

  useEffect(() => {
    if (messages.length > 1) {
      const sc = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
      if (sc) { const { scrollTop, scrollHeight, clientHeight } = sc; if (scrollHeight - scrollTop - clientHeight < 150) setTimeout(() => scrollToBottom(), 100); }
    }
  }, [messages.length, scrollToBottom]);

  const getConversationHistory = useCallback(() =>
    messages.filter(m => m.type === 'user' || (m.type === 'ai' && m.id !== 'welcome')).slice(-6).map(m => ({ type: m.type, content: m.content }))
  , [messages]);

  const speakText = useCallback((text: string) => {
    if (!voiceEnabled || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const plainText = text.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/[#*_`]/g, '').slice(0, 600);
    const utt = new SpeechSynthesisUtterance(plainText);
    utt.rate = 1.0; utt.pitch = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.name.includes('Google') && v.lang.startsWith('en')) || voices.find(v => v.lang.startsWith('en-'));
    if (preferred) utt.voice = preferred;
    utt.onstart = () => setIsSpeaking(true);
    utt.onend = () => setIsSpeaking(false);
    utt.onerror = () => setIsSpeaking(false);
    speechRef.current = utt;
    window.speechSynthesis.speak(utt);
  }, [voiceEnabled]);

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis?.cancel();
    setIsSpeaking(false);
  }, []);

  const handleStreamingResponse = useCallback(async (userInput: string) => {
    const history = getConversationHistory();
    const streamingMsgId = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    let streamingReceivedContent = false;

    setMessages(prev => [...prev, { id: streamingMsgId, type: "ai", content: "", movies: [], timestamp: new Date(), isStreaming: true }]);

    try {
      const response = await fetch('/api/ai/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ message: userInput, userId: user?.id ? String(user.id) : undefined, history }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const contentType = response.headers.get('content-type') || '';

      const applySseEvent = (event: Record<string, unknown>) => {
        const t = event.type as string;
        if (t === 'status') {
          setMessages(prev => prev.map(m => m.id === streamingMsgId ? { ...m, statusMessage: event.message as string } : m));
        } else if (t === 'chunk' && typeof event.content === 'string') {
          streamingReceivedContent = true;
          setMessages(prev => prev.map(m => m.id === streamingMsgId ? { ...m, content: m.content + event.content, statusMessage: undefined } : m));
          scrollToBottom();
        } else if (t === 'movies_loading') {
          setMessages(prev => prev.map(m => m.id === streamingMsgId ? { ...m, moviesLoading: event.count as number, moviesDone: false, movies: [] } : m));
        } else if (t === 'movie' && event.movie) {
          streamingReceivedContent = true;
          setMessages(prev => prev.map(m => m.id === streamingMsgId ? { ...m, movies: [...(m.movies || []), event.movie] } : m));
          scrollToBottom();
        } else if (t === 'done') {
          streamingReceivedContent = true;
          setMessages(prev => prev.map(m => {
            if (m.id !== streamingMsgId) return m;
            const finalMsg = {
              ...m,
              movies: Array.isArray(event.movies) && (event.movies as unknown[]).length > 0 ? (event.movies as typeof m.movies) : (m.movies || []),
              isStreaming: false, moviesDone: true, moviesLoading: undefined,
              fromCache: !!(event as any).fromCache,
            };
            if (voiceEnabled && finalMsg.content) setTimeout(() => speakText(finalMsg.content), 300);
            return finalMsg;
          }));
          if (!isOpen) setUnreadCount(c => c + 1);
        } else if (t === 'fallback') {
          streamingReceivedContent = true;
          setMessages(prev => prev.map(m => m.id === streamingMsgId ? {
            ...m, content: (event.response as string) || m.content,
            movies: Array.isArray(event.movies) && (event.movies as unknown[]).length > 0 ? (event.movies as typeof m.movies) : (m.movies || []),
            source: 'fallback', isStreaming: false, moviesDone: true,
          } : m));
        } else if (t === 'error') {
          setMessages(prev => prev.map(m => m.id === streamingMsgId ? {
            ...m, content: (event.message as string) || 'Something went wrong. Please try again.',
            isStreaming: false, moviesDone: true, moviesLoading: undefined, statusMessage: undefined,
          } : m));
        }
      };

      const parseSseLine = (line: string) => {
        const trimmed = line.replace(/\r$/, '').trim();
        if (!trimmed.startsWith('data:')) return;
        const payload = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed.slice(5).trimStart();
        if (payload === '[DONE]') return;
        try { applySseEvent(JSON.parse(payload)); } catch {}
      };

      if (contentType.includes('text/event-stream')) {
        const reader = response.body?.getReader();
        if (!reader) throw new Error('No reader');
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split(/\r?\n/);
          buffer = lines.pop() || '';
          for (const line of lines) parseSseLine(line);
        }
        if (buffer.trim()) for (const line of buffer.split(/\r?\n/)) parseSseLine(line);
        setMessages(prev => prev.map(m => {
          if (m.id !== streamingMsgId) return m;
          const hasText = Boolean(m.content?.trim()), hasMovies = Boolean(m.movies?.length);
          return { ...m, isStreaming: false, moviesDone: true, moviesLoading: undefined, statusMessage: undefined, ...(!hasText && !hasMovies ? { content: "I didn't get a complete reply. Please try again in a moment." } : {}) };
        }));
      } else {
        const data = await response.json();
        setMessages(prev => prev.map(m => m.id === streamingMsgId ? {
          ...m, content: data.response || data.error || 'No response received.',
          movies: data.movies || [], source: data.source, isStreaming: false, moviesDone: true,
        } : m));
      }
    } catch (error) {
      if (!streamingReceivedContent) {
        try {
          const resp = await fetch('/api/ai/chat', {
            method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            body: JSON.stringify({ message: userInput, userId: user?.id ? String(user.id) : undefined, history: getConversationHistory() }),
          });
          const data = await resp.json();
          setMessages(prev => prev.map(m => m.id === streamingMsgId ? {
            ...m, content: data.response || "I'd love to help! Tell me what kind of movies you're in the mood for.",
            movies: data.movies || [], source: data.source, isStreaming: false, moviesDone: true, moviesLoading: undefined, statusMessage: undefined,
          } : m));
        } catch {
          setMessages(prev => prev.map(m => m.id === streamingMsgId ? {
            ...m, content: "I'm having trouble connecting right now. Please try again in a moment!",
            isStreaming: false, moviesDone: true, moviesLoading: undefined, statusMessage: undefined,
          } : m));
        }
      } else {
        setMessages(prev => prev.map(m => m.id === streamingMsgId ? { ...m, isStreaming: false, moviesDone: true, moviesLoading: undefined, statusMessage: undefined } : m));
      }
    }
  }, [user, getConversationHistory, scrollToBottom, voiceEnabled, speakText, isOpen]);

  const handleSendMessage = useCallback(async (textOverride?: string) => {
    const text = (textOverride ?? inputValue).trim();
    if (!text || isLoading || sendInFlightRef.current) return;
    sendInFlightRef.current = true;
    stopSpeaking();
    setMessages(prev => [...prev, { id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`, type: "user", content: text, timestamp: new Date() }]);
    setInputValue("");
    setIsLoading(true);
    try { await handleStreamingResponse(text); } catch {} finally { sendInFlightRef.current = false; setIsLoading(false); }
  }, [inputValue, isLoading, handleStreamingResponse, stopSpeaking]);

  // Keep a ref so speech recognition onend can call it without stale closure
  useEffect(() => { handleSendRef.current = (t: string) => handleSendMessage(t); }, [handleSendMessage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== "Enter" || e.shiftKey || e.nativeEvent.isComposing) return;
    e.preventDefault(); void handleSendMessage();
  }, [handleSendMessage]);

  const toggleVoice = useCallback(() => {
    if (isListening) {
      // Stop — commit whatever was said
      recognitionRef.current?.stop();
      setIsListening(false);
      const text = finalTranscriptRef.current.trim() || liveTranscript.trim();
      if (text) {
        setLiveTranscript("");
        finalTranscriptRef.current = "";
        setInputValue("");
        setTimeout(() => handleSendRef.current(text), 100);
      } else {
        setLiveTranscript("");
        finalTranscriptRef.current = "";
      }
      return;
    }

    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;

    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    finalTranscriptRef.current = "";
    setLiveTranscript("");
    setIsListening(true);

    recognition.onresult = (e: any) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) {
          finalTranscriptRef.current += t + " ";
        } else {
          interim += t;
        }
      }
      const full = (finalTranscriptRef.current + interim).trim();
      setLiveTranscript(full);
      setInputValue(full);
    };

    recognition.onend = () => {
      setIsListening(false);
      const text = finalTranscriptRef.current.trim();
      if (text) {
        setLiveTranscript("");
        finalTranscriptRef.current = "";
        setInputValue("");
        setTimeout(() => handleSendRef.current(text), 150);
      } else {
        setLiveTranscript("");
        finalTranscriptRef.current = "";
      }
    };

    recognition.onerror = (e: any) => {
      if (e.error === 'no-speech' || e.error === 'aborted') return;
      console.error('Speech recognition error:', e.error);
      setIsListening(false);
      setLiveTranscript("");
      finalTranscriptRef.current = "";
    };

    recognition.start();
    recognitionRef.current = recognition;
  }, [isListening, liveTranscript]);

  const clearChat = useCallback(() => {
    stopSpeaking();
    setMessages([WELCOME_MSG]);
    setSuggestionPage(0);
  }, [stopSpeaking]);

  const currentSuggestions = ALL_SUGGESTIONS.slice(suggestionPage * 4, suggestionPage * 4 + 4).concat(
    ALL_SUGGESTIONS.slice(0, Math.max(0, (suggestionPage * 4 + 4) - ALL_SUGGESTIONS.length))
  ).slice(0, 4);

  const rotateSuggestions = useCallback(() => {
    setSuggestionPage(p => (p + 1) % Math.ceil(ALL_SUGGESTIONS.length / 4));
  }, []);

  if (!user) return null;

  const canVoice = !!(window as any).SpeechRecognition || !!(window as any).webkitSpeechRecognition;

  return (
    <>
      <style>{`
        @keyframes bounce { 0%, 100% { transform: translateY(0); opacity: 0.5; } 50% { transform: translateY(-4px); opacity: 1; } }
        @keyframes waveBar { from { transform: scaleY(0.4); opacity: 0.7; } to { transform: scaleY(1.4); opacity: 1; } }
        @keyframes msgSlide { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulseRing { 0% { transform: scale(1); opacity: 0.6; } 100% { transform: scale(1.8); opacity: 0; } }
        @keyframes orbRing { 0%, 100% { transform: scale(1); opacity: 0.4; } 50% { transform: scale(1.5); opacity: 0.1; } }
        @keyframes thinkBar { from { transform: scaleY(0.4); opacity: 0.6; } to { transform: scaleY(2.2); opacity: 1; } }
        @keyframes shimmerBar { 0% { background-position: 200% center; } 100% { background-position: -200% center; } }
        .msg-enter { animation: msgSlide 0.25s ease-out forwards; }
      `}</style>

      {isOpen && (
        <div className={cn("fixed z-[60] inset-0 md:inset-auto md:bottom-4 md:right-4 md:flex md:flex-col md:items-end", className)}>
          <div className="w-full h-full md:mb-3 md:w-[520px] md:h-[680px] bg-background md:border md:border-border/50 md:rounded-2xl md:shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom-5 fade-in duration-300">

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 shrink-0 relative overflow-hidden"
              style={{ background: 'linear-gradient(135deg, #1e1b4b 0%, #1e3a5f 50%, #14274e 100%)' }}>
              <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, #7c3aed 0%, transparent 50%), radial-gradient(circle at 80% 20%, #2563eb 0%, transparent 40%)' }} />
              <div className="relative flex items-center gap-2.5">
                <div className="relative">
                  <div className="h-9 w-9 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center">
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                  <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-[#1e1b4b]" style={{ animation: isLoading || isListening ? 'pulse 1s ease-in-out infinite' : 'none' }} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-1.5">
                    CineBot
                    {isSpeaking && <Volume2 className="h-3 w-3 text-emerald-400 animate-pulse" />}
                  </h3>
                  <p className="text-[10px] text-white/60">
                    {isListening ? "Listening…" : isLoading ? "Thinking..." : "AI Movie Assistant"}
                  </p>
                </div>
              </div>
              <div className="relative flex items-center gap-1">
                <Button variant="ghost" size="sm" onClick={clearChat} className="h-8 w-8 p-0 rounded-full hover:bg-white/10 text-white/60 hover:text-white" title="Clear chat">
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
                <Button variant="ghost" size="sm"
                  onClick={() => { setVoiceEnabled(v => !v); if (isSpeaking) stopSpeaking(); }}
                  className="h-8 w-8 p-0 rounded-full hover:bg-white/10 text-white/60 hover:text-white"
                  title={voiceEnabled ? "Mute AI voice" : "Enable AI voice"}
                >
                  {voiceEnabled ? <Volume2 className="h-3.5 w-3.5" /> : <VolumeX className="h-3.5 w-3.5" />}
                </Button>
                <Button variant="ghost" size="sm" onClick={toggleOpen} className="h-8 w-8 p-0 rounded-full hover:bg-white/10 text-white/60 hover:text-white">
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 relative min-h-0 overflow-hidden">
              <ScrollArea ref={scrollAreaRef} className="h-full px-3 py-2">
                <div className="space-y-2.5 pb-2">
                  {messages.map((message, idx) => (
                    <div key={message.id} className={cn("msg-enter flex items-end gap-2", message.type === "user" ? "justify-end" : "justify-start")} style={{ animationDelay: `${idx * 20}ms` }}>
                      {message.type === "ai" && (
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-blue-600 mb-0.5">
                          <Bot className="h-3.5 w-3.5 text-white" />
                        </div>
                      )}

                      <div className={cn(
                        "rounded-2xl px-3.5 py-2.5 shadow-sm max-w-[85%]",
                        message.type === "user"
                          ? "bg-gradient-to-br from-violet-600 to-blue-600 text-white rounded-br-sm"
                          : "bg-muted/80 text-foreground rounded-bl-sm border border-border/30"
                      )}>
                        {message.type === "user" && message.isVoice && (
                          <div className="flex items-center gap-1 mb-1 opacity-70">
                            <Mic className="h-2.5 w-2.5" />
                            <span className="text-[9px] uppercase tracking-wider">Voice</span>
                          </div>
                        )}

                        {message.isStreaming && !message.content && !message.statusMessage && <TypingIndicator />}

                        {message.statusMessage && !message.content && (
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <Sparkles className="h-3 w-3 animate-pulse text-violet-400" />
                            <span className="animate-pulse">{message.statusMessage}</span>
                          </div>
                        )}

                        {(() => {
                          if (!message.content) return null;
                          const hasMovieCards = message.movies && message.movies.length > 0;
                          let displayText = message.content;
                          if (hasMovieCards && !message.isStreaming) {
                            const lines = message.content.split('\n');
                            const intro: string[] = [];
                            for (const line of lines) {
                              if (/^\s*(\d+[\.\)\-:]|\*\*\d+|[-•*]\s)/.test(line)) break;
                              intro.push(line);
                            }
                            displayText = intro.join('\n').trim();
                          }
                          if (!displayText && !message.isStreaming) return null;

                          // Render with markdown formatting
                          const renderLine = (line: string, key: number) => {
                            // Numbered list
                            const numMatch = line.match(/^\s*(\d+)[.)]\s+(.+)/);
                            if (numMatch) return (
                              <div key={key} className="flex gap-1.5 items-start text-sm leading-relaxed">
                                <span className="shrink-0 w-4 h-4 rounded-full bg-violet-500/20 text-violet-400 text-[10px] font-bold flex items-center justify-center mt-0.5">{numMatch[1]}</span>
                                <span>{renderInline(numMatch[2])}</span>
                              </div>
                            );
                            // Bullet list
                            const bulletMatch = line.match(/^\s*[-•*]\s+(.+)/);
                            if (bulletMatch) return (
                              <div key={key} className="flex gap-1.5 items-start text-sm leading-relaxed">
                                <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-violet-400 mt-2" />
                                <span>{renderInline(bulletMatch[1])}</span>
                              </div>
                            );
                            // Empty line
                            if (!line.trim()) return <div key={key} className="h-1" />;
                            // Normal line
                            return <p key={key} className="text-sm leading-relaxed">{renderInline(line)}</p>;
                          };

                          const renderInline = (text: string): React.ReactNode => {
                            // Split on **bold** and *italic*
                            const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
                            return parts.map((part, i) => {
                              if (part.startsWith('**') && part.endsWith('**'))
                                return <strong key={i} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>;
                              if (part.startsWith('*') && part.endsWith('*'))
                                return <em key={i} className="italic text-muted-foreground">{part.slice(1, -1)}</em>;
                              return part;
                            });
                          };

                          const lines = displayText.split('\n');
                          return (
                            <div className="space-y-0.5">
                              {lines.map((line, i) => renderLine(line, i))}
                              {message.isStreaming && <span className="inline-block w-0.5 h-3.5 bg-violet-400 ml-0.5 animate-pulse align-middle rounded-full" />}
                            </div>
                          );
                        })()}

                        {message.fromCache && !message.isStreaming && (
                          <div className="flex items-center gap-1 mt-1 opacity-50">
                            <Zap className="h-2.5 w-2.5 text-yellow-400" />
                            <span className="text-[9px] text-yellow-400">From cache</span>
                          </div>
                        )}

                        {((message.movies && message.movies.length > 0) || (message.moviesLoading && !message.moviesDone)) && (
                          <div className="mt-2.5 pt-2 border-t border-border/20">
                            {message.movies && message.movies.length > 0 && (
                              <div className="flex items-center gap-1 mb-2">
                                <Sparkles className="h-3 w-3 text-yellow-400" />
                                <span className="text-[11px] font-medium text-muted-foreground">{message.movies.length} picks for you</span>
                              </div>
                            )}
                            <div className="grid grid-cols-2 gap-2">
                              {message.movies && message.movies.slice(0, 4).map((movie: any) => {
                                const mediaType = movie.media_type === 'tv' ? 'tv' : 'movie';
                                const title = movie.title || movie.name || 'Untitled';
                                const posterUrl = movie.poster_path ? `https://image.tmdb.org/t/p/w342${movie.poster_path}` : null;
                                const rating = movie.vote_average || 0;
                                const year = movie.release_date ? new Date(movie.release_date).getFullYear() : movie.first_air_date ? new Date(movie.first_air_date).getFullYear() : '';
                                const genre = movie.genre_ids?.length ? TMDB_GENRE_MAP[movie.genre_ids[0]] || '' : '';
                                const detailPath = mediaType === 'tv' ? `/tv/${movie.id}` : `/movie/${movie.id}`;
                                return (
                                  <Link key={movie.id} href={detailPath} onClick={toggleOpen}>
                                    <div className="group rounded-xl overflow-hidden border border-border/30 bg-card/80 hover:border-violet-500/60 hover:shadow-lg transition-all duration-200 cursor-pointer">
                                      <div className="relative aspect-[2/3] overflow-hidden bg-muted">
                                        {posterUrl ? (
                                          <img src={posterUrl} alt={title} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                                        ) : (
                                          <div className="w-full h-full flex flex-col items-center justify-center gap-1 text-muted-foreground">
                                            <span className="text-2xl">🎬</span>
                                            <span className="text-[9px]">No Poster</span>
                                          </div>
                                        )}
                                        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/10 to-transparent" />
                                        <div className="absolute bottom-0 inset-x-0 p-1.5">
                                          <p className="font-semibold text-[11px] leading-tight text-white line-clamp-2 group-hover:text-violet-300 transition-colors">{title}</p>
                                          <div className="flex items-center justify-between mt-0.5">
                                            <span className="text-[9px] text-white/60">{[year, genre].filter(Boolean).join(' · ')}</span>
                                            <div className="flex items-center gap-0.5 bg-black/50 text-yellow-400 text-[9px] font-bold px-1 py-0.5 rounded">
                                              <Star className="h-2 w-2 fill-yellow-400" />{rating.toFixed(1)}
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  </Link>
                                );
                              })}
                              {message.moviesLoading && !message.moviesDone && Array.from({ length: Math.max(0, Math.min(4, (message.moviesLoading || 4)) - (message.movies?.length || 0)) }).map((_, i) => (
                                <div key={`sk-${i}`} className="rounded-xl overflow-hidden border border-border/30 bg-card animate-pulse">
                                  <div className="aspect-[2/3] bg-muted" />
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {message.type === "ai" && message.moviesDone && !message.isStreaming && message.id !== 'welcome' && (message.movies?.length || 0) > 0 && (
                          <div className="mt-2 pt-1.5 border-t border-border/20 flex flex-wrap gap-1">
                            {buildFollowUps(message).map((chip, i) => (
                              <button key={i} onClick={() => handleSendMessage(chip)} disabled={isLoading}
                                className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20 hover:bg-violet-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                                {chip}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {isLoading && !messages.some(m => m.isStreaming) && (
                    <div className="flex items-end gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-blue-600 mb-0.5">
                        <Bot className="h-3.5 w-3.5 text-white" />
                      </div>
                      <div className="bg-muted/80 rounded-2xl rounded-bl-sm border border-border/30 px-3.5 py-2.5">
                        <TypingIndicator />
                      </div>
                    </div>
                  )}


                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              {showScrollButton && (
                <Button onClick={() => scrollToBottom(true)} size="sm" variant="secondary"
                  className="absolute bottom-2 right-3 h-7 w-7 rounded-full shadow-md z-10 p-0">
                  <ArrowDown className="h-3 w-3" />
                </Button>
              )}
            </div>

            {/* Quick suggestions */}
            <div className="px-3 pt-2 pb-0 shrink-0">
              <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none">
                {currentSuggestions.map((s, i) => (
                  <Button key={`${suggestionPage}-${i}`} variant="outline" size="sm"
                    onClick={() => handleSendMessage(s.query)}
                    disabled={isLoading}
                    className="text-[10px] h-6 px-2 rounded-full shrink-0 border-border/50 hover:border-violet-500/50 hover:text-violet-400 transition-colors">
                    {s.label}
                  </Button>
                ))}
                <Button variant="ghost" size="sm" onClick={rotateSuggestions}
                  className="text-[10px] h-6 px-2 rounded-full shrink-0 text-muted-foreground hover:text-foreground" title="More suggestions">
                  ↻
                </Button>
              </div>
            </div>

            {/* Input row */}
            <div className="px-3 py-2.5 shrink-0 safe-area-bottom">
              {isListening && (
                <div className="flex items-center gap-3 mb-2 px-3 py-1.5 rounded-xl bg-violet-500/10 border border-violet-500/30">
                  <div className="relative shrink-0">
                    <span className="absolute inset-0 rounded-full bg-violet-500 animate-ping opacity-30" />
                    <span className="relative w-2 h-2 rounded-full bg-violet-400 block" />
                  </div>
                  <WaveformBars active={true} />
                  <span className="text-xs text-violet-300 flex-1 truncate">
                    {liveTranscript || "Listening… speak now"}
                  </span>
                  <button onClick={toggleVoice} className="text-[10px] text-violet-400 hover:text-violet-200 shrink-0 font-medium">done</button>
                </div>
              )}
              <div className="flex gap-2 items-center">
                {canVoice && (
                  <button
                    onClick={toggleVoice}
                    disabled={isLoading}
                    className={cn(
                      "h-11 w-11 md:h-9 md:w-9 rounded-full flex items-center justify-center shrink-0 transition-all duration-200",
                      isListening
                        ? "bg-violet-500 text-white scale-110 shadow-lg shadow-violet-500/40"
                        : "bg-muted hover:bg-violet-500/20 hover:text-violet-400 text-muted-foreground",
                      isLoading && "opacity-50 cursor-not-allowed"
                    )}
                    title={isListening ? "Stop listening" : "Click to speak"}
                  >
                    {isListening ? <MicOff className="h-4 w-4 md:h-3.5 md:w-3.5" /> : <Mic className="h-4 w-4 md:h-3.5 md:w-3.5" />}
                  </button>
                )}
                <Input
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isListening ? "Listening… speak now" : "Ask about any movie..."}
                  disabled={isLoading || isListening}
                  className="flex-1 h-11 md:h-9 text-base md:text-sm rounded-full bg-muted border-0 focus-visible:ring-1 focus-visible:ring-violet-500/50"
                />
                <Button onClick={() => handleSendMessage()} disabled={!inputValue.trim() || isLoading}
                  size="sm" className="h-11 w-11 md:h-9 md:w-9 rounded-full p-0 bg-gradient-to-br from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 shrink-0">
                  <Send className="h-4 w-4 md:h-3.5 md:w-3.5" />
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
          className="fixed h-14 w-14 rounded-full shadow-xl transition-all duration-300 p-0 flex items-center justify-center select-none cursor-grab active:cursor-grabbing z-[60]"
          style={{ left: fabPos.x, top: fabPos.y, touchAction: 'none', background: 'linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)', boxShadow: '0 4px 20px rgba(124,58,237,0.4)' }}
        >
          <MessageSquare className="h-6 w-6 text-white pointer-events-none" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center border-2 border-background">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      )}
    </>
  );
}
