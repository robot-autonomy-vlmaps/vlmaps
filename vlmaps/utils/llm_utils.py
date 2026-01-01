import logging

from vlmaps.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)


def _sanitize_spatial_code(output: str) -> str:
    """
    Remove prose/markdown and keep only executable robot code lines.
    """
    if not output:
        return ""

    cleaned = (
        output.replace("```python", "```")
        .replace("```", "\n")
        .replace("`", "")
    )

    allowed_prefixes = (
        "robot.",
        "pos",
        "contour",
        "for ",
        "np.",
        "ids",
        "center",
        "bbox_list",
        "nearest_id",
    )

    kept_lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(prefix) for prefix in allowed_prefixes):
            kept_lines.append(stripped)

    return "\n".join(kept_lines)


def parse_instruction(language_instr):
    """
    Unified instruction parser that generates robot code for any navigation instruction.
    Works for both object goal navigation and spatial goal navigation.
    
    Example: "go to the chair, then the table" -> "robot.move_to_object('chair')\nrobot.move_to_object('table')"
    Example: "move to the left of the plant" -> "robot.move_to_left('plant')"
    """
    provider = get_llm_provider()
    instructions_list = [language_instr]
    results = ""
    for lang in instructions_list:
        text = provider.parse_instruction(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write ONLY Python commands for a LangRobot instance named 'robot'. "
                        "Do not include explanations, markdown, or code fences. "
                        "Return one or more newline-separated statements that can be executed with eval(). "
                        "Allowed APIs include robot.move_to_left/right/in_between/north/south/east/west/"
                        "turn/turn_absolute/move_forward/face/move_to_object/with_object_on_left/"
                        "with_object_on_right/get_pos/get_contour plus simple Python control flow."
                    ),
                },
                {"role": "user", "content": "move a bit to the right of the refrigerator"},
                {"role": "assistant", "content": "robot.move_to_right('refrigerator')"},
                {"role": "user", "content": "move in between the couch and bookshelf"},
                {"role": "assistant", "content": "robot.move_in_between('couch', 'bookshelf')"},
                {"role": "user", "content": "move in the middle of the stairs and oven"},
                {"role": "assistant", "content": "robot.move_in_between('stairs', 'oven')"},
                {"role": "user", "content": "face the toilet"},
                {"role": "assistant", "content": "robot.face('toilet')"},
                {"role": "user", "content": "move to the south side of the table"},
                {"role": "assistant", "content": "robot.move_south('table')"},
                {"role": "user", "content": "move to the west of the chair"},
                {"role": "assistant", "content": "robot.move_west('chair')"},
                {"role": "user", "content": "move to the east of the chair"},
                {"role": "assistant", "content": "robot.move_east('chair')"},
                {"role": "user", "content": "turn left 60 degrees"},
                {"role": "assistant", "content": "robot.turn(-60)"},
                {"role": "user", "content": "turn right 20 degrees"},
                {"role": "assistant", "content": "robot.turn(20)"},
                {"role": "user", "content": "find any chairs in the environment"},
                {"role": "assistant", "content": "robot.move_to_object('chair')"},
                {"role": "user", "content": "come to the table"},
                {"role": "assistant", "content": "robot.move_to_object('table')"},
                {"role": "user", "content": "go to the chair and then go to the table"},
                {"role": "assistant", "content": "robot.move_to_object('chair')\nrobot.move_to_object('table')"},
                {"role": "user", "content": "navigate to the green sofa and then go to the painting"},
                {"role": "assistant", "content": "robot.move_to_object('green_sofa')\nrobot.move_to_object('painting')"},
                {"role": "user", "content": "walk to the plant first, then come back to the table, and stand next to the bed"},
                {"role": "assistant", "content": "robot.move_to_object('plant')\nrobot.move_to_object('table')\nrobot.move_to_object('bed')"},
                {"role": "user", "content": "with the television on your left"},
                {"role": "assistant", "content": "robot.with_object_on_left('television')"},
                {"role": "user", "content": "with the toilet to your right, turn left 30 degrees"},
                {"role": "assistant", "content": "robot.with_object_on_right('toilet')\nrobot.turn(-30)"},
                {"role": "user", "content": "with the toilet to your left, turn right 30 degrees"},
                {"role": "assistant", "content": "robot.with_object_on_left('toilet')\nrobot.turn(30)"},
                {"role": "user", "content": "with the television behind you"},
                {"role": "assistant", "content": "robot.face('television')\nrobot.turn(180)"},
                {"role": "user", "content": "go to the south of the table in front of you, with the table on your left, turn right 45 degrees"},
                {"role": "assistant", "content": "robot.move_south('table')\nrobot.with_object_on_left('table')\nrobot.turn(45)"},
                {"role": "user", "content": "move forward for 3 meters"},
                {"role": "assistant", "content": "robot.move_forward(3)"},
                {"role": "user", "content": "move right 2 meters"},
                {"role": "assistant", "content": "robot.turn(90)\nrobot.move_forward(2)"},
                {"role": "user", "content": "move left 3 meters"},
                {"role": "assistant", "content": "robot.turn(-90)\nrobot.move_forward(3)"},
                {"role": "user", "content": "move back and forth between the chair and the table 3 times"},
                {"role": "assistant", "content": "pos1 = robot.get_pos('chair')\npos2 = robot.get_pos('table')\nfor i in range(3):\n    robot.move_to(pos1)\n    robot.move_to(pos2)"},
                {"role": "user", "content": "go to the television"},
                {"role": "assistant", "content": "robot.move_to_object('television')"},
                {"role": "user", "content": "monitor the chair from 4 view points"},
                {"role": "assistant", "content": "contour = robot.get_contour('chair')\nnp.random.shuffle(contour)\nfor pos in contour[:4]:\n    robot.move_to(pos)\n    robot.face('chair')"},
                {"role": "user", "content": "navigate to 3 meters right of the table"},
                {"role": "assistant", "content": "robot.move_to_right('table')\nrobot.face('table')\nrobot.turn(180)\nrobot.move_forward(3)"},
                {"role": "user", "content": "turn west"},
                {"role": "assistant", "content": "robot.turn_absolute(-90)"},
                {"role": "user", "content": "turn east"},
                {"role": "assistant", "content": "robot.turn_absolute(90)"},
                {"role": "user", "content": "turn south"},
                {"role": "assistant", "content": "robot.turn_absolute(180)"},
                {"role": "user", "content": "turn north"},
                {"role": "assistant", "content": "robot.turn_absolute(0)"},
                {"role": "user", "content": "turn east and then turn left 90 degrees"},
                {"role": "assistant", "content": "robot.turn_absolute(90)\nrobot.turn(-90)"},
                {"role": "user", "content": "move 3 meters north of the chair"},
                {"role": "assistant", "content": "robot.move_north('chair')\nrobot.move_forward(3)"},
                {"role": "user", "content": "move 1 meters south of the chair"},
                {"role": "assistant", "content": "robot.move_south('chair')\nrobot.move_forward(3)"},
                {"role": "user", "content": "move 3 meters west"},
                {"role": "assistant", "content": "robot.turn_absolute(-90)\nrobot.move_forward(3)"},
                {"role": "user", "content": lang},
            ],
        )
        if text:
            sanitized = _sanitize_spatial_code(text)
            results += (sanitized or text.strip()) + "\n"
    return results


if __name__ == '__main__':
    text = parse_instruction("go to the sofa, turn right and move in between the table and the chair, and then move back and forth to the keyboard and the screen twice")
    logger.info("%s", text)