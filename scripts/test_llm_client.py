import argparse
import logging

from vlmaps.utils.llm_utils import parse_instruction
from vlmaps.utils.index_utils import find_similar_category_id
from vlmaps.utils.logging_utils import setup_logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="LLM helper smoke test (requires API key env)")
    parser.add_argument(
        "--mode",
        choices=["instruction", "category", "all"],
        default="all",
        help="Which helper(s) to test",
    )
    parser.add_argument(
        "--instruction",
        default="go to the sofa, turn right and move in between the table and the chair",
        help="Instruction for parse_instruction",
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

    if args.mode in ("instruction", "all"):
        raw_response, sanitized_code = parse_instruction(args.instruction)
        logger.info("parse_instruction raw -> %s", raw_response)
        logger.info("parse_instruction sanitized -> %s", sanitized_code)

    if args.mode in ("category", "all"):
        class_list = [c.strip() for c in args.choices.split(",") if c.strip()]
        idx = find_similar_category_id(args.category, class_list)
        logger.info("find_similar_category -> %s", class_list[idx])


if __name__ == "__main__":
    setup_logging()
    main()