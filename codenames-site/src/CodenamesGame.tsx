import { useState, useEffect, useRef, useMemo } from 'react';
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

function CodenamesGame() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [connected, setConnected] = useState(false);
  const [showPrivateThoughts, setShowPrivateThoughts] = useState(false);
  const chatEndRef = useRef<null | HTMLDivElement>(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [gameState?.shared_context]);

  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8765');

    websocket.onopen = () => {
      console.log('Connected to game server');
      setConnected(true);
      websocket.send(JSON.stringify({ command: 'start' }));
    };

    websocket.onmessage = (event) => {
      const state = JSON.parse(event.data);
      setGameState(state);
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
    };
  }, []);

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
      if (cell.team === 'red') kind = 'red';
      else if (cell.team === 'blue') kind = 'blue';
      else if (cell.team === 'assassin') kind = 'assassin';

      return {
        word: cell.text,
        kind,
        isRevealed: cell.revealed
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
      map.set(card.text.toLowerCase(), card.text.toUpperCase());
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

  const cardTeam = finalSummary?.team ?? currentTurnTeam ?? (displayClue?.team ?? activeClue?.team ?? null);

  const cardBorderClass = cardTeam === 'RED'
    ? 'border-[#ff4f8b]/50 shadow-[0_0_26px_rgba(255,79,139,0.28)]'
    : cardTeam === 'BLUE'
      ? 'border-[#58c6ff]/50 shadow-[0_0_26px_rgba(88,198,255,0.26)]'
      : 'border-white/12 shadow-[0_0_24px_rgba(132,126,255,0.22)]';

  const clueToneClass = cardTeam === 'RED' ? 'text-[#ffd6e4]' : cardTeam === 'BLUE' ? 'text-[#e2f4ff]' : 'text-[#e5e6ff]';
  const guessChipClass = cardTeam === 'RED'
    ? 'bg-[#2b1326]/80 text-[#ffd6e4] border border-[#ff4f8b]/45 shadow-[0_0_18px_rgba(255,79,139,0.22)]'
    : cardTeam === 'BLUE'
      ? 'bg-[#0d2032]/80 text-[#e2f4ff] border border-[#58c6ff]/45 shadow-[0_0_18px_rgba(88,198,255,0.22)]'
      : 'bg-[#181533]/80 text-[#e5e6ff] border border-white/12 shadow-[0_0_15px_rgba(134,126,255,0.18)]';

  return (
    <div className="min-h-screen text-white/95 p-6 sm:p-8 lg:p-12">
      <div className="max-w-full mx-auto">
        {/* Header */}
        <div className="mb-4">
          <h1 className="text-3xl font-bold mb-1">Codenames AI vs AI</h1>
          <div className="flex items-center gap-4">
            <p className="text-gray-400">Delight Nexus Installation</p>
            <div className={`${connected ? 'text-green-400' : 'text-red-400'}`}>
              {connected ? '● Connected' : '○ Disconnected'}
            </div>
          </div>
        </div>

        <div className="flex gap-6 xl:gap-10">
          {/* Main Game Area */}
          <div className="flex-1">
            {gameState && (
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="rounded-2xl border border-[#ff4f8b]/28 bg-gradient-to-br from-[#1f152b] via-[#2a1a34] to-[#3a2142] p-4 flex items-center justify-between gap-4 shadow-[0_0_24px_rgba(255,79,139,0.2)]">
                  <div className="text-left">
                    <div className="text-xs uppercase tracking-[0.3em] text-[#ff9fbe]/75">Red Team</div>
                    <h2 className="text-[#ffe3ef] text-lg font-semibold">{gameState.red_team || 'Waiting...'}</h2>
                  </div>
                  <h2 className="text-[#ffb4cd] text-4xl font-bold drop-shadow-[0_0_12px_rgba(255,79,139,0.35)]">
                    {remainingCards ? remainingCards.red : '—'}
                  </h2>
                </div>
                <div className="rounded-2xl border border-[#58c6ff]/28 bg-gradient-to-br from-[#0e1b2c] via-[#14273a] to-[#1f3a50] p-4 flex items-center justify-between gap-4 shadow-[0_0_24px_rgba(88,198,255,0.2)]">
                  <h2 className="text-[#b9e9ff] text-4xl font-bold drop-shadow-[0_0_12px_rgba(88,198,255,0.35)]">
                    {remainingCards ? remainingCards.blue : '—'}
                  </h2>
                  <div className="text-right">
                    <div className="text-xs uppercase tracking-[0.3em] text-[#8fdcff]/65">Blue Team</div>
                    <h3 className="text-[#effaff] text-lg font-semibold">{gameState.blue_team || 'Waiting...'}</h3>
                  </div>
                </div>
              </div>
            )}

            {/* Game Board - Always visible */}
            <div className="mb-6">
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
            <div className={`rounded-xl border bg-[#140a2e]/85 backdrop-blur-sm p-4 shadow-lg shadow-black/30 ${cardBorderClass}`}>
              <div className="flex flex-wrap items-baseline gap-3">
                {displayClue ? (
                  <>
                    <span className={`text-xl font-semibold uppercase tracking-wide ${clueToneClass}`}>
                      {displayClue.word}
                    </span>
                    <span className="text-lg font-semibold text-white/80">{displayClue.number}</span>
                  </>
                ) : finalSummary ? (
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
                  <span className={`text-sm ${clueToneClass}`}>Awaiting clue…</span>
                )}
              </div>
              {!finalSummary && (
                <div className="mt-3">
                  {displayGuess ? (
                    <div className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold tracking-wide ${guessChipClass}`}>
                      {displayGuess.word}
                    </div>
                  ) : (
                    <div className="text-sm text-gray-500 italic">No guess yet</div>
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

              <div className="flex-1 overflow-y-auto bg-[#080318]/80 rounded p-3 space-y-2">
                {gameState?.shared_context?.map((msg, idx) => (
                  <div key={idx} className={`${msg.isPrivate && !showPrivateThoughts ? 'hidden' : ''}`}>
                    <div className={`text-xs ${getChatMessageStyle(msg)}`}>
                      {msg.speaker}
                    </div>
                    <div className={`text-sm ${getChatMessageStyle(msg)} ${msg.isPrivate ? 'pl-4' : ''}`}>
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
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CodenamesGame;
