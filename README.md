# ShopFleet Notifications Service

Event-driven notification dispatch for ShopFleet. Built with Python and FastAPI.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/send` | Queue notification event |
| GET | `/` | List notifications (filter by user_id, sent) |
| GET | `/{id}` | Get notification by ID |
| GET | `/health` | Service health check |

## Notification Types

- `order_confirmed`
- `order_shipped`
- `order_delivered`
- `payment_succeeded`
- `payment_failed`
- `welcome`

## Channels

- `email` (default)
- `sms`
- `push`

## Usage

```json
POST /send
{
  "type": "order_confirmed",
  "user_id": "user-123",
  "data": {
    "order_id": "ord-456",
    "total": "99.99"
  },
  "channel": "email"
}
```

## Development

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 3005
```

Runs on port 3005 by default.

## Part of ShopFleet

This Python service handles async notifications for the ShopFleet microservices demo.
