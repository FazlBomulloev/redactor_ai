from datetime import datetime, timedelta
from sqlalchemy import select, delete, update
from sqlalchemy.exc import SQLAlchemyError
from core.models.folder import Folder
from core.models.db_helper import db_helper
from core.repositories.base import BaseRepository


class FolderRepository(BaseRepository):
    def __init__(self):
        super().__init__(db=db_helper.session_getter, model=Folder)

    async def add(self, name):
        if not isinstance(name, str):
            raise ValueError("name must be an string")

        async with self.db() as session:
            try:
                folder = Folder(name=name)
                session.add(folder)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                raise RuntimeError(f"Failed to add folder: {e}")

    async def update(self, name: str, column: str, new_value: str):
        async with self.db() as session:
            stmt = (
                update(self.model)
                .where(self.model.name == name)
                .values({column: new_value})
            )

            await session.execute(stmt)
            await session.commit()
            return stmt

    async def delete(self, name: str):
        async with self.db() as session:
            stmt = delete(self.model).where(self.model.name == name)
            await session.execute(stmt)
            await session.commit()
