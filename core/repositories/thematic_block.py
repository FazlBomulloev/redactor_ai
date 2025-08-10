# core/repositories/thematic_block.py (исправленная версия)
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

from core.models.thematic_block import ThematicBlock
from core.models.db_helper import db_helper
from core.repositories.base import BaseRepository


class ThematicBlockRepository(BaseRepository):
    def __init__(self):
        super().__init__(db=db_helper.session_getter, model=ThematicBlock)

    async def add(self, name, source, description, time_back, stop_words, folder):
        async with self.db() as session:
            block = self.model(
                name=name,
                source=source,
                description=description,
                time_back=time_back,
                stop_words=stop_words,
                folder=folder,
            )
            session.add(block)
            await session.commit()
            await session.refresh(block)

    async def select_id_folder(self, id):
        try:
            async with self.db() as session:
                query = await session.execute(
                    select(self.model).where(self.model.folder_id == id)
                )
                query = query.scalars().all()
                return query
        except NoResultFound:
            print(f"No result found for name: {id}")
            return None
        except SQLAlchemyError as e:
            print(f"An error occurred while selecting by name: {e}")
            return None

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

    async def update_by_id(self, id: int, column: str, new_value):
        """Обновление тематического блока по ID"""
        try:
            async with self.db() as session:
                stmt = (
                    update(self.model)
                    .where(self.model.id == id)
                    .values({column: new_value})
                )
                await session.execute(stmt)
                await session.commit()
                return stmt
        except SQLAlchemyError as e:
            print(f"An error occurred while updating by id: {e}")
            return None

    async def delete(self, pb_id: int):
        async with self.db() as session:
            stmt = delete(self.model).where(self.model.id == pb_id)
            await session.execute(stmt)
            await session.commit()

    async def delete_fl_id(self, fl_id: int):
        async with self.db() as session:
            stmt = delete(self.model).where(self.model.folder_id == fl_id)
            await session.execute(stmt)
            await session.commit()