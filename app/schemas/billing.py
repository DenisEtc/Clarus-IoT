from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class SubscriptionStatusOut(BaseModel):
    has_active: bool
    ends_at: datetime | None
    remaining_days: int


class RenewIn(BaseModel):
    plan_code: str = Field(default="MONTHLY_1M")


class RenewOut(BaseModel):
    payment_id: uuid.UUID
    subscription_id: uuid.UUID
    ends_at: datetime
