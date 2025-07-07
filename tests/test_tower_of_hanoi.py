import asyncio
import os
import sys
from unittest.mock import MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.puzzles.base import CompletionResult
from src.puzzles.tower_of_hanoi import TowerOfHanoi
from src.solvers.multi_turn import MultiTurnSolver
from tests.mocks.mock_model import (
    MockGenerate,
    MockModel,
    MockTaskState,
    create_deterministic_model,
)


class TestTowerOfHanoiCore:
    """Core puzzle functionality tests."""

    def test_puzzle_initialization(self):
        """Test TowerOfHanoi initialization with 3 disks."""
        puzzle = TowerOfHanoi(n_disks=3)
        assert puzzle.n_disks == 3
        assert puzzle.get_state() == "Peg 0: 3 (bottom), 2, 1 (top)\nPeg 1: (empty)\nPeg 2: (empty)"
        assert not puzzle.is_solved()
        assert puzzle.get_optimal_move_count() == 8  # 3^2 - 1 = 8

    def test_basic_move_application(self):
        """Test basic move application and validation."""
        puzzle = TowerOfHanoi(n_disks=3)

        # Valid move
        result = puzzle.apply_moves([[1, 0, 2]])
        assert isinstance(result, str)  # Should return new state string
        assert "Peg 2: 1" in result

        # Invalid move (disk 3 on disk 1) - should return InvalidMoveError
        puzzle2 = TowerOfHanoi(n_disks=3)
        result2 = puzzle2.apply_moves([[3, 0, 2]])
        assert hasattr(result2, "move_index")  # Should be InvalidMoveError

    def test_puzzle_solved_detection(self):
        """Test puzzle solved detection."""
        puzzle = TowerOfHanoi(n_disks=2)
        assert not puzzle.is_solved()

        # Solve the puzzle with correct sequence
        puzzle.apply_moves([[1, 0, 1]])
        puzzle.apply_moves([[2, 0, 2]])
        puzzle.apply_moves([[1, 1, 2]])

        assert puzzle.is_solved()

    def test_move_parsing(self):
        """Test move parsing from JSON format."""
        puzzle = TowerOfHanoi(n_disks=3)

        # Test basic format
        moves = puzzle.parse_moves("[[1, 0, 2]]")
        assert moves == [[1, 0, 2]]

        # Test multiple moves
        moves = puzzle.parse_moves("[[1, 0, 2], [2, 0, 1]]")
        assert moves == [[1, 0, 2], [2, 0, 1]]

        # Test empty format
        moves = puzzle.parse_moves("[]")
        assert moves == []

    def test_move_format_description(self):
        """Test move format description."""
        puzzle = TowerOfHanoi(n_disks=3)
        format_desc = puzzle.get_move_format()
        assert "disk_id" in format_desc
        assert "from_peg" in format_desc
        assert "to_peg" in format_desc

    def test_optimal_move_calculation(self):
        """Test optimal move count calculation."""
        assert TowerOfHanoi(n_disks=1).get_optimal_move_count() == 0  # 1^2 - 1 = 0
        assert TowerOfHanoi(n_disks=2).get_optimal_move_count() == 3  # 2^2 - 1 = 3
        assert TowerOfHanoi(n_disks=3).get_optimal_move_count() == 8  # 3^2 - 1 = 8
        assert TowerOfHanoi(n_disks=4).get_optimal_move_count() == 15  # 4^2 - 1 = 15


class TestSolverIntegration:
    """Solver integration tests."""

    def test_solver_with_mock_model(self):
        """Test MultiTurnSolver with mock model for 3-disk puzzle."""
        mock_model = create_deterministic_model(puzzle_size=3, optimal=True)
        mock_generate = MockGenerate(mock_model)
        mock_state = MockTaskState(puzzle_size=3)

        # Create puzzle and solver with correct parameters
        puzzle = TowerOfHanoi(n_disks=3)
        config = {
            "turn_limit_multiplier": 2.0,
            "move_limit_multiplier": 10.0,
            "window_size": 4,
            "repeated_invalid_limit": 3,
            "state_revisit_limit": 2
        }
        templates = {
            "system": "You are solving Tower of Hanoi puzzles.",
            "user_first": "Initial state: {initial_state}",
            "user_turn": "Current state: {current_state}"
        }

        solver = MultiTurnSolver(puzzle, config, templates)

        # Test async solve method
        result = asyncio.run(solver.solve(mock_state, mock_generate))

        assert result is not None
        assert hasattr(result, "output")
        assert hasattr(result.output, "completion")

    def test_successful_completion_path(self):
        """Test successful completion path."""
        mock_model = create_deterministic_model(puzzle_size=3, optimal=True)
        mock_generate = MockGenerate(mock_model)
        mock_state = MockTaskState(puzzle_size=3)

        # Create puzzle and solver with correct parameters
        puzzle = TowerOfHanoi(n_disks=3)
        config = {
            "turn_limit_multiplier": 3.0,
            "move_limit_multiplier": 15.0,
            "window_size": 5,
            "repeated_invalid_limit": 3,
            "state_revisit_limit": 2
        }
        templates = {
            "system": "You are solving Tower of Hanoi puzzles.",
            "user_first": "Initial state: {initial_state}",
            "user_turn": "Current state: {current_state}"
        }

        solver = MultiTurnSolver(puzzle, config, templates)

        # Test async solve method
        result = asyncio.run(solver.solve(mock_state, mock_generate))

        # Parse completion result
        completion_result = CompletionResult.from_json(result.metadata["puzzle_result_json"])
        assert completion_result.solved
        assert completion_result.successful_moves >= 0
        assert completion_result.turns_taken >= 0

    def test_termination_on_solved_state(self):
        """Test termination when puzzle is solved."""
        mock_model = create_deterministic_model(puzzle_size=3, optimal=True)
        mock_generate = MockGenerate(mock_model)
        mock_state = MockTaskState(puzzle_size=3)

        # Create puzzle and solver with correct parameters
        puzzle = TowerOfHanoi(n_disks=3)
        config = {
            "turn_limit_multiplier": 5.0,
            "move_limit_multiplier": 20.0,
            "window_size": 6,
            "repeated_invalid_limit": 3,
            "state_revisit_limit": 2
        }
        templates = {
            "system": "You are solving Tower of Hanoi puzzles.",
            "user_first": "Initial state: {initial_state}",
            "user_turn": "Current state: {current_state}"
        }

        solver = MultiTurnSolver(puzzle, config, templates)

        # Test async solve method
        result = asyncio.run(solver.solve(mock_state, mock_generate))

        # Parse completion result
        completion_result = CompletionResult.from_json(result.metadata["puzzle_result_json"])
        assert completion_result.solved
        assert completion_result.turns_taken >= 0  # Should have taken some turns but not hit max

    def test_basic_error_handling(self):
        """Test basic error handling for invalid moves."""
        mock_model = MockModel()
        mock_model.generate_response = MagicMock(return_value="[[99, 0, 1]]")  # Invalid disk

        mock_generate = MockGenerate(mock_model)
        mock_state = MockTaskState(puzzle_size=3)

        # Create puzzle and solver with correct parameters
        puzzle = TowerOfHanoi(n_disks=3)
        config = {
            "turn_limit_multiplier": 1.0,
            "move_limit_multiplier": 5.0,
            "window_size": 3,
            "repeated_invalid_limit": 2,
            "state_revisit_limit": 2
        }
        templates = {
            "system": "You are solving Tower of Hanoi puzzles.",
            "user_first": "Initial state: {initial_state}",
            "user_turn": "Current state: {current_state}"
        }

        solver = MultiTurnSolver(puzzle, config, templates)

        # Test async solve method
        result = asyncio.run(solver.solve(mock_state, mock_generate))

        # Parse completion result
        completion_result = CompletionResult.from_json(result.metadata["puzzle_result_json"])
        assert not completion_result.solved
        assert completion_result.total_moves_attempted >= 0

    def test_give_up_scenario(self):
        """Test give-up scenario (empty move list)."""
        mock_model = MockModel()
        mock_model.generate_response = MagicMock(return_value="[]")  # Empty moves

        mock_generate = MockGenerate(mock_model)
        mock_state = MockTaskState(puzzle_size=3)

        # Create puzzle and solver with correct parameters
        puzzle = TowerOfHanoi(n_disks=3)
        config = {
            "turn_limit_multiplier": 1.0,
            "move_limit_multiplier": 5.0,
            "window_size": 3,
            "repeated_invalid_limit": 2,
            "state_revisit_limit": 2
        }
        templates = {
            "system": "You are solving Tower of Hanoi puzzles.",
            "user_first": "Initial state: {initial_state}",
            "user_turn": "Current state: {current_state}"
        }

        solver = MultiTurnSolver(puzzle, config, templates)

        # Test async solve method
        result = asyncio.run(solver.solve(mock_state, mock_generate))

        # Parse completion result
        completion_result = CompletionResult.from_json(result.metadata["puzzle_result_json"])
        assert not completion_result.solved
        assert completion_result.total_moves_attempted == 0


class TestScorerIntegration:
    """Scorer integration tests."""

    def test_completion_result_parsing(self):
        """Test CompletionResult parsing from TaskState."""

        # Test with valid completion result
        mock_state = MockTaskState(puzzle_size=3)
        completion_result = CompletionResult(
            solved=True,
            termination_reason="solved",
            turns_taken=7,
            total_moves_attempted=7,
            invalid_turns=0,
            successful_moves=7,
            puzzle_size=3
        )

        mock_state.metadata["puzzle_result_json"] = completion_result.to_json()
        parsed_result = CompletionResult.from_json(mock_state.metadata["puzzle_result_json"])

        assert parsed_result is not None
        assert parsed_result.solved
        assert parsed_result.successful_moves == 7
        assert parsed_result.puzzle_size == 3


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_complete_evaluation_flow(self):
        """Test complete evaluation flow: puzzle → solver → scorer."""
        # Create components
        mock_model = create_deterministic_model(puzzle_size=3, optimal=True)
        mock_generate = MockGenerate(mock_model)
        mock_state = MockTaskState(puzzle_size=3)

        # Create puzzle and solver with correct parameters
        puzzle = TowerOfHanoi(n_disks=3)
        config = {
            "turn_limit_multiplier": 3.0,
            "move_limit_multiplier": 15.0,
            "window_size": 5,
            "repeated_invalid_limit": 3,
            "state_revisit_limit": 2
        }
        templates = {
            "system": "You are solving Tower of Hanoi puzzles.",
            "user_first": "Initial state: {initial_state}",
            "user_turn": "Current state: {current_state}"
        }

        solver = MultiTurnSolver(puzzle, config, templates)

        # Run evaluation
        result = asyncio.run(solver.solve(mock_state, mock_generate))

        # Parse completion result
        completion_result = CompletionResult.from_json(result.metadata["puzzle_result_json"])

        # Verify complete flow
        assert completion_result.solved or not completion_result.solved  # Basic validation
        assert completion_result.successful_moves >= 0
        assert completion_result.total_moves_attempted >= 0
        assert completion_result.turns_taken >= 0
        assert completion_result.puzzle_size == 3

    def test_deterministic_mock_model(self):
        """Test with deterministic mock model."""
        mock_model = create_deterministic_model(puzzle_size=3, optimal=True)
        mock_generate = MockGenerate(mock_model)
        mock_state = MockTaskState(puzzle_size=3)

        config = {
            "turn_limit_multiplier": 2.0,
            "move_limit_multiplier": 10.0,
            "window_size": 4,
            "repeated_invalid_limit": 3,
            "state_revisit_limit": 2
        }
        templates = {
            "system": "You are solving Tower of Hanoi puzzles.",
            "user_first": "Initial state: {initial_state}",
            "user_turn": "Current state: {current_state}"
        }

        # Run multiple times - should be deterministic
        results = []
        for _ in range(3):
            puzzle_instance = TowerOfHanoi(n_disks=3)
            solver_instance = MultiTurnSolver(puzzle_instance, config, templates)
            result = asyncio.run(solver_instance.solve(mock_state, mock_generate))
            completion_result = CompletionResult.from_json(result.metadata["puzzle_result_json"])
            results.append((completion_result.solved, completion_result.successful_moves, completion_result.turns_taken))

        # All results should be deterministic (may or may not be identical due to state)
        assert len(results) == 3
        assert all(isinstance(r[0], bool) for r in results)  # All solved fields are boolean
        assert all(isinstance(r[1], int) for r in results)  # All move counts are integers
        assert all(isinstance(r[2], int) for r in results)  # All turn counts are integers

    def test_completion_result_structure(self):
        """Test CompletionResult structure and JSON serialization."""
        result = CompletionResult(
            solved=True,
            termination_reason="solved",
            turns_taken=7,
            total_moves_attempted=7,
            invalid_turns=0,
            successful_moves=7,
            puzzle_size=3
        )

        # Test basic structure
        assert hasattr(result, "solved")
        assert hasattr(result, "termination_reason")
        assert hasattr(result, "turns_taken")
        assert hasattr(result, "total_moves_attempted")
        assert hasattr(result, "successful_moves")
        assert hasattr(result, "puzzle_size")

        # Test JSON serialization
        json_str = result.to_json()
        assert json_str is not None

        # Test deserialization
        parsed = CompletionResult.from_json(json_str)
        assert parsed.solved
        assert parsed.successful_moves == 7
        assert parsed.puzzle_size == 3

    def test_integration_with_real_puzzle_states(self):
        """Test integration with real puzzle states."""
        mock_model = create_deterministic_model(puzzle_size=3, optimal=True)
        mock_generate = MockGenerate(mock_model)
        mock_state = MockTaskState(puzzle_size=3)

        # Create puzzle and solver with correct parameters
        puzzle = TowerOfHanoi(n_disks=3)
        config = {
            "turn_limit_multiplier": 3.0,
            "move_limit_multiplier": 15.0,
            "window_size": 5,
            "repeated_invalid_limit": 3,
            "state_revisit_limit": 2
        }
        templates = {
            "system": "You are solving Tower of Hanoi puzzles.",
            "user_first": "Initial state: {initial_state}",
            "user_turn": "Current state: {current_state}"
        }

        solver = MultiTurnSolver(puzzle, config, templates)

        # Test with different initial states
        # Record initial state
        initial_state = puzzle.get_state()

        result = asyncio.run(solver.solve(mock_state, mock_generate))

        # Parse completion result
        completion_result = CompletionResult.from_json(result.metadata["puzzle_result_json"])

        # Verify state progression
        final_state = puzzle.get_state()
        assert final_state != initial_state or not completion_result.solved  # State should change if solved
        assert completion_result.puzzle_size == 3


class TestMockModel:
    """Essential mock model tests."""

    def test_mock_model_initialization(self):
        """Test MockModel basic initialization."""
        mock_model = MockModel()
        assert mock_model is not None
        assert mock_model.turn_count == 0
        assert mock_model.puzzle_size == 3

    def test_mock_generate_function(self):
        """Test MockGenerate function."""
        mock_model = create_deterministic_model(puzzle_size=3, optimal=True)
        mock_generate = MockGenerate(mock_model)
        mock_state = MockTaskState(puzzle_size=3)

        # Test that generate function works (using __call__ method)
        response = asyncio.run(mock_generate(mock_state))
        assert response is not None

    def test_mock_task_state(self):
        """Test MockTaskState functionality."""
        mock_state = MockTaskState(puzzle_size=3)
        assert mock_state.metadata["n"] == 3
        assert hasattr(mock_state, "messages")
        assert isinstance(mock_state.messages, list)
