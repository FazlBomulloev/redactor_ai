from aiogram import types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class CreateKeyboard:
    def __init__(self):
        """Инициализация класса CreateKeyboard."""
        pass

    @staticmethod
    async def create_kb_menu(super_users: list, user_id):
        k_b = InlineKeyboardBuilder()
        btn_thematic_blocks = InlineKeyboardButton(
            text="Тематические блоки", callback_data="thematic_blocks"
        )
        btn_publication_schedule = InlineKeyboardButton(
            text="Расписание публикаций", callback_data="publication_schedule"
        )
        btn_publications = InlineKeyboardButton(
            text="Публикации", callback_data="publications"
        )
        btn_administration = InlineKeyboardButton(
            text="Администрирование", callback_data="administration"
        )
        btn_statistics = InlineKeyboardButton(
            text="Статистика", callback_data="statistics"
        )
        btn_stop_words = InlineKeyboardButton(
            text="Стоп-слова", callback_data="stop_words"
        )
        btn_comments = InlineKeyboardButton(
            text="Комментарии", callback_data="comments"
        )
        k_b.row(btn_thematic_blocks)
        k_b.row(btn_publication_schedule)
        k_b.row(btn_publications)
        if user_id in super_users:
            k_b.row(btn_administration)
        k_b.row(btn_statistics)
        k_b.row(btn_stop_words)
        k_b.row(btn_comments)

        return k_b.as_markup()

    @staticmethod
    async def create_keyboard(buttons, columns=1):
        keyboard_buttons = []
        for i in range(0, len(buttons), columns):
            row = [
                types.KeyboardButton(text=button) for button in buttons[i : i + columns]
            ]
            keyboard_buttons.append(row)
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=keyboard_buttons, resize_keyboard=True
        )
        return keyboard

    @staticmethod
    async def add_publication(names_pub, row=1):
        kb = InlineKeyboardBuilder()
        for i in range(0, len(names_pub), row):
            row_buttons = [
                InlineKeyboardButton(
                    text=name.name,
                    callback_data=f"addpub_{name.name}",
                )
                for name in names_pub[i : i + row]
            ]
            kb.row(*row_buttons)
        btn_back = InlineKeyboardButton(text="Назад", callback_data="publications")
        kb.row(btn_back)
        keyboard = kb.as_markup()
        return keyboard

    @staticmethod
    async def create_publication(names_pub, row=1):
        kb = InlineKeyboardBuilder()
        for i in range(0, len(names_pub), row):
            row_buttons = [
                InlineKeyboardButton(
                    text=name.name,
                    callback_data=f"pub_{name.name}",
                )
                for name in names_pub[i : i + row]
            ]
            kb.row(*row_buttons)
        btn_create_publication = InlineKeyboardButton(
            text="Создать публикацию", callback_data=f"create_publication"
        )
        btn_back = InlineKeyboardButton(text="Назад", callback_data="back_to_main")

        kb.row(btn_create_publication)
        kb.row(btn_back)

        keyboard = kb.as_markup()
        return keyboard

    @staticmethod
    async def create_tb(names_tb, fl_name, row=1):
        k_b = InlineKeyboardBuilder()
        for i in range(0, len(names_tb), row):
            row_buttons = [
                InlineKeyboardButton(
                    text=name.name,
                    callback_data=f"tb_id_{name.id}",  # ИСПРАВЛЕНО: используем ID
                )
                for name in names_tb[i : i + row]
            ]
            k_b.row(*row_buttons)

        k_b.row(
            InlineKeyboardButton(
                text="Изменить имя папки", callback_data=f"changefl_name_{fl_name}"
            )
        )
        k_b.row(
            InlineKeyboardButton(
                text="Удалить папку", callback_data=f"changefl_del_{fl_name}"
            )
        )
        k_b.row(InlineKeyboardButton(text="Создать блок", callback_data="create_block"))
        k_b.row(InlineKeyboardButton(text="Назад", callback_data="thematic_blocks"))
        keyboard = k_b.as_markup()
        return keyboard

    @staticmethod
    async def create_folder(names_fl, row=1):
        k_b = InlineKeyboardBuilder()
        for i in range(0, len(names_fl), row):
            row_buttons = [
                InlineKeyboardButton(
                    text=name.name,
                    callback_data=f"fl_{name.name}",
                )
                for name in names_fl[i : i + row]
            ]
            k_b.row(*row_buttons)

        k_b.row(
            InlineKeyboardButton(text="Создать папку", callback_data="create_folder")
        )
        k_b.row(InlineKeyboardButton(text="Назад", callback_data="back_to_main"))
        keyboard = k_b.as_markup()
        return keyboard

    @staticmethod
    async def create_tb_individual(name):
        """Старая функция для совместимости (использует имя)"""
        kb = InlineKeyboardBuilder()
        btn_change_name = InlineKeyboardButton(
            text="Изменить название", callback_data=f"changetb_name_{name}"
        )
        btn_change_source = InlineKeyboardButton(
            text="Изменить источник", callback_data=f"changetb_source_{name}"
        )
        btn_change_description = InlineKeyboardButton(
            text="Изменить описание", callback_data=f"changetb_description_{name}"
        )
        btn_change_backtime = InlineKeyboardButton(
            text="Изменить время поиска", callback_data=f"changetb_timeback_{name}"
        )
        btn_change_sw = InlineKeyboardButton(
            text="Изменить стоп-слова", callback_data=f"changetb_sw_{name}"
        )
        btn_change_delete = InlineKeyboardButton(
            text="Удалить", callback_data=f"changetb_delete_{name}"
        )
        btn_back = InlineKeyboardButton(text="Назад", callback_data="thematic_blocks")

        kb.row(btn_change_name)
        kb.row(btn_change_source)
        kb.row(btn_change_description)
        kb.row(btn_change_backtime)
        kb.row(btn_change_sw)
        kb.row(btn_change_delete)
        kb.row(btn_back)

        keyboard = kb.as_markup()
        return keyboard

    @staticmethod
    async def create_tb_individual_by_id(block_id, block_name=None):
        """Новая функция для создания клавиатуры по ID блока"""
        kb = InlineKeyboardBuilder()
        
        btn_change_name = InlineKeyboardButton(
            text="Изменить название", callback_data=f"changetb_name_id_{block_id}"
        )
        btn_change_source = InlineKeyboardButton(
            text="Изменить источник", callback_data=f"changetb_source_id_{block_id}"
        )
        btn_change_description = InlineKeyboardButton(
            text="Изменить описание", callback_data=f"changetb_description_id_{block_id}"
        )
        btn_change_backtime = InlineKeyboardButton(
            text="Изменить время поиска", callback_data=f"changetb_timeback_id_{block_id}"
        )
        btn_change_sw = InlineKeyboardButton(
            text="Изменить стоп-слова", callback_data=f"changetb_sw_id_{block_id}"
        )
        btn_change_delete = InlineKeyboardButton(
            text="Удалить", callback_data=f"changetb_delete_id_{block_id}"
        )
        btn_back = InlineKeyboardButton(text="Назад", callback_data="thematic_blocks")

        kb.row(btn_change_name)
        kb.row(btn_change_source)
        kb.row(btn_change_description)
        kb.row(btn_change_backtime)
        kb.row(btn_change_sw)
        kb.row(btn_change_delete)
        kb.row(btn_back)

        return kb.as_markup()

    @staticmethod
    async def create_ps():
        kb = InlineKeyboardBuilder()
        btn_weekday = InlineKeyboardButton(
            text="Будний день", callback_data=f"ps_weekday"
        )
        btn_weekend = InlineKeyboardButton(text="Выходной", callback_data=f"ps_weekend")
        btn_event = InlineKeyboardButton(text="Событие", callback_data=f"event")
        btn_back = InlineKeyboardButton(text="Назад", callback_data="back_to_main")

        kb.row(btn_weekday)
        kb.row(btn_weekend)
        kb.row(btn_event)
        kb.row(btn_back)

        keyboard = kb.as_markup()
        return keyboard

    @staticmethod
    async def create_ps_event():
        kb = InlineKeyboardBuilder()
        btn_list_events = InlineKeyboardButton(
            text="Список событий", callback_data=f"list_events"
        )
        btn_add_event = InlineKeyboardButton(
            text="Добавить событие", callback_data=f"add_event"
        )
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )

        kb.row(btn_list_events)
        kb.row(btn_add_event)
        kb.row(btn_back)

        keyboard = kb.as_markup()
        return keyboard

    @staticmethod
    async def create_adm_list(adm_list):
        k_b = InlineKeyboardBuilder()
        for i in range(0, len(adm_list), 1):
            row_buttons = [
                InlineKeyboardButton(
                    text=f"id {adm.admin_id}",
                    callback_data=f"ad_{adm.admin_id}",
                )
                for adm in adm_list[i : i + 1]
            ]
            k_b.row(*row_buttons)

        k_b.row(InlineKeyboardButton(text="Назад", callback_data="administration"))
        keyboard = k_b.as_markup()
        return keyboard

    @staticmethod
    async def create_rights(adm):
        kb = InlineKeyboardBuilder()
        kb.row(
            InlineKeyboardButton(
                text=f"Тематические блоки || {'Есть' if adm.thematickblock is True else 'Нет'}",
                callback_data=f"show_redact_{adm.thematickblock}_{adm.admin_id}_thematickblock",
            )
        )
        kb.row(
            InlineKeyboardButton(
                text=f"Публикации || {'Есть' if adm.publication is True else 'Нет'}",
                callback_data=f"show_redact_{adm.publication}_{adm.admin_id}_publication",
            )
        )
        kb.row(
            InlineKeyboardButton(
                text=f"Комментарии || {'Есть' if adm.comments is True else 'Нет'}",
                callback_data=f"show_redact_{adm.comments}_{adm.admin_id}_comments",
            )
        )
        kb.row(
            InlineKeyboardButton(
                text=f"События || {'Есть' if adm.event is True else 'Нет'}",
                callback_data=f"show_redact_{adm.event}_{adm.admin_id}_event",
            )
        )
        kb.row(InlineKeyboardButton(text="Назад", callback_data="admin_list"))

        return kb.as_markup()

    @staticmethod
    async def create_ev_individual(name):
        kb = InlineKeyboardBuilder()
        btn_change_name = InlineKeyboardButton(
            text="Изменить название", callback_data=f"evchange_name_{name}"
        )
        btn_change_source = InlineKeyboardButton(
            text="Изменить источник", callback_data=f"evchange_source_{name}"
        )
        btn_change_description = InlineKeyboardButton(
            text="Изменить описание", callback_data=f"evchange_description_{name}"
        )
        btn_change_timein = InlineKeyboardButton(
            text="Изменить время входа", callback_data=f"evchange_time_in_{name}"
        )
        btn_change_timeout = InlineKeyboardButton(
            text="Изменить время выхода", callback_data=f"evchange_time_out_{name}"
        )
        btn_back = InlineKeyboardButton(text="Назад", callback_data="list_events")

        kb.row(btn_change_name)
        kb.row(btn_change_source)
        kb.row(btn_change_description)
        kb.row(btn_change_timein)
        kb.row(btn_change_timeout)
        kb.row(btn_back)

        keyboard = kb.as_markup()
        return keyboard


create_kb = CreateKeyboard()