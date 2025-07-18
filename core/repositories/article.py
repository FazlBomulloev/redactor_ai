# core/repositories/article_repository.py
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from core.models.article import Article
from core.models.db_helper import db_helper
from core.repositories.base import BaseRepository


class ArticleRepository(BaseRepository):
    def __init__(self):
        super().__init__(db=db_helper.session_getter, model=Article)

    async def add(self, message_id, chat_id, content, created_at):
        if not isinstance(message_id, int):
            raise ValueError("message_id must be an integer")
        if not isinstance(chat_id, int):
            raise ValueError("chat_id must be an integer")
        if not isinstance(content, str):
            raise ValueError("text must be a string")

        async with self.db() as session:
            try:
                article = self.model(
                    message_id=message_id,
                    chat_id=chat_id,
                    content=content,
                    created_at=created_at,
                )
                session.add(article)
                await session.commit()
                await session.refresh(article)
                return article
            except SQLAlchemyError as e:
                await session.rollback()
                raise RuntimeError(f"Failed to add article: {e}")

    async def get_chars_count_yesterday(self):
        today = datetime.now()
        yesterday_start = (today - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        yesterday_end = (today - timedelta(days=1)).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        async with self.db() as session:
            try:
                result = await session.execute(
                    select(Article.content).where(
                        Article.created_at >= yesterday_start,
                        Article.created_at <= yesterday_end,
                    )
                )
                publications = result.scalars().all()
                total_chars = sum(len(pub) for pub in publications)
                print(f"Общее количество символов за вчера: {total_chars}")
                return total_chars
            except SQLAlchemyError as e:
                raise RuntimeError(
                    f"Не удалось получить количество символов за вчера: {e}"
                )

    async def get_chars_count_last_30_days(self):
        thirty_days_ago = datetime.now() - timedelta(days=30)
        async with self.db() as session:
            try:
                result = await session.execute(
                    select(Article.content).where(Article.created_at >= thirty_days_ago)
                )
                publications = result.scalars().all()
                return sum(len(pub) for pub in publications)
            except SQLAlchemyError as e:
                raise RuntimeError(f"Failed to get chars count for last 30 days: {e}")

    async def get_avg_chars_per_day(self):
        thirty_days_ago = datetime.now() - timedelta(days=30)
        async with self.db() as session:
            try:
                result = await session.execute(
                    select(Article.content).where(Article.created_at >= thirty_days_ago)
                )
                publications = result.scalars().all()
                total_chars = sum(len(pub) for pub in publications)
                return total_chars / 30
            except SQLAlchemyError as e:
                raise RuntimeError(f"Failed to get average chars per day: {e}")

    async def get_avg_chars_per_publication(self):
        async with self.db() as session:
            try:
                result = await session.execute(select(Article.content))
                publications = result.scalars().all()
                total_chars = sum(len(pub) for pub in publications)
                return total_chars / len(publications) if publications else 0
            except SQLAlchemyError as e:
                raise RuntimeError(f"Failed to get average chars per publication: {e}")

    async def get_publications_count_yesterday(self):
        today = datetime.now()
        yesterday_start = (today - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        yesterday_end = (today - timedelta(days=1)).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        async with self.db() as session:
            try:
                result = await session.execute(
                    select(Article).where(
                        Article.created_at >= yesterday_start,
                        Article.created_at <= yesterday_end,
                    )
                )
                publications = result.scalars().all()
                return len(publications)
            except SQLAlchemyError as e:
                raise RuntimeError(
                    f"Не удалось получить количество публикаций за вчера: {e}"
                )

    async def get_publications_count_last_30_days(self):
        thirty_days_ago = datetime.now() - timedelta(days=30)
        async with self.db() as session:
            try:
                result = await session.execute(
                    select(Article).where(Article.created_at >= thirty_days_ago)
                )
                return len(result.scalars().all())
            except SQLAlchemyError as e:
                raise RuntimeError(
                    f"Failed to get publications count for last 30 days: {e}"
                )

    async def get_statistics(self):
        try:
            yesterday_chars = await self.get_chars_count_yesterday()
            last_30_days_chars = await self.get_chars_count_last_30_days()
            avg_chars_per_day = await self.get_avg_chars_per_day()
            avg_chars_per_publication = await self.get_avg_chars_per_publication()
            yesterday_publications = await self.get_publications_count_yesterday()
            last_30_days_publications = await self.get_publications_count_last_30_days()

            return {
                "yesterday_chars": yesterday_chars,
                "last_30_days_chars": last_30_days_chars,
                "avg_chars_per_day": avg_chars_per_day,
                "avg_chars_per_publication": avg_chars_per_publication,
                "yesterday_publications": yesterday_publications,
                "last_30_days_publications": last_30_days_publications,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get statistics: {e}")

    async def get_all_copied_message_ids(self):
        async with self.db() as session:
            try:
                result = await session.execute(select(Article.message_id))
                return {row[0] for row in result.all()}
            except SQLAlchemyError as e:
                raise RuntimeError(f"Failed to get all copied message IDs: {e}")