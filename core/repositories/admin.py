from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

from core.models.admin import Admin
from core.models.db_helper import db_helper
from core.repositories.base import BaseRepository


class AdminRepository(BaseRepository):
    def __init__(self):
        super().__init__(db=db_helper.session_getter, model=Admin)

    async def add(self, admin_id):
        if not isinstance(admin_id, int):
            raise ValueError("admin_id must be an integer")

        async with self.db() as session:
            try:
                admin = Admin(admin_id=admin_id)
                session.add(admin)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                raise RuntimeError(f"Failed to add admin: {e}")

    async def select_adm_id(self, admin_id):
        if not isinstance(admin_id, int):
            raise ValueError("admin_id must be an integer")

        async with self.db() as session:
            try:
                query = await session.execute(
                    select(self.model).where(self.model.admin_id == admin_id)
                )
                admin = query.scalars().one()
                return admin
            except NoResultFound:
                raise ValueError(f"No admin found with id {admin_id}")
            except SQLAlchemyError as e:
                raise RuntimeError(f"Failed to select admin: {e}")

    async def update(self, adm_id: int, column: str, new_value: bool):
        if not isinstance(adm_id, int):
            raise ValueError("adm_id must be an integer")
        if not isinstance(column, str):
            raise ValueError("column must be a string")
        if not isinstance(new_value, bool):
            raise ValueError("new_value must be a boolean")

        async with self.db() as session:
            try:
                query = select(self.model).where(self.model.admin_id == adm_id)
                result = await session.execute(query)
                admin = result.scalars().one()

                if hasattr(admin, column):
                    setattr(admin, column, new_value)
                    await session.commit()
                    await session.refresh(admin)
                    return admin
                else:
                    raise ValueError(
                        f"Column {column} does not exist on model {self.model.__name__}"
                    )
            except NoResultFound:
                raise ValueError(f"No admin found with id {adm_id}")
            except SQLAlchemyError as e:
                await session.rollback()
                raise RuntimeError(f"Failed to update admin: {e}")

    async def delete(self, adm_id: int):
        if not isinstance(adm_id, int):
            raise ValueError("adm_id must be an integer")

        async with self.db() as session:
            try:
                stmt = delete(self.model).where(self.model.admin_id == adm_id)
                await session.execute(stmt)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                raise RuntimeError(f"Failed to delete admin: {e}")
