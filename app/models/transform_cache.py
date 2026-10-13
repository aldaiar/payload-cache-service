
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TransformCache(Base):
    __tablename__ = "transform_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    input_text: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
    )
    output_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )