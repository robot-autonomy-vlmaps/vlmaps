"""
Instruction templates for generating robot navigation tasks.
Each template is a tuple of (instruction_template, code_template).
"""
import random
from typing import List, Tuple, Dict, Any

# Non-navigable objects to exclude
NON_NAVIGABLE = {"void", "wall", "floor", "ceiling"}

# Object name conversions for natural language
OBJECT_NAME_MAP = {
    "tv_monitor": "television",
    "chest_of_drawers": "chest of drawers",
    "gym_equipment": "gym equipment",
    "board_panel": "board panel",
}

# Spatial directions
DIRECTIONS = ["north", "south", "east", "west", "left", "right"]
CARDINAL_DIRECTIONS = ["north", "south", "east", "west"]
INTERCARDINAL_DIRECTIONS = ["northeast", "northwest", "southeast", "southwest"]
ALL_DIRECTIONS = CARDINAL_DIRECTIONS + INTERCARDINAL_DIRECTIONS
SIDES = ["left", "right"]

# Direction to absolute angle mapping
DIRECTION_TO_ANGLE = {
    "north": 0,
    "east": 90,
    "south": 180,
    "west": -90,
    "northeast": 45,
    "northwest": -45,
    "southeast": 135,
    "southwest": -135,
}

# Difficulty 1: Simple single-action instructions
DIFFICULTY_1_TEMPLATES = [
    ("move to the {object}", "robot.move_to_object('{object}')"),
    ("go to the {object}", "robot.move_to_object('{object}')"),
    ("navigate to the {object}", "robot.move_to_object('{object}')"),
    ("face the {object}", "robot.face('{object}')"),
    ("turn left {degrees} degrees", "robot.turn(-{degrees})"),
    ("turn right {degrees} degrees", "robot.turn({degrees})"),
    ("turn {degrees} degrees", "robot.turn({degrees})"),
    ("turn north", "robot.turn_absolute(0)"),
    ("turn east", "robot.turn_absolute(90)"),
    ("turn south", "robot.turn_absolute(180)"),
    ("turn west", "robot.turn_absolute(-90)"),
]

# Difficulty 2: Basic spatial relations
DIFFICULTY_2_TEMPLATES = [
    ("move to the {direction} of the {object}", "robot.move_{direction}('{object}')"),
    ("go to the {direction} side of the {object}", "robot.move_{direction}('{object}')"),
    ("move to the {object}, then turn {direction}", "robot.move_to_object('{object}')\nrobot.turn({degrees})"),
    ("face the {object}, then turn {direction}", "robot.face('{object}')\nrobot.turn({degrees})"),
    ("move forward {meters} meters", "robot.move_forward({meters})"),
    ("turn {direction} and move forward {meters} meters", "robot.turn({degrees})\nrobot.move_forward({meters})"),
    ("move {meters} meters north", "robot.turn_absolute(0)\nrobot.move_forward({meters})"),
    ("move {meters} meters east", "robot.turn_absolute(90)\nrobot.move_forward({meters})"),
    ("move {meters} meters south", "robot.turn_absolute(180)\nrobot.move_forward({meters})"),
    ("move {meters} meters west", "robot.turn_absolute(-90)\nrobot.move_forward({meters})"),
    ("turn northeast", "robot.turn_absolute(45)"),
    ("turn northwest", "robot.turn_absolute(-45)"),
    ("turn southeast", "robot.turn_absolute(135)"),
    ("turn southwest", "robot.turn_absolute(-135)"),
    ("move {meters} meters northeast", "robot.turn_absolute(45)\nrobot.move_forward({meters})"),
    ("move {meters} meters northwest", "robot.turn_absolute(-45)\nrobot.move_forward({meters})"),
    ("move {meters} meters southeast", "robot.turn_absolute(135)\nrobot.move_forward({meters})"),
    ("move {meters} meters southwest", "robot.turn_absolute(-135)\nrobot.move_forward({meters})"),
]

# Difficulty 3: Multiple actions with temporal indicators
DIFFICULTY_3_TEMPLATES = [
    ("first move to the {object1}, then go to the {object2}", "robot.move_to_object('{object1}')\nrobot.move_to_object('{object2}')"),
    ("move to the {object1}, then move to the {object2}", "robot.move_to_object('{object1}')\nrobot.move_to_object('{object2}')"),
    ("go to the {object1}, then face the {object2}", "robot.move_to_object('{object1}')\nrobot.face('{object2}')"),
    ("move to the {direction} of the {object1}, with the {object2} on your {side}", "robot.move_{direction}('{object1}')\nrobot.with_object_on_{side}('{object2}')"),
    ("face the {object1}, then move to the {direction} of the {object2}", "robot.face('{object1}')\nrobot.move_{direction}('{object2}')"),
    ("move to the {object1}, then turn {direction} {degrees} degrees", "robot.move_to_object('{object1}')\nrobot.turn({degrees})"),
    ("turn {cardinal_direction}, then move forward {meters} meters", "robot.turn_absolute({angle})\nrobot.move_forward({meters})"),
    ("move to the {object1}, then turn {cardinal_direction} and move forward {meters} meters", "robot.move_to_object('{object1}')\nrobot.turn_absolute({angle})\nrobot.move_forward({meters})"),
    ("face the {object1}, then turn {cardinal_direction} and move {meters} meters", "robot.face('{object1}')\nrobot.turn_absolute({angle})\nrobot.move_forward({meters})"),
]

# Difficulty 4: Complex spatial relations
DIFFICULTY_4_TEMPLATES = [
    ("move in between the {object1} and {object2}, then face the {object3}", "robot.move_in_between('{object1}', '{object2}')\nrobot.face('{object3}')"),
    ("go to the {object1}, with the {object2} on your {side}, turn {direction} {degrees} degrees", "robot.move_to_object('{object1}')\nrobot.with_object_on_{side}('{object2}')\nrobot.turn({degrees})"),
    ("first move to the {direction} of the {object1}, then move in between the {object2} and {object3}", "robot.move_{direction}('{object1}')\nrobot.move_in_between('{object2}', '{object3}')"),
    ("move to the {object1}, then go to the {direction} of the {object2}, finally face the {object3}", "robot.move_to_object('{object1}')\nrobot.move_{direction}('{object2}')\nrobot.face('{object3}')"),
    ("with the {object1} on your {side}, move to the {direction} of the {object2}, then turn {direction} {degrees} degrees", "robot.with_object_on_{side}('{object1}')\nrobot.move_{direction}('{object2}')\nrobot.turn({degrees})"),
    ("turn {cardinal_direction}, move forward {meters} meters, then go to the {object1}", "robot.turn_absolute({angle})\nrobot.move_forward({meters})\nrobot.move_to_object('{object1}')"),
    ("move to the {object1}, turn {cardinal_direction}, then move forward {meters} meters", "robot.move_to_object('{object1}')\nrobot.turn_absolute({angle})\nrobot.move_forward({meters})"),
    ("face the {object1}, turn {cardinal_direction}, move {meters} meters, then go to the {object2}", "robot.face('{object1}')\nrobot.turn_absolute({angle})\nrobot.move_forward({meters})\nrobot.move_to_object('{object2}')"),
]

# Difficulty 5: Very complex multi-step instructions
DIFFICULTY_5_TEMPLATES = [
    ("first move to the {object1}, then move in between the {object2} and {object3}, finally go to the {direction} of the {object4}", "robot.move_to_object('{object1}')\nrobot.move_in_between('{object2}', '{object3}')\nrobot.move_{direction}('{object4}')"),
    ("move back and forth between the {object1} and {object2} {n} times", "pos1 = robot.get_pos('{object1}')\npos2 = robot.get_pos('{object2}')\nfor i in range({n}):\n    robot.move_to(pos1)\n    robot.move_to(pos2)"),
    ("first go to the {object1}, then move to the {direction} of the {object2}, with the {object3} on your {side}, finally face the {object4}", "robot.move_to_object('{object1}')\nrobot.move_{direction}('{object2}')\nrobot.with_object_on_{side}('{object3}')\nrobot.face('{object4}')"),
    ("move to the {object1}, then move in between the {object2} and {object3}, turn {direction} {degrees} degrees, and finally go to the {direction2} of the {object4}", "robot.move_to_object('{object1}')\nrobot.move_in_between('{object2}', '{object3}')\nrobot.turn({degrees})\nrobot.move_{direction2}('{object4}')"),
    ("with the {object1} on your {side}, move to the {direction} of the {object2}, then move in between the {object3} and {object4}, finally turn {direction2} {degrees} degrees", "robot.with_object_on_{side}('{object1}')\nrobot.move_{direction}('{object2}')\nrobot.move_in_between('{object3}', '{object4}')\nrobot.turn({degrees})"),
    ("turn {cardinal_direction}, move forward {meters} meters, then go to the {object1}, and finally move to the {direction} of the {object2}", "robot.turn_absolute({angle})\nrobot.move_forward({meters})\nrobot.move_to_object('{object1}')\nrobot.move_{direction}('{object2}')"),
    ("move to the {object1}, turn {cardinal_direction}, move {meters} meters, then move in between the {object2} and {object3}", "robot.move_to_object('{object1}')\nrobot.turn_absolute({angle})\nrobot.move_forward({meters})\nrobot.move_in_between('{object2}', '{object3}')"),
    ("face the {object1}, turn {cardinal_direction}, move forward {meters} meters, go to the {object2}, then turn {cardinal_direction2} and move {meters2} meters", "robot.face('{object1}')\nrobot.turn_absolute({angle})\nrobot.move_forward({meters})\nrobot.move_to_object('{object2}')\nrobot.turn_absolute({angle2})\nrobot.move_forward({meters2})"),
]


def get_templates_for_difficulty(difficulty: int) -> List[Tuple[str, str]]:
    """
    Get list of (instruction_template, code_template) pairs for a difficulty level.
    
    Args:
        difficulty: Difficulty level (1-5)
        
    Returns:
        List of (instruction_template, code_template) tuples
    """
    templates_map = {
        1: DIFFICULTY_1_TEMPLATES,
        2: DIFFICULTY_2_TEMPLATES,
        3: DIFFICULTY_3_TEMPLATES,
        4: DIFFICULTY_4_TEMPLATES,
        5: DIFFICULTY_5_TEMPLATES,
    }
    return templates_map.get(difficulty, [])


def object_name_to_natural(obj_name: str) -> str:
    """
    Convert object name to natural language format.
    
    Args:
        obj_name: Object name from categories (e.g., "tv_monitor")
        
    Returns:
        Natural language name (e.g., "television")
    """
    return OBJECT_NAME_MAP.get(obj_name, obj_name.replace("_", " "))


def get_navigable_objects() -> List[str]:
    """
    Get list of navigable objects from Matterport3D categories.
    
    Returns:
        List of object names (excluding non-navigable ones)
    """
    from vlmaps.utils.matterport3d_categories import mp3dcat
    
    navigable = [obj for obj in mp3dcat if obj not in NON_NAVIGABLE]
    return navigable


def generate_instruction_and_code(
    template_pair: Tuple[str, str],
    objects: List[str],
    params: Dict[str, Any]
) -> Tuple[str, str]:
    """
    Generate both instruction and code from template pair.
    
    Args:
        template_pair: (instruction_template, code_template) tuple
        objects: List of object names to use
        params: Dictionary with additional parameters (degrees, meters, n, etc.)
        
    Returns:
        (instruction, code) tuple
    """
    instruction_template, code_template = template_pair
    
    # Create a mapping for replacements
    replacements = {}
    
    # Map objects to placeholders
    object_idx = 0
    for i in range(1, 5):  # Support up to object4
        placeholder = f"{{object{i}}}"
        if placeholder in instruction_template or placeholder in code_template:
            if object_idx < len(objects):
                obj_name = objects[object_idx]
                natural_name = object_name_to_natural(obj_name)
                replacements[f"{{object{i}}}"] = natural_name
                replacements[f"object{i}"] = obj_name  # For code template
                object_idx += 1
    
    # Handle single {object} placeholder
    if "{object}" in instruction_template or "{object}" in code_template:
        if objects:
            obj_name = objects[0]
            natural_name = object_name_to_natural(obj_name)
            replacements["{object}"] = natural_name
            replacements["object"] = obj_name  # For code template
    
    # Handle direction placeholders
    if "{direction}" in instruction_template or "{direction}" in code_template:
        direction = params.get("direction", random.choice(DIRECTIONS))
        replacements["{direction}"] = direction
    
    if "{direction2}" in instruction_template or "{direction2}" in code_template:
        direction2 = params.get("direction2", random.choice(DIRECTIONS))
        replacements["{direction2}"] = direction2
    
    # Handle side placeholder
    if "{side}" in instruction_template or "{side}" in code_template:
        side = params.get("side", random.choice(SIDES))
        replacements["{side}"] = side
    
    # Handle degrees placeholder
    if "{degrees}" in instruction_template or "{degrees}" in code_template:
        degrees = params.get("degrees", random.randint(15, 90))
        # Note: The code template may already have a negative sign (e.g., robot.turn(-{degrees}))
        # So we should use the absolute value here and let the template handle the sign
        # But if degrees is already negative from params, use it as-is
        replacements["{degrees}"] = degrees
    
    # Handle meters placeholder
    if "{meters}" in instruction_template or "{meters}" in code_template:
        meters = params.get("meters", round(random.uniform(1.0, 5.0), 1))
        replacements["{meters}"] = meters
    
    # Handle n (number of times) placeholder
    if "{n}" in instruction_template or "{n}" in code_template:
        n = params.get("n", random.randint(2, 5))
        replacements["{n}"] = n
    
    # Handle cardinal_direction and angle placeholders
    if "{cardinal_direction}" in instruction_template or "{cardinal_direction}" in code_template:
        cardinal_direction = params.get("cardinal_direction", random.choice(ALL_DIRECTIONS))
        angle = DIRECTION_TO_ANGLE.get(cardinal_direction, 0)
        replacements["{cardinal_direction}"] = cardinal_direction
        replacements["{angle}"] = angle
    
    if "{cardinal_direction2}" in instruction_template or "{cardinal_direction2}" in code_template:
        cardinal_direction2 = params.get("cardinal_direction2", random.choice(ALL_DIRECTIONS))
        angle2 = DIRECTION_TO_ANGLE.get(cardinal_direction2, 0)
        replacements["{cardinal_direction2}"] = cardinal_direction2
        replacements["{angle2}"] = angle2
    
    # Handle meters2 placeholder
    if "{meters2}" in instruction_template or "{meters2}" in code_template:
        meters2 = params.get("meters2", round(random.uniform(1.0, 5.0), 1))
        replacements["{meters2}"] = meters2
    
    # Apply replacements to instruction
    instruction = instruction_template
    for placeholder, value in replacements.items():
        if placeholder.startswith("{") and placeholder.endswith("}"):
            instruction = instruction.replace(placeholder, str(value))
    
    # Apply replacements to code
    code = code_template
    
    # Handle direction in code template first (e.g., move_{direction} -> move_north or move_to_left)
    if "{direction}" in code:
        direction_value = replacements.get("{direction}", "north")
        # Map direction to correct method name
        if direction_value == "left":
            method_name = "move_to_left"
        elif direction_value == "right":
            method_name = "move_to_right"
        else:
            method_name = f"move_{direction_value}"  # north, south, east, west
        
        # Replace move_{direction} with the correct method name
        code = code.replace("move_{direction}", method_name)
        # Replace any remaining {direction} placeholders
        code = code.replace("{direction}", direction_value)
    
    if "{direction2}" in code:
        direction2_value = replacements.get("{direction2}", "north")
        # Map direction2 to correct method name
        if direction2_value == "left":
            method_name2 = "move_to_left"
        elif direction2_value == "right":
            method_name2 = "move_to_right"
        else:
            method_name2 = f"move_{direction2_value}"  # north, south, east, west
        
        # Replace move_{direction2} with the correct method name
        code = code.replace("move_{direction2}", method_name2)
        # Replace any remaining {direction2} placeholders
        code = code.replace("{direction2}", direction2_value)
    
    # Handle side in code template (e.g., with_object_on_{side} -> with_object_on_left)
    if "{side}" in code:
        side_value = replacements.get("{side}", "left")
        # Replace with_object_on_{side} with with_object_on_left (or right)
        code = code.replace("with_object_on_{side}", f"with_object_on_{side_value}")
        # Replace any remaining {side} placeholders
        code = code.replace("{side}", side_value)
    
    # For code, we need to handle object placeholders differently
    # Replace {object} with the actual object name (not natural language)
    for i in range(1, 5):
        placeholder = f"{{object{i}}}"
        if placeholder in code:
            if f"object{i}" in replacements:
                code = code.replace(placeholder, replacements[f"object{i}"])
    
    if "{object}" in code:
        if "object" in replacements:
            code = code.replace("{object}", replacements["object"])
    
    # Replace other placeholders in code (degrees, meters, n, angle, etc.)
    for placeholder, value in replacements.items():
        if placeholder.startswith("{") and placeholder.endswith("}"):
            if placeholder not in ["{object}", "{object1}", "{object2}", "{object3}", "{object4}", "{direction}", "{direction2}", "{side}", "{cardinal_direction}", "{cardinal_direction2}"]:
                code = code.replace(placeholder, str(value))
    
    return instruction, code


def format_code_template(code_template: str, objects: List[str], params: Dict[str, Any]) -> str:
    """
    Format code template with proper indentation and line breaks.
    This is a helper that calls generate_instruction_and_code and returns just the code.
    
    Args:
        code_template: Code template string
        objects: List of object names
        params: Dictionary with parameters
        
    Returns:
        Formatted code string
    """
    _, code = generate_instruction_and_code(("", code_template), objects, params)
    return code

