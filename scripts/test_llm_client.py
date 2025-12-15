import argparse
import logging

from vlmaps.utils.llm_utils import parse_object_goal_instruction, parse_spatial_instruction
from vlmaps.utils.index_utils import find_similar_category_id
from vlmaps.utils.logging_utils import setup_logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="LLM helper smoke test (requires API key env)")
    parser.add_argument(
        "--mode",
        choices=["object", "spatial", "category", "all"],
        default="all",
        help="Which helper(s) to test",
    )
    parser.add_argument(
        "--object-instr",
        default="go to the sofa, turn right and move in between the table and the chair, and then move back and forth to the keyboard and the screen twice",
        help="Instruction for parse_object_goal_instruction",
    )
    parser.add_argument(
        "--spatial-instr",
        default="move to the right of the refrigerator",
        help="Instruction for parse_spatial_instruction",
    )
    parser.add_argument(
        "--category",
        default="television",
        help="Category name for find_similar_category",
    )
    parser.add_argument(
        "--choices",
        default="tv_monitor,plant,chair",
        help="Comma-separated class list for find_similar_category",
    )
    args = parser.parse_args()

    if args.mode in ("object", "all"):
        resp = parse_object_goal_instruction(args.object_instr)
        logger.info("parse_object_goal_instruction -> %s", resp)

    if args.mode in ("spatial", "all"):
        resp = parse_spatial_instruction(args.spatial_instr)
        logger.info("parse_spatial_instruction -> %s", resp)

    if args.mode in ("category", "all"):
        class_list = [c.strip() for c in args.choices.split(",") if c.strip()]
        idx = find_similar_category_id(args.category, class_list)
        logger.info("find_similar_category -> %s", class_list[idx])


if __name__ == "__main__":
    setup_logging()
    main()