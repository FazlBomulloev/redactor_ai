from sqlalchemy import select, update, delete

from core.models.publication import Publication
from core.models.db_helper import db_helper
from core.repositories.base import BaseRepository


class PublicationRepository(BaseRepository):
    def __init__(self):
        super().__init__(db=db_helper.session_getter, model=Publication)

    async def add(self, name, text, media):
        async with self.db() as session:
            publication = Publication(name=name, text=text, media=media)
            session.add(publication)
            await session.commit()

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

    async def delete(self, pb_id: int):
        async with self.db() as session:
            stmt = delete(self.model).where(self.model.id == pb_id)
            await session.execute(stmt)
            await session.commit()
