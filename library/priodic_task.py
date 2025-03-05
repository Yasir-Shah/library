from celery import shared_task
from celery.utils.log import get_task_logger
from models import Book

logger = get_task_logger(__name__)


@shared_task
def check_overdue_loans():
    logger.info("The sample task just ran.")
    print("working!")
    


