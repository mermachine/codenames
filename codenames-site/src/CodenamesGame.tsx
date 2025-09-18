import { useState, useEffect } from 'react';
import { CardGrid, type CardState } from './components/CardGrid';

type GamePhase = 'STARTING' | 'THINKING' | 'GUESSING' | 'ENDED';

interface GameState {
  phase: GamePhase;
  last_action: string;
  last_reasoning: string;
  total_games: number;
  current_team: string | null;
  board: string[][] | null;
  game_state: any;
  red_team: string | null;
  blue_team: string | null;
}

function CodenamesGame() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [connected, setConnected] = useState(false);
  

  useEffect(() => {
    // Connect to WebSocket server
    const websocket = new WebSocket('ws://localhost:8765');

    websocket.onopen = () => {
      console.log('Connected to game server');
      setConnected(true);
      // Start a new game
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

  // Convert board state to CardGrid format
  const getBoardStates = (): CardState[][] => {
    if (!gameState?.board) return [];

    return gameState.board.map(row =>
      row.map(cell => {
        // Parse the cell string to determine state
        const isRevealed = cell.includes('[') && cell.includes(']');
        const word = isRevealed
          ? cell.substring(0, cell.indexOf('[')).trim()
          : cell.trim();

        let kind: 'red' | 'blue' | 'neutral' | 'assassin' = 'neutral';
        if (isRevealed) {
          if (cell.includes('RED')) kind = 'red';
          else if (cell.includes('BLUE')) kind = 'blue';
          else if (cell.includes('ASSASSIN')) kind = 'assassin';
        }

        return {
          word,
          kind,
          isRevealed
        };
      })
    );
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

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Codenames AI vs AI</h1>
          <p className="text-gray-400">
            Delight Nexus Installation 
          </p>
          <div className={`mt-2 ${connected ? 'text-green-400' : 'text-red-400'}`}>
            {connected ? '● Connected' : '○ Disconnected'}
          </div>
        </div>

        {gameState && (
          <>
            {/* Game Info Bar */}
            <div className="bg-gray-800 rounded-lg p-4 mb-6">
              <div className="flex justify-between items-center">
                <div>
                  <span className="text-gray-400">Phase: </span>
                  <span className={getPhaseColor(gameState.phase)}>
                    {gameState.phase}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Current Team: </span>
                  <span className={getTeamColor(gameState.current_team)}>
                    {gameState.current_team || 'Starting...'}
                  </span>
                </div>
                <div className="text-gray-400">
                  Games Played: {gameState.total_games}
                </div>
              </div>
            </div>

            {/* Teams */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-red-900 bg-opacity-30 rounded-lg p-4">
                <h3 className="text-red-400 font-semibold mb-2">Red Team</h3>
                <p>{gameState.red_team || 'Waiting...'}</p>
              </div>
              <div className="bg-blue-900 bg-opacity-30 rounded-lg p-4">
                <h3 className="text-blue-400 font-semibold mb-2">Blue Team</h3>
                <p>{gameState.blue_team || 'Waiting...'}</p>
              </div>
            </div>

            {/* Game Board */}
            {gameState.board && (
              <div className="mb-6">
                <CardGrid states={getBoardStates()} />
              </div>
            )}

            {/* Current Action */}
            <div className="bg-gray-800 rounded-lg p-4 mb-4">
              <h3 className="text-lg font-semibold mb-2">Current Action</h3>
              <p className="text-yellow-200">{gameState.last_action}</p>
            </div>

            {/* AI Reasoning */}
            {gameState.last_reasoning && (
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-2">AI Reasoning</h3>
                <p className="text-gray-300 whitespace-pre-wrap">
                  {gameState.last_reasoning}
                </p>
              </div>
            )}
          </>
        )}

        {/* Loading State */}
        {!gameState && connected && (
          <div className="text-center py-20">
            <div className="text-2xl text-gray-400">Waiting for game to start...</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default CodenamesGame;