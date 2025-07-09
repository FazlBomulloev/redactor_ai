from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, ForeignKey
from .thematic_block import ThematicBlock
from datetime import datetime, date
from .base import Base


class PublicationSchedule(Base):
    __tablename__ = "publication_schedule"

    time: Mapped[str] = mapped_column(nullable=False)
    ind_pub_id: Mapped[int] = mapped_column(
        ForeignKey("publications.id"), nullable=True
    )
    thematic_block_id: Mapped[str] = mapped_column(
        ForeignKey("thematic_blocks.id"), nullable=False
    )
    today: Mapped[int] = mapped_column(nullable=False)

    thematic_block: Mapped["ThematicBlock"] = relationship("ThematicBlock")
