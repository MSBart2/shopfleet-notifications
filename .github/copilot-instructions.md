# Copilot Instructions — shopfleet-notifications

> For full technical details — endpoints, data models, enums, template contracts, dispatch flow, and deployment — see [architecture.md](../architecture.md).

## Commands

```bash
# Install (including dev deps)
pip install -e ".[dev]"

# Run service (dev)
uvicorn app.main:app --reload --port 3005

# Run all tests
pytest

# Run a single test
pytest tests/test_main.py::test_queue_notification

# Lint
ruff check .
```

## Key Conventions

- Ruff line-length is 100.
- `NotificationType` and `Channel` are `str` + `Enum` subclasses — they serialise as plain strings in JSON automatically.
- All timestamps are UTC ISO 8601 strings built as `datetime.utcnow().isoformat() + "Z"`.
- IDs are `str(uuid.uuid4())`.
- The `GET /{notification_id}` not-found path uses a raw tuple return — **known issue**; use `HTTPException(status_code=404)` when touching that route.
