import hashlib
import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from src.common.models import Currency, PaymentStatus


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    currency: Currency
    description: str = Field("", max_length=1024)
    metadata: dict[str, Any] = {}
    webhook_url: HttpUrl

    def get_hash(self) -> str:
        data = self.model_dump(mode="json")
        data["amount"] = str(self.amount.quantize(Decimal("0.01")))
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


class PaymentAccepted(BaseModel):
    payment_id: uuid.UUID
    status: PaymentStatus
    created_at: datetime


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: uuid.UUID = Field(validation_alias="id")
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any] = Field(validation_alias="meta")
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
    notified_at: datetime | None
