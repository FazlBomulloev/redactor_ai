from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AIApiKey(Base):
    __tablename__ = "ai_api_keys"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)

    # Связь с агентами
    agents: Mapped[list["AIAgent"]] = relationship("AIAgent", back_populates="api_key")


class AIAgent(Base):
    __tablename__ = "ai_agents"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Связь с API ключом
    api_key_id: Mapped[int] = mapped_column(ForeignKey("ai_api_keys.id"), nullable=False)
    api_key: Mapped["AIApiKey"] = relationship("AIApiKey", back_populates="agents")