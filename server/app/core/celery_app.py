from celery import Celery
from kombu import Queue, Exchange
from app.core.config import settings


def create_celery_app() -> Celery:
    app = Celery("magriplast")

    app.conf.update(
        broker_url=settings.celery_broker_url,
        result_backend=settings.celery_result_backend,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Africa/Tunis",
        enable_utc=True,
        task_acks_late=True,         
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,  # One task at a time per worker (OCR is heavy)
        result_expires=86400, 
        # Two separate queues — CPU-bound vs I/O-bound
        task_queues=(
            Queue(
                "pdf_processing",
                Exchange("pdf_processing"),
                routing_key="pdf_processing",
            ),
            Queue(
                "llm_tasks",
                Exchange("llm_tasks"),
                routing_key="llm_tasks",
            ),
        ),

        task_default_queue="pdf_processing",
        task_routes={
            "app.workers.ocr_worker.*": {"queue": "pdf_processing"},
            "app.workers.llm_worker.*": {"queue": "llm_tasks"},
            "app.workers.pipeline.*": {"queue": "pdf_processing"},
        },
        task_max_retries=3,
        task_default_retry_delay=10,  # seconds
    )

    return app


celery_app = create_celery_app()