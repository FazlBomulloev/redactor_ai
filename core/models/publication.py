from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, ForeignKey, String

from .thematic_block import ThematicBlock
from datetime import datetime, date
from .base import Base


class Publication(Base):
    __tablename__ = "publications"

    name: Mapped[str] = mapped_column(String(25), nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    media: Mapped[str] = mapped_column(nullable=True)
