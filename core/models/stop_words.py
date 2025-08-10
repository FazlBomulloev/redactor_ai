from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class StopWords(Base):
    __tablename__ = "stop_words"

    word: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
