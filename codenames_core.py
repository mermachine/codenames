"""
Codenames Core Game Logic
For the Delight Nexus - Saving Sonnet 3.6
"""

import random
from typing import List, Tuple, Dict, Optional
from enum import Enum
from dataclasses import dataclass

class Team(Enum):
    RED = "red"
    BLUE = "blue"
    NEUTRAL = "neutral"
    ASSASSIN = "assassin"

@dataclass
class Word:
    text: str
    team: Team
    revealed: bool = False

@dataclass
class Clue:
    word: str
    number: int
    reasoning: Optional[str] = None  # AI's internal reasoning for transparency

class CodenamesGame:
    def __init__(self, words_list: List[str], seed: Optional[int] = None):
        """Initialize a Codenames game with 25 words"""
        if seed:
            random.seed(seed)

        # Select 25 random words
        self.words = random.sample(words_list, 25)

        # Assign teams (9-8-7-1 distribution)
        # Starting team gets 9 words
        starting_team = random.choice([Team.RED, Team.BLUE])
        other_team = Team.BLUE if starting_team == Team.RED else Team.RED

        team_assignments = (
            [starting_team] * 9 +
            [other_team] * 8 +
            [Team.NEUTRAL] * 7 +
            [Team.ASSASSIN] * 1
        )
        random.shuffle(team_assignments)

        # Create the board
        self.board = []
        for i in range(25):
            self.board.append(Word(
                text=self.words[i],
                team=team_assignments[i],
                revealed=False
            ))

        self.starting_team = starting_team
        self.current_team = starting_team
        self.game_over = False
        self.winner = None
        self.turn_history = []

    def get_board_display(self, spymaster: bool = False) -> List[List[str]]:
        """Get 5x5 board for display"""
        display = []
        for i in range(5):
            row = []
            for j in range(5):
                word = self.board[i * 5 + j]
                if spymaster and not word.revealed:
                    # Show color coding for spymaster
                    row.append(f"{word.text}[{word.team.value[0].upper()}]")
                elif word.revealed:
                    row.append(f"{word.text}✓")
                else:
                    row.append(word.text)
            display.append(row)
        return display

    def get_remaining_words(self, team: Team) -> List[str]:
        """Get list of unrevealed words for a team"""
        return [w.text for w in self.board if w.team == team and not w.revealed]

    def give_clue(self, clue: Clue):
        """Record a clue given by spymaster"""
        self.turn_history.append({
            'team': self.current_team,
            'clue': clue,
            'guesses': []
        })

    def make_guess(self, word_text: str) -> Tuple[bool, str]:
        """
        Make a guess for a word
        Returns (continue_turn, result_message)
        """
        word = next((w for w in self.board if w.text.lower() == word_text.lower()), None)

        if not word:
            return False, "Word not found on board"

        if word.revealed:
            return False, "Word already revealed"

        word.revealed = True
        self.turn_history[-1]['guesses'].append(word_text)

        # Check results
        if word.team == Team.ASSASSIN:
            self.game_over = True
            self.winner = Team.BLUE if self.current_team == Team.RED else Team.RED
            return False, f"ASSASSIN! {self.winner.value} team wins!"

        if word.team == self.current_team:
            # Check for victory
            if not self.get_remaining_words(self.current_team):
                self.game_over = True
                self.winner = self.current_team
                return False, f"All words found! {self.winner.value} team wins!"
            return True, f"Correct! {word.text} was {word.team.value}"

        # Wrong team or neutral
        return False, f"{word.text} was {word.team.value}. Turn ends."

    def end_turn(self):
        """Switch to other team"""
        self.current_team = Team.BLUE if self.current_team == Team.RED else Team.RED

    def get_game_state(self) -> Dict:
        """Get current game state for AI analysis"""
        return {
            'current_team': self.current_team.value,
            'remaining_red': len(self.get_remaining_words(Team.RED)),
            'remaining_blue': len(self.get_remaining_words(Team.BLUE)),
            'revealed_words': [w.text for w in self.board if w.revealed],
            'turn_history': self.turn_history,
            'game_over': self.game_over,
            'winner': self.winner.value if self.winner else None
        }