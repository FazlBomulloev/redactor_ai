from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship


from .base import Base


class Folder(Base):
    __tablename__ = "folders"

    name: Mapped[str] = mapped_column(String(25), nullable=False)

    thematic_blocks: Mapped[list["ThematicBlock"]] = relationship(
        "ThematicBlock", back_populates="folder"
    )
