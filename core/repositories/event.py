from os import times
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from core.models.event import Event
from core.models.db_helper import db_helper
from core.repositories.base import BaseRepository


class EventRepository(BaseRepository):
    def __init__(self):
        super().__init__(db=db_helper.session_getter, model=Event)

    async def add(
        self, name, source, description, stop_description, interval, time_in, time_out
    ):
        try:
            async with self.db() as session:
                event = self.model(
                    name=name,
                    source=source,
                    description=description,
                    stop_description=stop_description,
                    interval=interval,
                    time_in=time_in,
                    time_out=time_out,
                )
                session.add(event)
                await session.commit()
                await session.refresh(event)
                return event
        except IntegrityError as e:
            print(f"Integrity error occurred while adding event: {e}")
        except SQLAlchemyError as e:
            print(f"An error occurred while adding event: {e}")
        return None

    async def update(self, id: int, column: str, new_value: str):
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
        except NoResultFound:
            print(f"No result found for name: {id}")
        except SQLAlchemyError as e:
            print(f"An error occurred while updating event: {e}")
        return None

    async def delete(self, ev_id: int):
        try:
            async with self.db() as session:
                stmt = delete(self.model).where(self.model.id == ev_id)
                await session.execute(stmt)
                await session.commit()
        except NoResultFound:
            print(f"No result found for event_id: {ev_id}")
        except SQLAlchemyError as e:
            print(f"An error occurred while deleting event: {e}")
        return None
