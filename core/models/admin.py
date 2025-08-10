from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Admin(Base):
    __tablename__ = "admins"

    admin_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    thematickblock: Mapped[int] = mapped_column(Boolean, nullable=False, default=False)
    publication: Mapped[int] = mapped_column(Boolean, nullable=False, default=False)
    comments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    event: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
