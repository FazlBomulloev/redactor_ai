from sqlalchemy import Boolean, Integer, Text, Column, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Article(Base):
    __tablename__ = "articles"

    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text)
    created_at = Column(DateTime, nullable=False)
