from functools import wraps
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv

from core.repositories.admin import AdminRepository

repo_adm = AdminRepository()
super_adm = [6640814090, 817411344, 1097958911]


load_dotenv()


def check_permission(permission_field):
    def decorator(func):
        @wraps(func)
        async def wrapper(callback_query: CallbackQuery, *args, **kwargs):
            user_id = callback_query.from_user.id
            if user_id in super_adm:
                return await func(callback_query, *args, **kwargs)

            admin = await repo_adm.select_adm_id(user_id)
            if not admin or not getattr(admin, permission_field):
                await callback_query.message.answer(
                    "У вас нет прав для выполнения этого действия."
                )
                return
            return await func(callback_query, *args, **kwargs)

        @wraps(func)
        async def message_wrapper(message: Message, state: FSMContext, *args, **kwargs):
            user_id = message.from_user.id
            if user_id in super_adm:
                return await func(message, state, *args, **kwargs)

            admin = await repo_adm.select_adm_id(user_id)
            if not admin or not getattr(admin, permission_field):
                await message.answer("У вас нет прав для выполнения этого действия.")
                return
            return await func(message, state, *args, **kwargs)

        if func.__annotations__.get("callback_query"):
            return wrapper
        elif func.__annotations__.get("message"):
            return message_wrapper
        else:
            raise ValueError(
                "Декоратор поддерживает только функции с аннотациями 'callback_query' или 'message'"
            )

    return decorator
