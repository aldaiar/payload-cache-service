
import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Payload(Base):
    __tablename__ = "payloads"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    request_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    output: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )