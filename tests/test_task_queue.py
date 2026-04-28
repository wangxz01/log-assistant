from typing import Any

from app.services import task_queue


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.values: dict[str, str] = {}
        self.queue: list[str] = []
        self.expirations: dict[str, int] = {}

    def hset(self, key: str, field: str | None = None, value: str | None = None, mapping: dict[str, str] | None = None) -> None:
        self.hashes.setdefault(key, {})
        if mapping:
            self.hashes[key].update(mapping)
        elif field is not None and value is not None:
            self.hashes[key][field] = value

    def expire(self, key: str, ttl: int) -> None:
        self.expirations[key] = ttl

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value
        if ex is not None:
            self.expirations[key] = ex

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def hgetall(self, key: str) -> dict[str, str]:
        return self.hashes.get(key, {})

    def rpush(self, key: str, value: str) -> None:
        assert key == task_queue.TASK_QUEUE_KEY
        self.queue.append(value)

    def blpop(self, key: str, timeout: int = 0) -> tuple[str, str] | None:
        assert key == task_queue.TASK_QUEUE_KEY
        if not self.queue:
            return None
        return key, self.queue.pop(0)


def test_submit_task_enqueues_redis_job(monkeypatch: Any) -> None:
    fake_redis = FakeRedis()
    monkeypatch.setattr(task_queue, "_get_redis", lambda: fake_redis)

    task_id = task_queue.submit_task(log_id=42, user_id=7, user_local_id=3)

    assert fake_redis.hashes[f"task:{task_id}"]["status"] == "pending"
    assert fake_redis.hashes[f"task:{task_id}"]["log_id"] == "42"
    assert fake_redis.values["task:log:7:42"] == task_id
    assert fake_redis.queue == [task_id]
    assert task_queue.get_next_task(timeout=0) == task_id
