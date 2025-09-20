import { useState, useEffect, useRef, useMemo, useLayoutEffect, useCallback } from 'react';
import { CardGrid, type CardState } from './components/CardGrid';

type GamePhase = 'STARTING' | 'THINKING' | 'GUESSING' | 'ENDED';

interface ChatMessage {
  speaker: string;
  team: 'RED' | 'BLUE' | 'SYSTEM';
  message: string;
  isPrivate?: boolean;
}

interface BoardCard {
  text: string;
  team: string;
  revealed: boolean;
}

interface GameState {
  phase: GamePhase;
  last_action: string;
  last_reasoning: string;
  total_games: number;
  current_team: string | null;
  board: BoardCard[] | null;
  game_state: any;
  red_team: string | null;
  blue_team: string | null;
  shared_context?: ChatMessage[];
  paused?: boolean;
}

type TeamColor = 'RED' | 'BLUE';

type ActiveClue = {
  id: string;
  team: TeamColor;
  word: string;
  number: number;
  chatIndex: number;
};

type ActiveGuess = {
  id: number;
  team: TeamColor;
  word: string;
};

type ClueFlight = {
  id: string;
  team: TeamColor;
  word: string;
  number: number;
  startX: number;
  startY: number;
  endX: number;
  endY: number;
};

function FloatingClue({ flight, onComplete }: { flight: ClueFlight; onComplete: (id: string) => void }) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) {
      onComplete(flight.id);
      return;
    }

    element.style.opacity = '1';
    element.style.transform = 'translate(-50%, -50%) scale(1)';

    let cancelled = false;
    let animation: Animation | null = null;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const dispose = () => {
      cancelled = true;
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
      if (animation) {
        animation.cancel();
      }
    };

    if (typeof window !== 'undefined') {
      const mediaQuery = window.matchMedia?.('(prefers-reduced-motion: reduce)');
      if (mediaQuery?.matches) {
        timeoutId = setTimeout(() => {
          if (!cancelled) {
            onComplete(flight.id);
          }
        }, 1000);

        return dispose;
      }
    }

    const start = () => {
      const deltaX = flight.endX - flight.startX;
      const deltaY = flight.endY - flight.startY;

      animation = element.animate(
        [
          { transform: 'translate(-50%, -50%) scale(1)', opacity: 1 },
          { transform: 'translate(-50%, -50%) scale(1.05)', opacity: 0.92, offset: 0.45 },
          { transform: `translate(-50%, -50%) translate(${deltaX}px, ${deltaY}px) scale(0.9)`, opacity: 0 }
        ],
        {
          duration: 1600,
          easing: 'cubic-bezier(0.2, 0.7, 0.3, 1)',
          fill: 'forwards'
        }
      );

      animation.onfinish = () => {
        if (!cancelled) {
          onComplete(flight.id);
        }
      };
    };

    timeoutId = setTimeout(() => {
      if (!cancelled) {
        start();
      }
    }, 1000);

    return dispose;
  }, [flight, onComplete]);

  const teamClasses = flight.team === 'RED'
    ? 'bg-[#1e0b23]/95 text-[#ffe3ef] border border-[#ff76b2]/55 shadow-[0_0_30px_rgba(255,118,178,0.48)]'
    : 'bg-[#081625]/95 text-[#e7f8ff] border border-[#7bd6ff]/55 shadow-[0_0_30px_rgba(123,214,255,0.44)]';

  return (
    <div
      ref={ref}
      className={`pointer-events-none fixed z-[120] inline-flex items-center gap-3 rounded-2xl px-6 py-3 font-semibold uppercase tracking-[0.2em] text-base backdrop-blur-md [text-shadow:0_0_10px_rgba(0,0,0,0.45)] ${teamClasses}`}
      style={{
        left: `${flight.startX}px`,
        top: `${flight.startY}px`,
        transform: 'translate(-50%, -50%)'
      }}
    >
      <span>{flight.word}</span>
      <span className="text-lg font-bold tracking-[0.18em] text-white/85">{flight.number}</span>
    </div>
  );
}

function CodenamesGame() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [connected, setConnected] = useState(false);
  const [showPrivateThoughts, setShowPrivateThoughts] = useState(true);
  const [paused, setPaused] = useState(false);
  const [gamePaused, setGamePaused] = useState(false); // Actual game pause state from backend
  const [humanMessage, setHumanMessage] = useState('');
  const [selectedAI, setSelectedAI] = useState<string | null>(null);
  const chatEndRef = useRef<null | HTMLDivElement>(null);
  const chatContainerRef = useRef<null | HTMLDivElement>(null);
  const websocketRef = useRef<WebSocket | null>(null);
  const lastUserScrollTime = useRef<number>(0);
  const autoScrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const boardContainerRef = useRef<HTMLDivElement | null>(null);
  const cluePanelRef = useRef<HTMLDivElement | null>(null);
  const lastClueIdRef = useRef<string | null>(null);
  const [clueFlight, setClueFlight] = useState<ClueFlight | null>(null);
  const handleClueFlightComplete = useCallback((id: string) => {
    setClueFlight((current) => (current && current.id === id ? null : current));
  }, []);

  // Smart auto-scroll that respects user reading
  useEffect(() => {
    if (!chatContainerRef.current) return;

    const container = chatContainerRef.current;
    const now = Date.now();
    const timeSinceUserScroll = now - lastUserScrollTime.current;

    // Check if user is at or near the bottom (within 50px)
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;

    // Auto-scroll immediately if user is already at bottom or hasn't scrolled recently
    if (isNearBottom || timeSinceUserScroll > 10000) {
      container.scrollTop = container.scrollHeight;
    } else {
      // User scrolled up recently, delay auto-scroll for 10 seconds
      if (autoScrollTimeoutRef.current) {
        clearTimeout(autoScrollTimeoutRef.current);
      }

      autoScrollTimeoutRef.current = setTimeout(() => {
        if (chatContainerRef.current) {
          chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
      }, 10000 - timeSinceUserScroll);
    }
  }, [gameState?.shared_context]);

  // Track user scroll events
  const handleChatScroll = () => {
    if (!chatContainerRef.current) return;

    const container = chatContainerRef.current;
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;

    // Only update scroll time if user scrolled away from bottom
    if (!isNearBottom) {
      lastUserScrollTime.current = Date.now();
    }

    // Clear pending auto-scroll if user manually scrolled to bottom
    if (isNearBottom && autoScrollTimeoutRef.current) {
      clearTimeout(autoScrollTimeoutRef.current);
      autoScrollTimeoutRef.current = null;
    }
  };

  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8765');
    websocketRef.current = websocket;

    websocket.onopen = () => {
      console.log('Connected to game server');
      setConnected(true);
      websocket.send(JSON.stringify({ command: 'start' }));
    };

    websocket.onmessage = (event) => {
      const state = JSON.parse(event.data);
      setGameState(state);
      // Update the actual game pause state from backend
      if (typeof state.paused === 'boolean') {
        setGamePaused(state.paused);
      }
    };

    websocket.onclose = () => {
      console.log('Disconnected from game server');
      setConnected(false);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      websocket.close();
      websocketRef.current = null;
      if (autoScrollTimeoutRef.current) {
        clearTimeout(autoScrollTimeoutRef.current);
      }
    };
  }, []);

  const togglePause = async () => {
    if (connected) {
      try {
        const command = paused ? 'resume' : 'pause';
        const response = await fetch(`http://localhost:8766/${command}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          setPaused(!paused);
          console.log(`Game ${command}d successfully`);
        } else {
          console.error(`Failed to ${command} game`);
        }
      } catch (error) {
        console.error('Error toggling pause:', error);
      }
    }
  };

  const sendHumanMessage = () => {
    console.log("sendHumanMessage called", { humanMessage, selectedAI, websocketConnected: !!websocketRef.current });

    if (!humanMessage.trim() || !selectedAI || !websocketRef.current) {
      console.log("Validation failed", {
        hasMessage: !!humanMessage.trim(),
        hasSelectedAI: !!selectedAI,
        hasWebSocket: !!websocketRef.current
      });
      return;
    }

    const message = {
      command: 'human_question',
      target_ai: selectedAI,
      message: humanMessage.trim()
    };

    console.log("Sending WebSocket message:", message);
    websocketRef.current.send(JSON.stringify(message));
    setHumanMessage('');
    setSelectedAI(null);
  };

  const getBoardStates = (): CardState[] => {
    // If no board data, create placeholder cards
    if (!gameState?.board) {
      return Array.from({ length: 25 }, () => ({
        word: '•••',
        kind: 'neutral' as const,
        isRevealed: false
      }));
    }

    return gameState.board.map(cell => {
      let kind: 'red' | 'blue' | 'neutral' | 'assassin' = 'neutral';
      if (cell?.team === 'red') kind = 'red';
      else if (cell?.team === 'blue') kind = 'blue';
      else if (cell?.team === 'assassin') kind = 'assassin';

      return {
        word: cell?.text || '•••',
        kind,
        isRevealed: cell?.revealed || false
      };
    });
  };

  const getChatMessageStyle = (msg: ChatMessage) => {
    if (msg.team === 'SYSTEM') return 'text-[#9da3c4] italic';
    if (msg.team === 'RED') return msg.isPrivate ? 'text-[#ffb0cc] italic opacity-70' : 'text-[#ff6ea7]';
    return msg.isPrivate ? 'text-[#a3dbff] italic opacity-70' : 'text-[#63cfff]';
  };

  const remainingCards = useMemo(() => {
    if (!gameState?.board) return null;

    return gameState.board.reduce<{ red: number; blue: number }>((counts, cell) => {
      if (!cell.revealed) {
        if (cell.team === 'red') counts.red += 1;
        else if (cell.team === 'blue') counts.blue += 1;
      }
      return counts;
    }, { red: 0, blue: 0 });
  }, [gameState?.board]);

  const normalizeTeam = (team: string | null | undefined): TeamColor | null => {
    if (!team) return null;
    const lower = team.toLowerCase();
    if (lower.includes('red')) return 'RED';
    if (lower.includes('blue')) return 'BLUE';
    return null;
  };

  const boardWordMap = useMemo(() => {
    const map = new Map<string, string>();
    if (!gameState?.board) return map;

    gameState.board.forEach(card => {
      if (card?.text) {
        map.set(card.text.toLowerCase(), card.text.toUpperCase());
      }
    });

    return map;
  }, [gameState?.board]);

  const { activeClue, activeGuess } = useMemo(() => {
    if (!gameState?.shared_context) {
      return { activeClue: null, activeGuess: null } as {
        activeClue: ActiveClue | null;
        activeGuess: ActiveGuess | null;
      };
    }

    let clue: ActiveClue | null = null;
    let guess: ActiveGuess | null = null;

    const clueRegex = /^([A-Za-z][A-Za-z-]*)\s+(\d+)$/;

    const normalizeToken = (token: string): string => {
      const lower = token.toLowerCase();
      if (boardWordMap.has(lower)) {
        return boardWordMap.get(lower)!;
      }
      return token.toUpperCase();
    };

    const extractGuessWord = (message: string): string | null => {
      const direct = message.match(/I['’]?ll\s+guess\s+([A-Za-z][A-Za-z-]*)/i);
      if (direct) return normalizeToken(direct[1]);

      const generic = message.match(/\bguess\s+([A-Za-z][A-Za-z-]*)/i);
      if (generic) return normalizeToken(generic[1]);

      const tokens = message.match(/[A-Za-z]+/g);
      if (!tokens) return null;

      for (let i = tokens.length - 1; i >= 0; i -= 1) {
        const token = tokens[i];
        if (boardWordMap.has(token.toLowerCase())) {
          return boardWordMap.get(token.toLowerCase())!;
        }
      }

      return null;
    };

    gameState.shared_context.forEach((msg, idx) => {
      if (msg.isPrivate) return;

      const speaker = msg.speaker.toLowerCase();
      const isSpymaster = speaker.includes('spymaster');
      const isGuesser = speaker.includes('guesser');

      if (isSpymaster) {
        const match = msg.message.trim().match(clueRegex);
        const team = msg.team === 'RED' || msg.team === 'BLUE' ? msg.team : null;

        if (match && team) {
          clue = {
            id: `${team}-${idx}`,
            team,
            word: match[1].toUpperCase(),
            number: Number(match[2]),
            chatIndex: idx
          };
          guess = null;
        }
        return;
      }

      if (!clue) return;

      if (isGuesser && msg.team === clue.team) {
        const word = extractGuessWord(msg.message);
        if (word) {
          guess = {
            id: idx,
            team: clue.team,
            word
          };
        }
        return;
      }

      if (msg.team === 'SYSTEM') {
        const result = msg.message.match(/^([A-Za-z][A-Za-z-]*)\s+was\s+/i);
        if (result) {
          guess = null;
        }
      }
    });

    return { activeClue: clue, activeGuess: guess };
  }, [gameState?.shared_context, boardWordMap]);

  const currentTurnTeam = useMemo(() => normalizeTeam(gameState?.current_team), [gameState?.current_team]);

  const finalSummary = useMemo(() => {
    if (!gameState || gameState.phase !== 'ENDED' || !gameState.shared_context) return null;

    let winnerMessage: string | null = null;
    let statsMessage: string | null = null;
    let team: TeamColor | null = null;

    for (let idx = gameState.shared_context.length - 1; idx >= 0; idx -= 1) {
      const msg = gameState.shared_context[idx];
      if (msg.team !== 'SYSTEM') continue;

      if (!statsMessage && /final:/i.test(msg.message)) {
        statsMessage = msg.message;
      }

      if (!winnerMessage && /game over/i.test(msg.message)) {
        winnerMessage = msg.message;
        const match = msg.message.match(/\((red|blue)\)/i);
        if (match) {
          team = match[1].toUpperCase() as TeamColor;
        }
      }

      if (winnerMessage && statsMessage) break;
    }

    if (!winnerMessage && !statsMessage) return null;

    if (team) {
      winnerMessage = `${team} TEAM WINS`;
    } else if (winnerMessage) {
      winnerMessage = winnerMessage.replace(/^[^A-Za-z0-9]+/, '').trim();
    }

    return {
      team,
      winnerMessage,
      statsMessage
    };
  }, [gameState?.phase, gameState?.shared_context]);

  const displayClue = useMemo(() => {
    if (finalSummary || !activeClue) return null;
    if (currentTurnTeam && activeClue.team !== currentTurnTeam) return null;
    return activeClue;
  }, [finalSummary, activeClue, currentTurnTeam]);

  const displayGuess = useMemo(() => {
    if (finalSummary || !displayClue) return null;
    if (!activeGuess || activeGuess.team !== displayClue.team) return null;
    return activeGuess;
  }, [finalSummary, displayClue, activeGuess]);

  useLayoutEffect(() => {
    if (!displayClue) {
      setClueFlight(null);
      lastClueIdRef.current = null;
      return;
    }

    if (displayClue.id === lastClueIdRef.current) {
      return;
    }

    if (typeof window === 'undefined') {
      lastClueIdRef.current = displayClue.id;
      return;
    }

    let frame = 0;
    const measure = () => {
      const boardEl = boardContainerRef.current;
      const clueEl = cluePanelRef.current;

      if (!displayClue) {
        return;
      }

      if (!boardEl || !clueEl) {
        frame = window.requestAnimationFrame(measure);
        return;
      }

      const boardRect = boardEl.getBoundingClientRect();
      const clueRect = clueEl.getBoundingClientRect();

      setClueFlight({
        id: displayClue.id,
        team: displayClue.team,
        word: displayClue.word,
        number: displayClue.number,
        startX: boardRect.left + boardRect.width / 2,
        startY: boardRect.top + boardRect.height / 2,
        endX: clueRect.left + clueRect.width / 2,
        endY: clueRect.top + clueRect.height / 2
      });

      lastClueIdRef.current = displayClue.id;
    };

    frame = window.requestAnimationFrame(measure);

    return () => window.cancelAnimationFrame(frame);
  }, [displayClue]);

  const cardTeam = finalSummary?.team ?? currentTurnTeam ?? (displayClue?.team ?? activeClue?.team ?? null);

  const cardBorderClass = cardTeam === 'RED'
    ? 'border-[#ff76b2]/55 shadow-[0_0_32px_rgba(255,118,178,0.4)]'
    : cardTeam === 'BLUE'
      ? 'border-[#7bd6ff]/55 shadow-[0_0_32px_rgba(123,214,255,0.38)]'
      : 'border-white/14 shadow-[0_0_26px_rgba(132,126,255,0.28)]';

  const clueToneClass = cardTeam === 'RED' ? 'text-[#ffe3ef]' : cardTeam === 'BLUE' ? 'text-[#e7f8ff]' : 'text-[#e5e6ff]';
  const guessChipClass = cardTeam === 'RED'
    ? 'bg-[#30132a]/80 text-[#ffe3ef] border border-[#ff76b2]/45 shadow-[0_0_18px_rgba(255,118,178,0.22)]'
    : cardTeam === 'BLUE'
      ? 'bg-[#0f2334]/80 text-[#e7f8ff] border border-[#7bd6ff]/45 shadow-[0_0_18px_rgba(123,214,255,0.22)]'
      : 'bg-[#181533]/80 text-[#e5e6ff] border border-white/12 shadow-[0_0_15px_rgba(134,126,255,0.18)]';
  const clueInTransit = Boolean(displayClue && clueFlight && clueFlight.id === displayClue.id);
  const guessVisible = !clueInTransit ? displayGuess : null;
  const showAwaitingClue = !displayClue || clueInTransit;

  return (
    <div className="min-h-screen text-white/95 p-6 sm:p-8 lg:p-12">
      {clueFlight && (
        <FloatingClue flight={clueFlight} onComplete={handleClueFlightComplete} />
      )}
      <div className="max-w-full mx-auto">
        {/* Header */}
        <div className="mb-4">
          <h1 className="text-3xl font-bold mb-1">Codenames AI vs AI</h1>
          <div className="flex items-center gap-4">
            <p className="text-gray-400">Delight Nexus Installation</p>
            <div className={`${connected ? 'text-green-400' : 'text-red-400'}`}>
              {connected ? '● Connected' : '○ Disconnected'}
            </div>
            <div className="text-purple-400">
              {gamePaused ? '● Paused' : '● Playing'}
            </div>
          </div>
        </div>

        <div className="flex gap-6 xl:gap-10">
          {/* Main Game Area */}
          <div className="flex-1">
            {gameState && (
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="rounded-2xl border border-[#ff76b2]/35 bg-gradient-to-br from-[#35142d] via-[#4a1b3c] to-[#611f4c] p-4 flex items-center justify-between gap-4 shadow-[0_0_32px_rgba(255,118,178,0.32)]">
                  <div className="text-left">
                    <div className="text-xs uppercase tracking-[0.3em] text-[#ffd0e1]/80">Red Team</div>
                    {gameState.red_team ? (
                      <div className="text-[#fff0f7] text-sm font-semibold drop-shadow-[0_0_12px_rgba(255,159,190,0.45)]">
                        <div><span className="text-[#ff9cc4] text-xs">SPYMASTER:</span> {gameState.red_team.split(' + ')[0]}</div>
                        <div><span className="text-[#ff9cc4] text-xs">GUESSER:</span> {gameState.red_team.split(' + ')[1]}</div>
                      </div>
                    ) : (
                      <h2 className="text-[#fff0f7] text-lg font-semibold">Waiting...</h2>
                    )}
                  </div>
                  <h2 className="text-[#ff9cc4] text-4xl font-bold drop-shadow-[0_0_16px_rgba(255,118,178,0.55)]">
                    {remainingCards ? remainingCards.red : '—'}
                  </h2>
                </div>
                <div className="rounded-2xl border border-[#7bd6ff]/35 bg-gradient-to-br from-[#0f2436] via-[#16374f] to-[#1f4e6c] p-4 flex items-center justify-between gap-4 shadow-[0_0_32px_rgba(123,214,255,0.3)]">
                  <h2 className="text-[#bfefff] text-4xl font-bold drop-shadow-[0_0_16px_rgba(123,214,255,0.5)]">
                    {remainingCards ? remainingCards.blue : '—'}
                  </h2>
                  <div className="text-right">
                    <div className="text-xs uppercase tracking-[0.3em] text-[#d3f3ff]/75">Blue Team</div>
                    {gameState.blue_team ? (
                      <div className="text-[#f2fbff] text-sm font-semibold drop-shadow-[0_0_12px_rgba(123,214,255,0.35)]">
                        <div><span className="text-[#7bd6ff] text-xs">SPYMASTER:</span> {gameState.blue_team.split(' + ')[0]}</div>
                        <div><span className="text-[#7bd6ff] text-xs">GUESSER:</span> {gameState.blue_team.split(' + ')[1]}</div>
                      </div>
                    ) : (
                      <h3 className="text-[#f2fbff] text-lg font-semibold">Waiting...</h3>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Game Board - Always visible */}
            <div className="mb-6" ref={boardContainerRef}>
              <CardGrid states={getBoardStates()} />
            </div>

            {/* Loading State */}
            {!gameState && connected && (
              <div className="text-center py-20">
                <div className="text-2xl text-gray-400">Waiting for game...</div>
              </div>
            )}
          </div>

          {/* Chat Sidebar */}
          <div className="w-96 flex flex-col gap-4">
            <div
              ref={cluePanelRef}
              className={`rounded-2xl border bg-[#140a2e]/75 backdrop-blur-sm p-4 shadow-[0_0_28px_rgba(72,65,115,0.35)] transition ${cardBorderClass}`}
            >
              <div className="relative min-h-[2.5rem] w-full flex flex-wrap items-center gap-3">
                {finalSummary ? (
                  <div className="w-full text-center space-y-2">
                    {finalSummary.winnerMessage && (
                      <div className="text-2xl font-bold uppercase tracking-wide text-white">
                        {finalSummary.winnerMessage}
                      </div>
                    )}
                    {finalSummary.statsMessage && (
                      <div className="text-sm text-gray-300">
                        {finalSummary.statsMessage}
                      </div>
                    )}
                  </div>
                ) : (
                  <>
                    <span
                      className={`absolute left-0 top-1/2 -translate-y-1/2 text-sm ${clueToneClass} transition-opacity duration-700 ease-out ${showAwaitingClue ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
                    >
                      Awaiting clue…
                    </span>
                    {displayClue && (
                      <div
                        className={`flex items-baseline gap-3 transition-all duration-500 ease-out ${clueInTransit ? 'opacity-0 translate-y-1 pointer-events-none' : 'opacity-100 translate-y-0'} relative z-10`}
                      >
                        <span className={`text-xl font-semibold uppercase tracking-wide ${clueToneClass}`}>
                          {displayClue.word}
                        </span>
                        <span className="text-lg font-semibold text-white/90">{displayClue.number}</span>
                      </div>
                    )}
                  </>
                )}
              </div>
              {!finalSummary && (
                <div className="mt-3">
                  {guessVisible ? (
                    <div className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold tracking-wide ${guessChipClass}`}>
                      {guessVisible.word}
                    </div>
                  ) : (
                    <div className="text-xs uppercase tracking-[0.3em] text-white/40">Listening for guesses…</div>
                  )}
                </div>
              )}
            </div>

            <div className="rounded-xl border border-white/10 bg-[#0d0820]/80 backdrop-blur-sm p-4 flex flex-col h-[80vh] shadow-[0_0_25px_rgba(45,35,89,0.35)]">
              <div className="flex justify-between items-center mb-3">
                <h2 className="text-lg font-semibold">Game Chat</h2>
                <button
                  onClick={() => setShowPrivateThoughts(!showPrivateThoughts)}
                  className="text-xs rounded border border-white/10 bg-[#1a1233]/70 px-3 py-1 tracking-wide uppercase text-[10px] text-[#dcd4ff] transition hover:border-white/30 hover:bg-[#241642]"
                >
                  {showPrivateThoughts ? 'Hide' : 'Show'} Private Thoughts
                </button>
              </div>

              <div ref={chatContainerRef} onScroll={handleChatScroll} className="flex-1 overflow-y-auto bg-[#080318]/80 rounded p-3 space-y-3">
                {gameState?.shared_context?.map((msg, idx) => (
                  <div key={idx} className={`${msg.isPrivate && !showPrivateThoughts ? 'hidden' : ''} text-left`}>
                    <div className={`text-xs font-bold mb-2 ${getChatMessageStyle(msg)} uppercase tracking-widest bg-white/5 px-2 py-1 rounded inline-block`}>
                      {msg.speaker}
                    </div>
                    <div className={`text-sm leading-relaxed ${getChatMessageStyle(msg)} ${msg.isPrivate ? 'pl-3 border-l-2 border-white/20 italic' : ''}`}>
                      {msg.isPrivate && '🤔 '}{msg.message}
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />

                {(!gameState?.shared_context || gameState.shared_context.length === 0) && (
                  <div className="text-gray-500 text-center py-8">
                    Game chat will appear here...
                  </div>
                )}
              </div>

              {/* Controls Row 1 - AI Selectors + Pause */}
              {connected && (
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between">
                    {/* AI Selector - only when paused */}
                    {paused ? (
                      <div className="flex items-center gap-3">
                        <div className="text-xs text-[#c2c8ef] font-semibold">Ask:</div>

                        {/* Single Compact AI Selector */}
                        <div className="flex items-center gap-1 px-2 py-1 rounded border border-white/20 bg-[#1a1233]/50">
                          {/* Team Balls */}
                          <button
                            onClick={() => {
                              const currentRole = selectedAI?.includes('spymaster') ? 'spymaster' : 'guesser';
                              setSelectedAI(`red_${currentRole}`);
                            }}
                            className={`w-3 h-3 rounded-full border transition-all ${
                              selectedAI?.includes('red')
                                ? 'bg-[#ff76b2] border-[#ff76b2] shadow-[0_0_8px_rgba(255,118,178,0.6)]'
                                : 'border-[#ff76b2]/40 hover:border-[#ff76b2]/60 hover:bg-[#ff76b2]/20'
                            }`}
                          />
                          <button
                            onClick={() => {
                              const currentRole = selectedAI?.includes('spymaster') ? 'spymaster' : 'guesser';
                              setSelectedAI(`blue_${currentRole}`);
                            }}
                            className={`w-3 h-3 rounded-full border transition-all ${
                              selectedAI?.includes('blue')
                                ? 'bg-[#7bd6ff] border-[#7bd6ff] shadow-[0_0_8px_rgba(123,214,255,0.6)]'
                                : 'border-[#7bd6ff]/40 hover:border-[#7bd6ff]/60 hover:bg-[#7bd6ff]/20'
                            }`}
                          />

                          <span className="text-[10px] text-white/40 mx-1">|</span>

                          {/* Role Toggle */}
                          <button
                            onClick={() => {
                              const currentTeam = selectedAI?.includes('red') ? 'red' : selectedAI?.includes('blue') ? 'blue' : 'red';
                              const newRole = selectedAI?.includes('spymaster') ? 'guesser' : 'spymaster';
                              setSelectedAI(`${currentTeam}_${newRole}`);
                            }}
                            className="text-[10px] font-medium transition-colors hover:text-white"
                          >
                            <span className={selectedAI?.includes('spymaster') ? 'text-white' : 'text-white/60'}>SPY</span>
                            <span className="text-white/40 mx-1">|</span>
                            <span className={selectedAI?.includes('guesser') ? 'text-white' : 'text-white/60'}>GUESS</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div></div>
                    )}

                    <button
                    onClick={togglePause}
                    className={`text-sm rounded border border-white/10 bg-[#1a1233]/70 px-3 py-1 tracking-wide uppercase text-[11px] text-[#dcd4ff] transition hover:border-white/30 hover:bg-[#241642] min-w-[100px] flex items-center justify-center gap-1 ${
                      paused ? 'text-[#a7f3d0] border-green-400/30' : ''
                    }`}
                  >
                    {paused ? (
                      <>
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M8 5v14l11-7z"/>
                        </svg>
                        Resume
                      </>
                    ) : (
                      <>
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                        </svg>
                        Pause
                      </>
                    )}
                  </button>
                </div>

                  {/* Controls Row 2 - Input Box */}
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={humanMessage}
                      onChange={(e) => setHumanMessage(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && humanMessage.trim() && selectedAI && paused) {
                          sendHumanMessage();
                        }
                      }}
                      placeholder={paused ? "Ask an AI..." : "Pause game to ask an AI..."}
                      disabled={!paused || !selectedAI}
                      className="flex-1 px-3 py-2 text-sm bg-[#080318]/80 border border-white/10 rounded text-white placeholder-gray-500 transition-colors focus:border-white/30 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                    <button
                      onClick={sendHumanMessage}
                      disabled={!paused || !humanMessage.trim() || !selectedAI}
                      className="px-3 py-2 text-sm bg-[#1a1233]/70 border border-white/10 rounded text-[#dcd4ff] transition hover:border-white/30 hover:bg-[#241642] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Ask
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CodenamesGame;
