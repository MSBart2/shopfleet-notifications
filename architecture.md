# Architecture Reference — shopfleet-notifications

## Service Overview

| Property | Value |
|----------|-------|
| Name | `shopfleet-notifications` |
| Role | Leaf service — no downstream dependents |
| Language | Python 3.11+ |
| Framework | FastAPI |
| Port | `3005` (override via `PORT` env var) |
| State | In-memory only — no database, no persistence across restarts |
| Entry point | `app/main.py` |

## Position in ShopFleet

```
shopfleet-shared ──┐
shopfleet-orders ──┼──▶ shopfleet-notifications
shopfleet-payments─┘
```

This service is a **consumer** of events from orders and payments services. It has no dependents — nothing calls it from within the platform except external orchestrators or API gateways.

## Code Layout

```
shopfleet-notifications/
├── app/
│   ├── __init__.py         # empty
│   └── main.py             # entire application: models, templates, routes
├── Dockerfile
├── pyproject.toml
├── acp-manifest.json
└── architecture.md         # this file
```

All application logic lives in `app/main.py`. There are no sub-modules.

## Data Models

### `NotificationEvent` (inbound)
Accepted by `POST /send`. Fields the caller provides:

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `type` | `NotificationType` (enum) | ✅ | — | See enum values below |
| `user_id` | `str` | ✅ | — | Opaque user identifier |
| `data` | `dict` | ❌ | `{}` | Template interpolation values |
| `channel` | `Channel` (enum) | ❌ | `email` | Delivery channel |

### `Notification` (stored / returned)
Created internally from a `NotificationEvent`. All fields serialise as JSON:

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | `uuid4()` string |
| `user_id` | `str` | Copied from event |
| `type` | `NotificationType` | Copied from event |
| `channel` | `Channel` | Copied from event |
| `subject` | `str` | Rendered from template |
| `body` | `str` | Rendered from template |
| `sent_at` | `str \| None` | UTC ISO 8601 + `Z`; `null` until dispatch runs |
| `created_at` | `str` | UTC ISO 8601 + `Z`; set at creation |

## Enums

### `NotificationType`
| Value | Trigger context |
|-------|----------------|
| `order_confirmed` | Order placed successfully |
| `order_shipped` | Shipment created |
| `order_delivered` | Delivery confirmed |
| `order_disputed` | Customer opened a dispute after delivery |
| `payment_succeeded` | Payment processed |
| `payment_failed` | Payment declined/errored |
| `welcome` | New user registration |

### `Channel`
| Value | Notes |
|-------|-------|
| `email` | Default |
| `sms` | |
| `push` | |

## Endpoints

### `POST /send` → 201
Queue and dispatch a notification.

**Request body** (`application/json`):
```json
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

**Response body** — a `Notification` object:
```json
{
  "id": "a1b2c3d4-...",
  "user_id": "user-123",
  "type": "order_confirmed",
  "channel": "email",
  "subject": "Order Confirmed - #ord-456",
  "body": "Your order #ord-456 has been confirmed! Total: $99.99",
  "sent_at": null,
  "created_at": "2024-01-01T12:00:00.000000Z"
}
```

> `sent_at` is `null` in the immediate response — the background task populates it asynchronously.

---

### `GET /` → 200
List notifications with optional filters.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `user_id` | `str` | Filter to a specific user |
| `sent` | `bool` | `true` = dispatched only, `false` = pending only |

**Response:**
```json
{
  "notifications": [ /* Notification objects */ ],
  "total": 2
}
```

---

### `GET /{notification_id}` → 200 / non-standard 404
Fetch a single notification by UUID.

**Success:** returns a `Notification` object.

**Not found:** returns `({"error": "Not found"}, 404)` — this is a raw tuple return, not an `HTTPException`. FastAPI does not set the HTTP status code correctly with this pattern; it returns 200. **Known issue** — use `HTTPException(status_code=404)` when fixing or extending this route.

---

### `GET /health` → 200
```json
{ "status": "ok", "service": "notifications", "count": 42 }
```

## Template System

Templates are defined as a static dict in `main.py` (`TEMPLATES`). Interpolation uses plain `str.replace` with `{key}` placeholders — **not** Jinja2 (which is installed but unused).

| Type | Subject template | Body template |
|------|-----------------|---------------|
| `order_confirmed` | `Order Confirmed - #{order_id}` | `Your order #{order_id} has been confirmed! Total: ${total}` |
| `order_shipped` | `Your Order Has Shipped!` | `Order #{order_id} is on its way. Track it here: {tracking_url}` |
| `order_delivered` | `Order Delivered` | `Order #{order_id} has been delivered. Enjoy!` |
| `payment_succeeded` | `Payment Successful` | `Payment of ${amount} for order #{order_id} was successful.` |
| `payment_failed` | `Payment Failed` | `Payment for order #{order_id} failed. Please update your payment method.` |
| `welcome` | `Welcome to ShopFleet!` | `Thanks for joining, {name}! Start shopping now.` |

Keys in the `data` dict of the inbound event must match placeholder names exactly (case-sensitive). Unrecognised keys are silently ignored; missing keys leave the placeholder unreplaced.

## Dispatch Flow

```
POST /send
  └─▶ render_template()          # build subject + body
  └─▶ Notification created       # stored in notifications dict
  └─▶ 201 returned to caller
  └─▶ BackgroundTask runs        # FastAPI BackgroundTasks
        └─▶ send_notification()  # sets sent_at, prints to stdout
                                 # no real API call — simulation only
```

## State Store

```python
notifications: dict[str, Notification] = {}  # module-level, in-memory
```

Keyed by `notification.id` (UUID string). Lost on process restart. No locking — concurrent writes are not safe under multi-worker deployments.

## Runtime & Deployment

| Concern | Detail |
|---------|--------|
| Dev server | `uvicorn app.main:app --reload --port 3005` |
| Production image | `python:3.12-slim`; CMD runs uvicorn bound to `0.0.0.0:3005` |
| Multi-worker | Not safe — in-memory store is per-process |
| Config | `PORT` env var (default `3005`) |
