import json
import logging
from typing import Any, Dict, List
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

class MockModel:
    """Mock model that generates predictable responses for testing."""

    def __init__(self, optimal: bool = True, deterministic: bool = True):
        """Initialize mock model with simple configuration.

        Args:
            optimal: Whether to use optimal solving strategy
            deterministic: Whether responses should be deterministic
        """
        self.optimal = optimal
        self.deterministic = deterministic
        self.move_history: List[List[int]] = []
        self.turn_count = 0
        self.puzzle_size = 3

        # Optimal solution for 3-disk Tower of Hanoi (7 moves)
        self.optimal_solution = [
            [1, 0, 2],  # Move disk 1 from peg 0 to peg 2
            [2, 0, 1],  # Move disk 2 from peg 0 to peg 1
            [1, 2, 1],  # Move disk 1 from peg 2 to peg 1
            [3, 0, 2],  # Move disk 3 from peg 0 to peg 2
            [1, 1, 0],  # Move disk 1 from peg 1 to peg 0
            [2, 1, 2],  # Move disk 2 from peg 1 to peg 2
            [1, 0, 2]   # Move disk 1 from peg 0 to peg 2
        ]

        logger.info(f"Initialized MockModel with optimal={optimal}, deterministic={deterministic}")

    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a response based on the conversation history.

        Args:
            messages: List of conversation messages
            **kwargs: Additional generation parameters

        Returns:
            Mock model response string
        """
        self.turn_count += 1
        logger.debug(f"Generating response for turn {self.turn_count}")

        # Generate moves based on strategy
        if self.optimal and self.puzzle_size == 3:
            moves = self._generate_optimal_moves()
        else:
            moves = self._generate_basic_moves()

        # Format response as JSON
        if moves:
            return json.dumps(moves)
        else:
            return "[]"

    def _generate_optimal_moves(self) -> List[List[int]]:
        """Generate optimal moves for N=3 puzzle."""
        if len(self.move_history) < len(self.optimal_solution):
            # Return next move from optimal solution
            next_move = self.optimal_solution[len(self.move_history)]
            self.move_history.append(next_move)
            return [next_move]
        else:
            # Puzzle should be solved by now
            return []

    def _generate_basic_moves(self) -> List[List[int]]:
        """Generate basic valid moves."""
        # Simple strategy: move smallest disk available
        if self.turn_count <= 7:  # Reasonable number of moves
            disk = 1
            from_peg = (self.turn_count - 1) % 3
            to_peg = (self.turn_count) % 3
            return [[disk, from_peg, to_peg]]
        else:
            return []


class MockGenerate:
    """Mock generate function for testing solver integration."""

    def __init__(self, mock_model: MockModel):
        """Initialize with a mock model.

        Args:
            mock_model: MockModel instance to use for generation
        """
        self.mock_model = mock_model

    async def __call__(self, state) -> Any:
        """Generate mock response and update state.

        Args:
            state: TaskState object to update

        Returns:
            Updated state object
        """
        # Extract messages from state
        messages = []
        if hasattr(state, "messages") and state.messages:
            for msg in state.messages:
                if hasattr(msg, "content"):
                    # Determine message role based on type
                    msg_type = type(msg).__name__.lower()
                    if "system" in msg_type:
                        role = "system"
                    elif "user" in msg_type:
                        role = "user"
                    else:
                        role = "assistant"

                    messages.append({
                        "role": role,
                        "content": msg.content
                    })

        # Generate response
        response = self.mock_model.generate_response(messages)

        # Update state output
        if not hasattr(state, "output"):
            state.output = MagicMock()
        state.output.completion = response

        return state


class MockTaskState:
    """Mock TaskState for testing."""

    def __init__(self, puzzle_size: int = 3):
        """Initialize mock task state.

        Args:
            puzzle_size: Size of the puzzle
        """
        self.metadata = {
            "n": puzzle_size,
            "puzzle_type": "tower_of_hanoi",
            "optimal_moves": 2**puzzle_size - 1
        }
        self.messages = []
        self.output = MagicMock()
        self.output.completion = ""


def create_deterministic_model(puzzle_size: int = 3, optimal: bool = True) -> MockModel:
    """Create a deterministic mock model for testing.

    Args:
        puzzle_size: Size of puzzle to solve
        optimal: Whether to use optimal solving strategy

    Returns:
        Configured MockModel instance
    """
    model = MockModel(optimal=optimal, deterministic=True)
    model.puzzle_size = puzzle_size
    return model


def create_mock_conversation(puzzle_size: int = 3) -> List[Dict[str, str]]:
    """Create a mock conversation for testing.

    Args:
        puzzle_size: Size of puzzle for the conversation

    Returns:
        List of mock conversation messages
    """
    initial_state = f"Peg 0: {', '.join(str(i) for i in range(puzzle_size, 0, -1))}\nPeg 1: (empty)\nPeg 2: (empty)"

    return [
        {
            "role": "system",
            "content": "You are solving Tower of Hanoi puzzles."
        },
        {
            "role": "user",
            "content": f"Initial state: {initial_state}\nFormat: [[disk_id, from_peg, to_peg], ...]"
        },
        {
            "role": "assistant",
            "content": "[[1, 0, 2]]"
        },
        {
            "role": "user",
            "content": f"Current state: Peg 0: {', '.join(str(i) for i in range(puzzle_size, 1, -1))}\nPeg 1: (empty)\nPeg 2: 1\nProgress: Turn 1, 1 moves successful"
        }
    ]


if __name__ == "__main__":
    # Test the mock model
    model = create_deterministic_model(3, optimal=True)

    # Test conversation
    messages = create_mock_conversation(3)

    for i in range(5):
        response = model.generate_response(messages)
        print(f"Turn {i+1}: {response}")

        # Add response to conversation
        messages.append({"role": "assistant", "content": response})

        # Simulate next user message
        if response != "[]":
            messages.append({
                "role": "user",
                "content": f"Turn {i+2}: Continue solving..."
            })
        else:
            break
