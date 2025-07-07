from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
import json
from typing import Any, Dict, List, Union

from inspect_ai.model import ChatMessage


@dataclass
class PuzzleContext:
    """Tracks the state and progress of a puzzle solving session across multiple turns.

    Attributes:
        puzzle_state: Current state of the puzzle as a string representation
        turn_count: Number of interaction turns completed
        total_moves: Total number of moves attempted (valid and invalid)
        invalid_turns: Number of turns that resulted in invalid moves
        successful_moves: Number of moves that were successfully applied
        state_history: List of states for loop detection
        recent_invalid_attempts: List of recent invalid move attempts for pattern detection
    """

    turn_count: int = 0
    total_moves: int = 0
    invalid_turns: int = 0
    successful_moves: int = 0
    recent_invalid_attempts: List[str] = field(default_factory=list)
    full_conversation_history: List[ChatMessage] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PuzzleContext":
        return cls(**data)


@dataclass
class CompletionResult:
    """Contains the final results and metrics from a completed puzzle solving session.

    Attributes:
        solved: Whether the puzzle was successfully solved
        termination_reason: Reason why the solving session ended
        turns_taken: Number of interaction turns used
        total_moves_attempted: Total number of moves attempted
        invalid_turns: Number of turns with invalid moves
        successful_moves: Number of moves successfully applied
        puzzle_size: Size/difficulty of the puzzle (e.g., number of disks)
    """

    solved: bool
    termination_reason: str
    turns_taken: int
    total_moves_attempted: int
    invalid_turns: int
    successful_moves: int
    puzzle_size: int

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> "CompletionResult":
        data = json.loads(json_str)
        # Only keep keys that are fields of the dataclass to ignore extra fields from input
        allowed_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in allowed_keys}
        return cls(**filtered_data)


@dataclass
class InvalidMoveError:
    """Represents an invalid move attempt with detailed error information.

    Attributes:
        move_index: The index of the invalid move in the submitted move list
        move: The actual move that was invalid
        reason: Human-readable explanation of why the move was invalid
    """

    move_index: int
    move: str
    reason: str

    def __str__(self) -> str:
        return f'Invalid move "{self.move}" at index {self.move_index}: {self.reason}'


class PuzzleInterface(ABC):
    """Abstract base class defining the interface for puzzle implementations.
    """

    @abstractmethod
    def size(self) -> int:
        """Return the size of the puzzle.
        """

    @abstractmethod
    def get_state(self) -> str:
        """Get the current puzzle state as a string.
        """

    @abstractmethod
    def apply_moves(self, moves: List[Any]) -> Union[str, InvalidMoveError]:
        """Apply a list of moves to the current puzzle state.

        Args:
            moves: List of moves to apply

        Returns:
            New state string if all moves are valid, or InvalidMoveError for the first invalid move
        """

    @abstractmethod
    def is_solved(self) -> bool:
        """Check if the puzzle is in a solved state.
        """

    @abstractmethod
    def parse_moves(self, llm_output: str) -> List[Any]:
        """Parse LLM output into a list of moves.

        Returns:
            List of parsed moves, where each move is a list of integers
        """

    @abstractmethod
    def get_move_format(self) -> str:
        """Return a string describing the expected move format.
        """

    @abstractmethod
    def get_optimal_move_count(self) -> int:
        """Return the minimum number of moves required to solve the puzzle.
        """

    @abstractmethod
    def get_state_history(self) -> List[str]:
        """Return the history of states for loop detection."""
