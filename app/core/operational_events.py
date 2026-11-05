"""Best-effort storage for supplementary operational events in MongoDB."""
import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _collection() -> Collection[dict[str, Any]] | None:
    if not settings.mongodb_url:
        return None

    client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=2000)
    return client[settings.mongodb_database]["operational_events"]


def record_event(
    event_type: str,
    entity_type: str,
    entity_id: int | str,
    payload: dict[str, Any] | None = None,
) -> bool:
    """Write one event when configured; MongoDB failures never affect business writes."""
    try:
        collection = _collection()
        if collection is None:
            return False
        collection.insert_one(
            {
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "payload": payload or {},
                "created_at": datetime.now(timezone.utc),
            }
        )
        return True
    except PyMongoError:
        logger.warning("Could not write operational event to MongoDB", exc_info=True)
        return False
