from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid
import os

app = FastAPI(title="ShopFleet Notifications", version="1.0.0")

class NotificationType(str, Enum):
    order_confirmed = "order_confirmed"
    order_shipped = "order_shipped"
    order_delivered = "order_delivered"
    payment_succeeded = "payment_succeeded"
    payment_failed = "payment_failed"
    welcome = "welcome"

class Channel(str, Enum):
    email = "email"
    sms = "sms"
    push = "push"

class Notification(BaseModel):
    id: str
    user_id: str
    type: NotificationType
    channel: Channel
    subject: str
    body: str
    sent_at: Optional[str] = None
    created_at: str

class NotificationEvent(BaseModel):
    type: NotificationType
    user_id: str
    data: dict = {}
    channel: Channel = Channel.email

# In-memory store
notifications: dict[str, Notification] = {}

# Email templates (simplified)
TEMPLATES = {
    NotificationType.order_confirmed: {
        "subject": "Order Confirmed - #{order_id}",
        "body": "Your order #{order_id} has been confirmed! Total: ${total}"
    },
    NotificationType.order_shipped: {
        "subject": "Your Order Has Shipped!",
        "body": "Order #{order_id} is on its way. Track it here: {tracking_url}"
    },
    NotificationType.order_delivered: {
        "subject": "Order Delivered",
        "body": "Order #{order_id} has been delivered. Enjoy!"
    },
    NotificationType.payment_succeeded: {
        "subject": "Payment Successful",
        "body": "Payment of ${amount} for order #{order_id} was successful."
    },
    NotificationType.payment_failed: {
        "subject": "Payment Failed",
        "body": "Payment for order #{order_id} failed. Please update your payment method."
    },
    NotificationType.welcome: {
        "subject": "Welcome to ShopFleet!",
        "body": "Thanks for joining, {name}! Start shopping now."
    },
}

def render_template(notification_type: NotificationType, data: dict) -> tuple[str, str]:
    template = TEMPLATES.get(notification_type, {"subject": "Notification", "body": "You have a new notification."})
    subject = template["subject"]
    body = template["body"]
    for key, value in data.items():
        subject = subject.replace(f"{{{key}}}", str(value))
        body = body.replace(f"{{{key}}}", str(value))
    return subject, body

def send_notification(notification: Notification):
    """Simulate sending (just marks as sent after delay)"""
    # In real implementation: call email/SMS/push API
    notification.sent_at = datetime.utcnow().isoformat() + "Z"
    notifications[notification.id] = notification
    print(f"[SENT] {notification.channel.value}: {notification.subject} to user {notification.user_id}")

@app.get("/health")
def health():
    return {"status": "ok", "service": "notifications", "count": len(notifications)}

@app.post("/send", status_code=201)
def queue_notification(event: NotificationEvent, background_tasks: BackgroundTasks):
    subject, body = render_template(event.type, event.data)
    
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=event.user_id,
        type=event.type,
        channel=event.channel,
        subject=subject,
        body=body,
        created_at=datetime.utcnow().isoformat() + "Z",
    )
    notifications[notification.id] = notification
    
    # Send async
    background_tasks.add_task(send_notification, notification)
    
    return notification

@app.get("/")
def list_notifications(user_id: Optional[str] = None, sent: Optional[bool] = None):
    results = list(notifications.values())
    if user_id:
        results = [n for n in results if n.user_id == user_id]
    if sent is not None:
        results = [n for n in results if (n.sent_at is not None) == sent]
    return {"notifications": results, "total": len(results)}

@app.get("/{notification_id}")
def get_notification(notification_id: str):
    if notification_id not in notifications:
        return {"error": "Not found"}, 404
    return notifications[notification_id]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3005"))
    uvicorn.run(app, host="0.0.0.0", port=port)
