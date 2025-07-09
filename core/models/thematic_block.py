from sqlalchemy import ARRAY, String, JSON, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ThematicBlock(Base):
    __tablename__ = "thematic_blocks"

    name: Mapped[str] = mapped_column(String(25), nullable=False)
    source: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    time_back: Mapped[int] = mapped_column(Integer)
    stop_words: Mapped[str] = mapped_column(String)

    folder_id: Mapped[int] = mapped_column(ForeignKey("folders.id"), nullable=False)

    folder: Mapped["Folder"] = relationship("Folder", back_populates="thematic_blocks")
