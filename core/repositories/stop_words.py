from sqlalchemy import select, delete
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

from core.models.stop_words import StopWords
from core.models.db_helper import db_helper
from core.repositories.base import BaseRepository


class StopWordsRepository(BaseRepository):
    def __init__(self):
        super().__init__(db=db_helper.session_getter, model=StopWords)

    async def add(self, word, description=""):
        async with self.db() as session:
            stop_word = self.model(
                word=word,
                description=description,
            )
            session.add(stop_word)
            await session.commit()
            await session.refresh(stop_word)
            return stop_word

    async def get_all_words(self):
        """Получить все стоп-слова как список строк"""
        try:
            async with self.db() as session:
                query = await session.execute(select(self.model))
                stop_words = query.scalars().all()
                return [sw.word for sw in stop_words]
        except SQLAlchemyError as e:
            print(f"An error occurred while getting stop words: {e}")
            return []

    async def delete_word(self, word: str):
        async with self.db() as session:
            stmt = delete(self.model).where(self.model.word == word)
            await session.execute(stmt)
            await session.commit()
