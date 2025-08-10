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
                            # Добавляем проверку на пустое значение
                            if not enti_id or str(enti_id).strip() == "" or str(enti_id).strip() == "0":
                                print(f"Empty or zero entity_id detected: '{enti_id}'")
                                continue
                                
                            # Конвертируем в int и выполняем запрос
                            int_id = int(str(enti_id).strip())
                            query = await session.execute(
                                select(self.model).where(self.model.id == int_id)
                            )
                            result = query.scalars().one_or_none()
                            if result:
                                sources.append(result)
                            else:
                                print(f"No result found for entity_id: {enti_id} (converted to {int_id}) in table {self.model.__tablename__}")
                        except (ValueError, TypeError) as e:
                            print(f"Invalid entity_id conversion '{enti_id}': {e}")
                            continue
                        except (NoResultFound, SQLAlchemyError) as e:
                            print(f"Database error for entity_id {enti_id}: {e}")
                            continue
                    return sources
                else:
                    try:
                        # Добавляем проверку на пустое значение
                        if not entity_id or str(entity_id).strip() == "" or str(entity_id).strip() == "0":
                            print(f"Empty or zero entity_id detected: '{entity_id}'")
                            return None
                            
                        # Конвертируем в int и выполняем запрос
                        int_id = int(str(entity_id).strip())
                        query = await session.execute(
                            select(self.model).where(self.model.id == int_id)
                        )
                        result = query.scalars().one_or_none()
                        if result is None:
                            print(f"No result found for entity_id: {entity_id} (converted to {int_id}) in table {self.model.__tablename__}")
                        return result
                    except (ValueError, TypeError) as e:
                        print(f"Invalid entity_id conversion '{entity_id}': {e}")
                        return None
        except SQLAlchemyError as e:
            print(f"Database error in select_id: {e}")
            return None

    async def select_name(self, name):
        try:
            async with self.db() as session:
                # Добавляем проверку на пустое имя
                if not name or str(name).strip() == "":
                    print(f"Empty name provided: '{name}'")
                    return None
                    
                query = await session.execute(
                    select(self.model).where(self.model.name == str(name).strip())
                )
                result = query.scalars().one_or_none()
                if result is None:
                    print(f"No result found for name: '{name}' in table {self.model.__tablename__}")
                return result
        except SQLAlchemyError as e:
            print(f"Database error in select_name: {e}")
            return None