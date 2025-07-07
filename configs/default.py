"""Default configuration for Tower of Hanoi evaluation framework."""

# Model settings
model = "openrouter/google/gemini-2.5-pro"
temperature = 1.0

# Experiment settings
puzzle = "tower_of_hanoi"
puzzle_sizes = [8]

# Scaling multipliers (relative to optimal moves)
turn_limit_multiplier = 2.0   # 2x optimal assumes 1 move per turn worst case
move_limit_multiplier = 10.0  # 10x optimal for total attempts

# Termination conditions
repeated_invalid_limit = 3    # Stop after 3 identical invalid attempts
state_revisit_limit = 2       # Stop after visiting same state twice

# Paths
prompt_template_dir = "./prompts/tower_of_hanoi/"
output_dir = "./results/experiment_001"

# Random seed for reproducibility
seed = 42

# Sliding window size (messages to keep)
window_size = 4  # 2 complete exchanges