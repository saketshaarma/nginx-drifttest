import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db import db
from comparison import execute_comparison

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _scheduled_run(node_pair_id: str):
    logger.info(f"Scheduled comparison run for node pair {node_pair_id}")
    try:
        await execute_comparison(node_pair_id, triggered_by="scheduled")
    except Exception as exc:
        logger.error(f"Scheduled run failed for {node_pair_id}: {exc}")


def schedule_node_pair(node_pair: dict):
    """Add or update a scheduled job for a node pair."""
    job_id = f"nodepair-{node_pair['id']}"
    remove_node_pair_job(node_pair["id"])
    if node_pair.get("schedule_enabled") and node_pair.get("schedule_interval_minutes"):
        interval = int(node_pair["schedule_interval_minutes"])
        scheduler.add_job(
            _scheduled_run,
            trigger="interval",
            minutes=interval,
            args=[node_pair["id"]],
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info(f"Scheduled {job_id} every {interval} min")


def remove_node_pair_job(node_pair_id: str):
    job_id = f"nodepair-{node_pair_id}"
    job = scheduler.get_job(job_id)
    if job:
        scheduler.remove_job(job_id)


async def load_all_schedules():
    pairs = await db.node_pairs.find({"schedule_enabled": True}).to_list(1000)
    for pair in pairs:
        schedule_node_pair(pair)


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
