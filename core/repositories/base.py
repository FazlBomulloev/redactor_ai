from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound


class BaseRepository:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    async def select_all(self):
        try:
            async with self.db() as session:
                query = await session.execute(select(self.model))
                query = query.scalars().all()
                return query
        except SQLAlchemyError as e:
            print(f"An error occurred while selecting all records: {e}")
            return []

    async def select_id(self, entity_id):
        try:
            async with self.db() as session:
                if isinstance(entity_id, list):
                    sources = []
                    for enti_id in entity_id:
                        try:
                            query = await session.execute(
                                select(self.model).where(self.model.id == int(enti_id))
                            )
                            result = query.scalars().one_or_none()  # Изменено с .one() на .one_or_none()
                            if result:  # Добавлена проверка на None
                                sources.append(result)
                            else:
                                print(f"No result found for entity_id: {enti_id}")
                        except (NoResultFound, ValueError) as e:
                            print(f"Error for entity_id {enti_id}: {e}")
                            continue
                    return sources
                else:
                    try:
                        query = await session.execute(
                            select(self.model).where(self.model.id == int(entity_id))
                        )
                        result = query.scalars().one_or_none()  # Изменено с .one() на .one_or_none()
                        return result  # Может вернуть None, это нормально
                    except ValueError:
                        print(f"Invalid entity_id: {entity_id}")
                        return None
        except SQLAlchemyError as e:
            print(f"An error occurred while selecting by id: {e}")
            return None

    async def select_name(self, name):
        try:
            async with self.db() as session:
                query = await session.execute(
                    select(self.model).where(self.model.name == name)
                )
                query = query.scalars().one_or_none()  # Изменено с .one() на .one_or_none()
                return query
        except SQLAlchemyError as e:
            print(f"An error occurred while selecting by name: {e}")
            return None