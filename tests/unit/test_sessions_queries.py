import pytest

from app.db.queries.sessions import list_sessions


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _RecordingQuery:
    def __init__(self, calls):
        self._calls = calls

    def select(self, *args, **kwargs):
        self._calls.append(("select", args, kwargs))
        return self

    def eq(self, *args, **kwargs):
        self._calls.append(("eq", args, kwargs))
        return self

    def order(self, *args, **kwargs):
        self._calls.append(("order", args, kwargs))
        return self

    def limit(self, *args, **kwargs):
        self._calls.append(("limit", args, kwargs))
        return self

    async def execute(self):
        return _FakeResult([])


class _RecordingDb:
    def __init__(self):
        self.calls: list[tuple] = []

    def table(self, name):
        self.calls.append(("table", name))
        return _RecordingQuery(self.calls)


@pytest.mark.anyio
async def test_list_sessions_orders_desc_and_limits_to_10():
    db = _RecordingDb()

    await list_sessions(db, "user-1", channel="web")

    call_names = [c[0] for c in db.calls]
    assert call_names == ["table", "select", "eq", "eq", "eq", "order", "limit"]

    order_call = next(c for c in db.calls if c[0] == "order")
    assert order_call[1] == ("last_used_at",)
    assert order_call[2] == {"desc": True}

    limit_call = next(c for c in db.calls if c[0] == "limit")
    assert limit_call[1] == (10,)
