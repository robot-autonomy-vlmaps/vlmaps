"""
Generate robot instruction dataset with instructions, code, and difficulty levels.
"""
import json
import logging
import random
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

from vlmaps.utils.instruction_templates import (
    get_templates_for_difficulty,
    get_navigable_objects,
    generate_instruction_and_code,
    ALL_DIRECTIONS,
)
from vlmaps.utils.task_utils import compute_task_difficulty

logger = logging.getLogger(__name__)

# All available robot methods (public methods that can be called in instructions)
ALL_ROBOT_METHODS = [
    "move_to",
    "turn",
    "get_pos",
    "get_contour",
    "with_object_on_left",
    "with_object_on_right",
    "move_to_left",
    "move_to_right",
    "move_in_between",
    "turn_absolute",
    "face",
    "move_north",
    "move_south",
    "move_west",
    "move_east",
    "move_to_object",
    "move_forward",
]

# Compiled regex pattern for method extraction (compile once for performance)
METHOD_PATTERN = re.compile(r"robot\.(\w+)\s*\(")


def count_objects_needed(instruction_template: str, code_template: str) -> int:
    """
    Count the number of objects needed for a template.
    
    Args:
        instruction_template: Instruction template string
        code_template: Code template string
        
    Returns:
        Number of objects needed (0-4)
    """
    # Check for numbered objects first (object1, object2, etc.)
    max_numbered = 0
    for i in range(1, 5):
        placeholder = f"{{object{i}}}"
        if placeholder in instruction_template or placeholder in code_template:
            max_numbered = i
    
    # Check for single {object} placeholder
    has_single_object = "{object}" in instruction_template or "{object}" in code_template
    
    # Return max of numbered objects or 1 if single object exists
    return max(max_numbered, 1 if has_single_object else 0)


def select_random_objects(navigable_objects: List[str], count: int) -> List[str]:
    """
    Select random objects from navigable objects list.
    
    Args:
        navigable_objects: List of available object names
        count: Number of objects to select
        
    Returns:
        List of selected object names
        
    Raises:
        ValueError: If count exceeds available objects
    """
    if count == 0:
        return []
    
    if count > len(navigable_objects):
        raise ValueError(
            f"Requested {count} objects but only {len(navigable_objects)} available"
        )
    
    return random.sample(navigable_objects, count)


def determine_direction(
    instruction_template: str, code_template: str, placeholder: str
) -> str:
    """
    Determine appropriate direction value for a placeholder.
    
    Args:
        instruction_template: Instruction template string
        code_template: Code template string
        placeholder: Direction placeholder ("{direction}" or "{direction2}")
        
    Returns:
        Random direction value
    """
    is_turn_instruction = "turn" in instruction_template.lower()
    has_placeholder = placeholder in instruction_template
    
    # If it's a turn instruction with the placeholder, use left/right
    if is_turn_instruction and has_placeholder:
        return random.choice(["left", "right"])
    
    # Otherwise, use all spatial directions
    return random.choice(["north", "south", "east", "west", "left", "right"])


def determine_degrees(
    instruction_template: str, code_template: str, direction: str = None
) -> int:
    """
    Determine appropriate degrees value based on template and direction.
    
    Args:
        instruction_template: Instruction template string
        code_template: Code template string
        direction: Optional direction parameter
        
    Returns:
        Degrees value (can be negative for left turns)
    """
    code_has_negative = "-{degrees}" in code_template
    instruction_lower = instruction_template.lower()
    
    # Check if instruction explicitly says "turn left" or "turn right"
    is_left = "turn left" in instruction_lower
    is_right = "turn right" in instruction_lower
    
    # If direction parameter is set and template uses it for turning
    if not is_left and not is_right and direction:
        is_turn_with_direction = (
            "turn" in instruction_lower and "{direction}" in instruction_template
        )
        if is_turn_with_direction:
            is_left = direction == "left"
            is_right = direction == "right"
    
    # Generate degrees based on direction
    degrees = random.randint(15, 90)
    
    if is_left:
        # Left turn: negative unless code template already has negative
        return degrees if code_has_negative else -degrees
    elif is_right:
        # Right turn: always positive
        return degrees
    else:
        # Random direction: check code template for sign handling
        if code_has_negative:
            return degrees
        else:
            return random.choice([-degrees, degrees])


def generate_template_params(
    instruction_template: str, code_template: str
) -> Dict[str, Any]:
    """
    Generate random parameters for a template.
    
    Args:
        instruction_template: Instruction template string
        code_template: Code template string
        
    Returns:
        Dictionary of parameter values
    """
    params = {}
    
    # Handle direction placeholders
    if "{direction}" in instruction_template or "{direction}" in code_template:
        params["direction"] = determine_direction(
            instruction_template, code_template, "{direction}"
        )
    
    if "{direction2}" in instruction_template or "{direction2}" in code_template:
        params["direction2"] = determine_direction(
            instruction_template, code_template, "{direction2}"
        )
    
    # Handle degrees (needs direction to be set first)
    if "{degrees}" in instruction_template or "{degrees}" in code_template:
        params["degrees"] = determine_degrees(
            instruction_template, code_template, params.get("direction")
        )
    
    # Handle meters
    if "{meters}" in instruction_template or "{meters}" in code_template:
        params["meters"] = round(random.uniform(1.0, 5.0), 1)
    
    if "{meters2}" in instruction_template or "{meters2}" in code_template:
        params["meters2"] = round(random.uniform(1.0, 5.0), 1)
    
    # Handle n (number of times)
    if "{n}" in instruction_template or "{n}" in code_template:
        params["n"] = random.randint(2, 5)
    
    # Handle cardinal directions
    if "{cardinal_direction}" in instruction_template or "{cardinal_direction}" in code_template:
        params["cardinal_direction"] = random.choice(ALL_DIRECTIONS)
    
    if "{cardinal_direction2}" in instruction_template or "{cardinal_direction2}" in code_template:
        params["cardinal_direction2"] = random.choice(ALL_DIRECTIONS)
    
    # Handle side
    if "{side}" in instruction_template or "{side}" in code_template:
        params["side"] = random.choice(["left", "right"])
    
    return params


def ensure_difficulty_match(
    instruction: str, target_difficulty: int, max_attempts: int = 100
) -> bool:
    """
    Check if instruction matches target difficulty.
    
    Args:
        instruction: Generated instruction text
        target_difficulty: Target difficulty level (1-5)
        max_attempts: Maximum attempts (not used, kept for API compatibility)
        
    Returns:
        True if difficulty matches, False otherwise
    """
    task = {"instruction": instruction}
    computed_difficulty = compute_task_difficulty(task)
    return computed_difficulty == target_difficulty


def generate_dataset_for_difficulty(
    difficulty: int,
    count: int,
    navigable_objects: List[str],
    max_attempts_per_sample: int = 50,
) -> List[Dict]:
    """
    Generate N samples for a difficulty level.
    
    Args:
        difficulty: Difficulty level (1-5)
        count: Number of samples to generate
        navigable_objects: List of navigable object names
        max_attempts_per_sample: Maximum attempts per sample to match difficulty
        
    Returns:
        List of task dictionaries with instruction, code, and difficulty
    """
    templates = get_templates_for_difficulty(difficulty)
    if not templates:
        logger.warning(f"No templates found for difficulty {difficulty}")
        return []
    
    if count == 0:
        return []
    
    # Validate we have enough objects for the most complex template
    max_objects_needed = max(
        count_objects_needed(inst, code) for inst, code in templates
    )
    if max_objects_needed > len(navigable_objects):
        logger.warning(
            f"Some templates require {max_objects_needed} objects, "
            f"but only {len(navigable_objects)} available. "
            f"Generation may fail for some templates."
        )
    
    tasks = []
    attempts = 0
    mismatches = 0
    errors = 0
    max_total_attempts = count * max_attempts_per_sample
    
    # Progress logging interval
    log_interval = max(1, count // 10)  # Log every 10% progress
    
    while len(tasks) < count and attempts < max_total_attempts:
        attempts += 1
        
        # Select random template
        template_pair = random.choice(templates)
        instruction_template, code_template = template_pair
        
        # Count objects needed
        num_objects_needed = count_objects_needed(instruction_template, code_template)
        
        # Select random objects
        try:
            selected_objects = select_random_objects(navigable_objects, num_objects_needed)
        except ValueError as e:
            logger.warning(f"Skipping template due to object requirement: {e}")
            errors += 1
            continue
        
        # Generate random parameters
        params = generate_template_params(instruction_template, code_template)
        
        # Generate instruction and code
        try:
            instruction, code = generate_instruction_and_code(
                template_pair, selected_objects, params
            )
            
            # Verify difficulty matches
            if ensure_difficulty_match(instruction, difficulty):
                task = {
                    "instruction": instruction,
                    "code": code,
                    "difficulty": difficulty,
                }
                tasks.append(task)
                
                # Progress logging
                if len(tasks) % log_interval == 0:
                    logger.info(
                        f"Progress: {len(tasks)}/{count} tasks generated "
                        f"for difficulty {difficulty} "
                        f"(attempts: {attempts}, mismatches: {mismatches}, errors: {errors})"
                    )
            else:
                mismatches += 1
                # Only log mismatches at debug level to avoid spam
                if logger.isEnabledFor(logging.DEBUG):
                    computed = compute_task_difficulty({"instruction": instruction})
                    logger.debug(
                        f"Difficulty mismatch: expected {difficulty}, got {computed} "
                        f"for: {instruction[:50]}..."
                    )
        except Exception as e:
            errors += 1
            logger.warning(f"Error generating task: {e}")
            continue
    
    # Final summary
    if len(tasks) < count:
        logger.warning(
            f"Only generated {len(tasks)}/{count} tasks for difficulty {difficulty} "
            f"after {attempts} attempts "
            f"(mismatches: {mismatches}, errors: {errors}, "
            f"success rate: {len(tasks)/attempts*100:.1f}%)"
        )
    else:
        logger.info(
            f"Successfully generated {len(tasks)} tasks for difficulty {difficulty} "
            f"in {attempts} attempts "
            f"(mismatches: {mismatches}, errors: {errors}, "
            f"success rate: {len(tasks)/attempts*100:.1f}%)"
        )
    
    return tasks


def count_method_usage(tasks: List[Dict]) -> Dict[str, int]:
    """
    Count method usage across all generated tasks.
    
    Args:
        tasks: List of task dictionaries with code fields
        
    Returns:
        Dictionary mapping method names to usage counts
    """
    method_counter = Counter({method: 0 for method in ALL_ROBOT_METHODS})
    
    for task in tasks:
        code = task.get("code", "")
        # Find all method calls in the code
        matches = METHOD_PATTERN.findall(code)
        for method_name in matches:
            if method_name in method_counter:
                method_counter[method_name] += 1
    
    return dict(sorted(method_counter.items()))


def calculate_difficulty_distribution(tasks: List[Dict]) -> Dict[int, int]:
    """
    Calculate difficulty distribution from tasks.
    
    Args:
        tasks: List of task dictionaries with difficulty fields
        
    Returns:
        Dictionary mapping difficulty levels to counts
    """
    distribution = Counter(task["difficulty"] for task in tasks)
    return dict(sorted(distribution.items()))


def main():
    """Main function to generate the instruction dataset."""
    start_time = datetime.now()
    
    # Configuration for sample counts
    difficulty_counts = {1: 0, 2: 0, 3: 1000, 4: 2000, 5: 3000}
    
    # Get navigable objects
    navigable_objects = get_navigable_objects()
    logger.info(f"Using {len(navigable_objects)} navigable objects")
    
    # Generate tasks for each difficulty level
    all_tasks = []
    task_id = 0
    
    for difficulty in sorted(difficulty_counts.keys()):
        count = difficulty_counts[difficulty]
        if count == 0:
            logger.info(f"Skipping difficulty {difficulty} (count is 0)")
            continue
        
        logger.info(f"Generating {count} tasks for difficulty {difficulty}...")
        
        tasks = generate_dataset_for_difficulty(difficulty, count, navigable_objects)
        
        # Add task_id to each task
        for task in tasks:
            task["task_id"] = task_id
            task_id += 1
        
        all_tasks.extend(tasks)
        logger.info(f"Completed difficulty {difficulty}: {len(tasks)} tasks generated")
    
    if not all_tasks:
        logger.warning("No tasks were generated!")
        return
    
    # Create output structure
    output = {
        "metadata": {
            "total_tasks": len(all_tasks),
            "generation_timestamp": start_time.isoformat(),
            "difficulty_distribution": calculate_difficulty_distribution(all_tasks),
            "method_usage": count_method_usage(all_tasks),
        },
        "tasks": all_tasks,
    }
    
    # Save to JSON
    output_path = Path("instruction_dataset.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    # Calculate generation time
    generation_time = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"Saved {len(all_tasks)} tasks to {output_path}")
    logger.info(f"Generation time: {generation_time:.2f} seconds")
    logger.info(f"Difficulty distribution: {output['metadata']['difficulty_distribution']}")
    logger.info(f"Method usage: {output['metadata']['method_usage']}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()

