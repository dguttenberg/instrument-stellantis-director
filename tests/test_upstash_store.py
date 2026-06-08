"""UpstashDraftStore conforms to the DraftStore protocol, driven by an in-memory
fake of the Upstash REST client (no live Redis needed)."""

from director_agent.draftstore.upstash_store import UpstashDraftStore
from director_agent.schemas.cell import CellOutputEnvelope


class FakeRedis:
    """Minimal in-memory stand-in for upstash_redis.Redis (set/get/sadd/smembers/mget)."""

    def __init__(self):
        self.kv = {}
        self.sets = {}

    def set(self, key, value):
        self.kv[key] = value

    def get(self, key):
        return self.kv.get(key)

    def sadd(self, key, *members):
        self.sets.setdefault(key, set()).update(members)

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def mget(self, *keys):
        return [self.kv.get(k) for k in keys]


def _envelope(cell_id, confidence="high"):
    return CellOutputEnvelope.model_validate(
        {
            "cell_id": cell_id,
            "cell_type": "existing_running_footage",
            "outputs": [
                {
                    "type": "twelvelabs_query",
                    "confidence": confidence,
                    "query": {"tags": ["ram_1500"], "natural_language": "ram driving"},
                }
            ],
        }
    )


def test_put_get_list_approve_roundtrip():
    store = UpstashDraftStore(url="x", token="y", client=FakeRedis())

    rec = store.put(_envelope("c1", "high"))
    assert rec.review_status == "auto_accept" and rec.approved is True

    rec2 = store.put(_envelope("c2", "medium"))
    assert rec2.review_status == "needs_approve" and rec2.approved is False

    assert store.get("c1").cell_id == "c1"
    assert {r.cell_id for r in store.list()} == {"c1", "c2"}

    approved = store.approve("c2")
    assert approved.approved is True
    assert store.get("c2").approved is True

    assert store.get("missing") is None
    assert store.approve("missing") is None


def test_empty_list():
    store = UpstashDraftStore(url="x", token="y", client=FakeRedis())
    assert store.list() == []
