"""Shared safety constraints applied regardless of which policy chose
the action. Kept separate from any single policy/env file so training
and serving can't silently drift out of sync.
"""

FRUSTRATION_MASK_THRESHOLD = 0.7
INCREASE_DIFFICULTY_ACTION = 2
HOLD_ACTION = 1


def apply_frustration_mask(frustration: float, action: int) -> int:
    """If frustration is at/above threshold and the chosen action would
    increase difficulty, remap to hold instead."""
    if frustration >= FRUSTRATION_MASK_THRESHOLD and action == INCREASE_DIFFICULTY_ACTION:
        return HOLD_ACTION
    return action
