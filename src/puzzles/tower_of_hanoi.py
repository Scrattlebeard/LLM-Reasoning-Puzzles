from copy import deepcopy
import json
import logging
import re
from typing import List, Optional, Tuple, Union

from src.puzzles.base import InvalidMoveError, PuzzleInterface

logger = logging.getLogger(__name__)

class TowerOfHanoi(PuzzleInterface):

    @staticmethod
    def get_optimal_move_count_for_difficulty(difficulty: int) -> int:
        return (2**difficulty) - 1

    def __init__(self, n_disks: int = 3):
        if n_disks < 0:
            raise ValueError(f"Number of disks must be non-negative, got {n_disks}")

        self.n_disks = n_disks
        self.pegs: List[List[int]] = [
            (
                list(range(n_disks, 0, -1)) if n_disks > 0 else []
            ),  # Peg 0: all disks (largest to smallest)
            [],  # Peg 1: empty
            [],  # Peg 2: empty
        ]
        self._state_history: List[str] = [self.get_state()]

    def get_state(self) -> str:
        """Return formatted state string.

        Returns:
            String representation in format:
            "Peg 0: 3 (bottom), 2, 1 (top)\nPeg 1: (empty)\nPeg 2: (empty)"
        """
        lines = []

        for peg_idx, peg_disks in enumerate(self.pegs):
            if not peg_disks:
                lines.append(f"Peg {peg_idx}: (empty)")
            elif len(peg_disks) == 1:
                lines.append(f"Peg {peg_idx}: {peg_disks[0]}")
            else:
                disk_parts = [f"{peg_disks[0]} (bottom)"]
                if len(peg_disks) > 2:
                    disk_parts.extend(map(str, peg_disks[1:-1]))
                disk_parts.append(f"{peg_disks[-1]} (top)")
                lines.append(f"Peg {peg_idx}: {', '.join(disk_parts)}")

        return "\n".join(lines)

    def apply_moves(self, moves: List[List[int]]) -> Union[str, InvalidMoveError]:
        """Apply a list of moves to current state with atomic rollback.

        Move sequences are applied atomically - if any move fails, the entire
        sequence is rolled back and the state remains unchanged.
        """
        if not moves:
            return self.get_state()

        logger.debug(f"Taking state snapshot before applying {len(moves)} moves")
        state_snapshot = deepcopy(self.pegs)
        history_snapshot = self._state_history.copy()

        for move_index, move in enumerate(moves):
            disk, from_peg, to_peg = move
            is_valid, error_message = self.can_move(disk, from_peg, to_peg)
            if is_valid:
                self.execute_move(int(disk), int(from_peg), int(to_peg))
                self._state_history.append(self.get_state())
                logger.debug(f"Applied move {move}: {self.get_state()}")
            else:
                # Rollback to snapshot on execution failure
                logger.debug(f"Move execution failed at index {move_index}, rolling back")
                self.pegs= state_snapshot
                self._state_history = history_snapshot
                return InvalidMoveError(
                    move_index=move_index,
                    move=str(move),
                    reason=f"Failed to execute move: {error_message}",
                )

        logger.debug(f"Successfully applied {len(moves)} moves")
        return self.get_state()

    def execute_move(self, disk: int, from_peg: int, to_peg: int) -> None:
        """Execute a move if it's legal.

        Args:
            disk: Disk ID to move (1 to n_disks)
            from_peg: Source peg index (0, 1, or 2)
            to_peg: Destination peg index (0, 1, or 2)

        """
        removed_disk = self.pegs[from_peg].pop()
        self.pegs[to_peg].append(removed_disk)
        logger.debug(f"Executed move: disk {disk} from peg {from_peg} to peg {to_peg}")

    def can_move(self, disk: int, from_peg: int, to_peg: int) -> Tuple[bool, str]:
        """Check if a move is legal without executing it.

        Args:
            disk: Disk ID to move (1 to n_disks)
            from_peg: Source peg index (0, 1, or 2)
            to_peg: Destination peg index (0, 1, or 2)

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if move is legal, False otherwise
            - error_message: Empty string if valid, detailed error if invalid
        """

        error = self._validate_move_parameters(disk, from_peg, to_peg)\
             or self._validate_disk_position(disk, from_peg)\
             or self._validate_destination_constraints(disk, to_peg)

        return (False, error) if error else (True, "")

    def get_top_disk(self, peg: int) -> Optional[int]:
        if not self.pegs[peg]:
            return None

        return self.pegs[peg][-1]

    def _validate_peg_index(self, peg: int) -> Optional[str]:
        if not isinstance(peg, int) or peg < 0 or peg >= 3:
            return f"Invalid peg index: {peg}. Must be 0, 1, or 2."

    def _validate_disk_exists(self, disk: int) -> Optional[str]:
        if not isinstance(disk, int) or disk < 1 or disk > self.n_disks:
            return f"Invalid disk ID: {disk}. Must be between 1 and {self.n_disks}."

    def _validate_pegs(self, from_peg: int, to_peg: int) -> Optional[str]:
        if from_peg == to_peg:
            return f"Cannot move from peg {from_peg} to same peg"

    def _validate_move_parameters(self, disk: int, from_peg: int, to_peg: int) -> Optional[str]:
        return self._validate_peg_index(from_peg)\
             or self._validate_peg_index(to_peg)\
             or self._validate_disk_exists(disk)\
             or self._validate_pegs(from_peg, to_peg)

    def _validate_disk_position(self, disk: int, from_peg: int) -> str:
        """Validate that disk is accessible on the source peg."""
        if disk not in self.pegs[from_peg]:
            return (
                f"Disk {disk} is not on peg {from_peg}. Current location: "
                f"{self._find_disk_peg(disk)}"
            )

        top_disk = self.get_top_disk(from_peg)
        if top_disk is None:
                return f"Peg {from_peg} is empty, cannot move disk {disk}"

        return f"Cannot move disk {disk}: disk {top_disk} is on top of peg {from_peg}" if top_disk != disk else ""

    def _find_disk_peg(self, disk: int) -> Optional[int]:
        for peg_idx, peg in enumerate(self.pegs):
            if disk in peg:
                return peg_idx
        return None

    def _validate_destination_constraints(self, disk: int, to_peg: int) -> Optional[str]:
        """Validate destination peg constraints."""
        destination_top = self.get_top_disk(to_peg)
        if destination_top is not None and disk > destination_top:
            return (
                f"Cannot place disk {disk} on disk {destination_top}: "
                f"larger disk cannot be placed on smaller disk"
            )

    def is_solved(self) -> bool:
        return (
            len(self.pegs[0]) == 0
            and len(self.pegs[1]) == 0
            and len(self.pegs[2]) == self.n_disks
            and self.pegs[2] == list(range(self.n_disks, 0, -1))
        )

    def parse_moves(self, llm_output: str) -> List[List[int]]:
        """Parse LLM output into move list.

        Supports formats JSON: [[1,0,2], [2,0,1]]
        """
        if not llm_output or not isinstance(llm_output, str):
            raise ValueError("Failed to parse moves from LLM output: Was null or not a string")

        if llm_output == "[]":
            return []

        json_pattern = r"(\[\s*\[\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\](?:\s*,\s*\[\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\])*\s*\])"
        json_matches = re.findall(json_pattern, llm_output)

        if json_matches:
            try:
                json_result = json.loads(json_matches[-1])
                if json_result and isinstance(json_result, list):
                    return json_result
            except Exception:
                pass

        raise ValueError(f"Failed to parse moves from LLM output: {llm_output}")

    def get_move_format(self) -> str:
        """Return string describing expected move format."""
        return "[[disk_id, from_peg, to_peg], ...]"

    def get_state_history(self) -> List[str]:
        """Get history of states for loop detection."""
        return self._state_history.copy()

    def copy(self) -> "TowerOfHanoi":
        new_puzzle = TowerOfHanoi(self.n_disks)
        new_puzzle.pegs = deepcopy(self.pegs)
        new_puzzle._state_history = self._state_history.copy()
        return new_puzzle

    def __str__(self) -> str:
        return f"TowerOfHanoi({self.n_disks} disks):\n{self.get_state()}"

    def get_optimal_move_count(self) -> int:
        return self.n_disks**2 - 1

    def size(self) -> int:
        return self.n_disks
