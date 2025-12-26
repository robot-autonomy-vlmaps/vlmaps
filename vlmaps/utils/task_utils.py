"""
Utility functions for task processing and analysis.
"""
from typing import Dict


def compute_task_difficulty(task: Dict) -> int:
    """
    Compute difficulty (1-5) for any navigation task based solely on instruction complexity.
    
    This is a universal function that works for object, spatial, and future task types.
    Difficulty is determined purely by analyzing the instruction text, not by subgoal count.
    
    Criteria:
    - 1: Very simple instructions with minimal complexity indicators
    - 2: Simple instructions with basic complexity
    - 3: Moderate complexity with multiple indicators
    - 4: Complex instructions with many indicators
    - 5: Very complex instructions with high complexity indicators
    
    Args:
        task: Task dictionary with instruction field
        
    Returns:
        Difficulty level (1-5)
    """
    instruction = task.get("instruction", "").lower()
    
    if not instruction:
        # Default to moderate difficulty if no instruction
        return 3
    
    # Count complexity indicators
    # Basic complexity words (sequential/temporal indicators)
    basic_complexity = ["first", "then", "after", "next", "finally", "before", "later", "and then"]
    basic_count = sum(1 for word in basic_complexity if word in instruction)
    
    # Spatial relation complexity
    simple_spatial = ["left", "right", "north", "south", "east", "west", "front", "back"]
    complex_spatial = ["between", "middle", "in between", "with", "on your", "face"]
    
    simple_spatial_count = sum(1 for word in simple_spatial if word in instruction)
    complex_spatial_count = sum(1 for phrase in complex_spatial if phrase in instruction)
    
    # Additional complexity indicators
    proximity_words = ["nearby", "closest", "near", "adjacent"]
    proximity_count = sum(1 for word in proximity_words if word in instruction)
    
    # Count commas and conjunctions (indicates multiple actions/objects)
    conjunction_count = instruction.count(",") + instruction.count(" and ") + instruction.count(" or ")
    
    # Compute overall complexity score
    # Base complexity from sequential indicators
    complexity_score = basic_count * 1.0
    
    # Add spatial complexity (weighted higher for complex relations)
    complexity_score += simple_spatial_count * 0.5
    complexity_score += complex_spatial_count * 2.0
    
    # Add proximity complexity
    complexity_score += proximity_count * 0.5
    
    # Add conjunction complexity (multiple actions/objects)
    complexity_score += conjunction_count * 0.3
    
    # Determine difficulty based purely on complexity score
    if complexity_score <= 2.0:
        return 1
    elif complexity_score <= 4.0:
        return 2
    elif complexity_score <= 6.0:
        return 3
    elif complexity_score <= 8.0:
        return 4
    else:
        return 5
