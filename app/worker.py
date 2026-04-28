import logging

from app.services.task_queue import get_next_task, run_task


logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Log analysis worker started.")

    while True:
        task_id = get_next_task(timeout=5)
        if not task_id:
            continue

        logger.info("Processing analysis task %s", task_id)
        run_task(task_id)


if __name__ == "__main__":
    main()
