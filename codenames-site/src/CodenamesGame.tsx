import { useState, useEffect, useRef } from 'react';
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

  const getPhaseColor = (phase: GamePhase) => {
    switch (phase) {
      case 'THINKING': return 'text-yellow-400';
      case 'GUESSING': return 'text-blue-400';
      case 'ENDED': return 'text-green-400';
      default: return 'text-gray-400';
    }
  };

  const getTeamColor = (team: string | null) => {
    if (!team) return '';
    return team.toLowerCase().includes('red') ? 'text-red-500' : 'text-blue-500';
  };

  const getChatMessageStyle = (msg: ChatMessage) => {
    if (msg.team === 'SYSTEM') return 'text-gray-400 italic';
    if (msg.team === 'RED') return msg.isPrivate ? 'text-red-300 italic opacity-70' : 'text-red-400';
    return msg.isPrivate ? 'text-blue-300 italic opacity-70' : 'text-blue-400';
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
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

        <div className="flex gap-4">
          {/* Main Game Area */}
          <div className="flex-1">
            {/* Game Board - Always visible */}
            <div className="mb-4">
              <CardGrid states={getBoardStates()} />
            </div>

            {gameState && (
              <>
                {/* Game Info Bar */}
                <div className="bg-gray-800 rounded-lg p-3 mb-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="text-gray-400">Phase: </span>
                      <span className={getPhaseColor(gameState.phase)}>
                        {gameState.phase}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">Turn: </span>
                      <span className={getTeamColor(gameState.current_team)}>
                        {gameState.current_team || 'Starting...'}
                      </span>
                    </div>
                    <div className="text-gray-400">
                      Games: {gameState.total_games}
                    </div>
                  </div>
                </div>

                {/* Teams */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-red-900 bg-opacity-30 rounded-lg p-3">
                    <h3 className="text-red-400 font-semibold">Red Team</h3>
                    <p className="text-sm">{gameState.red_team || 'Waiting...'}</p>
                  </div>
                  <div className="bg-blue-900 bg-opacity-30 rounded-lg p-3">
                    <h3 className="text-blue-400 font-semibold">Blue Team</h3>
                    <p className="text-sm">{gameState.blue_team || 'Waiting...'}</p>
                  </div>
                </div>
              </>
            )}

            {/* Loading State */}
            {!gameState && connected && (
              <div className="text-center py-20">
                <div className="text-2xl text-gray-400">Waiting for game...</div>
              </div>
            )}
          </div>

          {/* Chat Sidebar */}
          <div className="w-96 bg-gray-800 rounded-lg p-4 flex flex-col h-[80vh]">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-lg font-semibold">Game Chat</h2>
              <button
                onClick={() => setShowPrivateThoughts(!showPrivateThoughts)}
                className="text-xs bg-gray-700 px-2 py-1 rounded hover:bg-gray-600"
              >
                {showPrivateThoughts ? 'Hide' : 'Show'} Private Thoughts
              </button>
            </div>

            <div className="flex-1 overflow-y-auto bg-gray-900 rounded p-3 space-y-2">
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
  );
}

export default CodenamesGame;
