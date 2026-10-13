import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Payload, TransformCache
from app.schemas.payload import PayloadCreate
from app.services.transformer import transform


class PayloadService:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def make_request_hash(data: PayloadCreate) -> str:
        canonical = json.dumps(
            {
                "list_1": data.list_1,
                "list_2": data.list_2,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get_or_transform(self, value: str) -> str:
        cached = self.session.scalar(
            select(TransformCache).where(
                TransformCache.input_text == value
            )
        )

        if cached is not None:
            return cached.output_text

        result = transform(value)

        self.session.add(
            TransformCache(
                input_text=value,
                output_text=result,
            )
        )
        self.session.flush()

        return result

    def create_payload(self, data: PayloadCreate) -> str:
        request_hash = self.make_request_hash(data)

        existing = self.session.scalar(
            select(Payload).where(
                Payload.request_hash == request_hash
            )
        )

        if existing is not None:
            return existing.id

        transformed_1 = [
            self.get_or_transform(value)
            for value in data.list_1
        ]
        transformed_2 = [
            self.get_or_transform(value)
            for value in data.list_2
        ]

        output_parts = [
            item
            for pair in zip(transformed_1, transformed_2)
            for item in pair
        ]

        payload = Payload(
            id=str(uuid.uuid4()),
            request_hash=request_hash,
            output=", ".join(output_parts),
        )

        self.session.add(payload)
        self.session.flush()

        return payload.id

    def get_payload(self, payload_id: str) -> Payload | None:
        return self.session.get(Payload, payload_id)