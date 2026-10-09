import ctypes
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import files_core as core

TITLE = 'Управление каталогами'
ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons')
PARENT_NAME = '..'

SIZE_OPERATORS = [('больше', '>'), ('меньше', '<'), ('не меньше', '>='), ('не больше', '<='), ('равен', '=')]
SIZE_UNITS = [('байт', 1), ('КБ', 1024), ('МБ', 1024 ** 2), ('ГБ', 1024 ** 3)]
CONTROL_KEYS = {65: 'select_all', 70: 'select_by_pattern', 79: 'choose_directory'}
COLUMNS = [('size', 'Размер', 110, 'e'), ('attributes', 'Атрибуты', 90, 'w'), ('modified', 'Изменён', 140, 'w')]
PREVIEW_LIMIT = 8
MESSAGE_TIME = 8000
SETTINGS_PATH = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'menu_explorer_settings.json')
DEFAULT_SETTINGS = {
    'non_empty': 'ask',
    'confirm_recycle': False,
    'confirm_permanent': True,
    'columns': [],
}


def load_settings():
    settings = dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, encoding='utf-8') as file:
            saved = json.load(file)
        for key in settings:
            if key in saved and type(saved[key]) is type(settings[key]):
                settings[key] = saved[key]
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings):
    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as file:
            json.dump(settings, file, ensure_ascii=False, indent=2)
    except OSError:
        pass

HELP_TEXT = (
    'Программа показывает содержимое текущего каталога и удаляет файлы и каталоги.\n\n'
    'Переход в каталог — двойной щелчок по нему или Enter. Строка «..» вверху списка — '
    'переход на уровень выше (также Backspace). Перейти в любой каталог можно через '
    '«Файл → Открыть каталог…» или вписав путь в адресную строку.\n\n'
    'Размер, атрибуты и дата изменения включаются в меню «Вид».\n\n'
    'Удаление: выделите файлы и каталоги (несколько — мышью с Ctrl или Shift) и выберите '
    '«Правка → Удалить в корзину» (Delete) или «Удалить безвозвратно» (Shift+Delete). '
    'Группу файлов или каталогов можно выделить по шаблону имени и весу: «Правка → Выделить по шаблону…» (Ctrl+F).\n\n'
    'Шаблон: * — любые символы, ? — один символ. Например: * — всё, *.txt — по расширению, '
    'отчёт* — начинается с «отчёт», *копия* — содержит «копия».\n\n'
    'Файлы «только для чтения» не удаляются. Для каждого непустого каталога программа спрашивает, удалять ли его.\n\n'
    'В «Сервис → Настройки…» можно выбрать, что делать с непустыми каталогами без вопроса, '
    'и включить или выключить подтверждение удаления.'
)


def load_icon(name):
    return tk.PhotoImage(file=os.path.join(ICON_DIR, name))


def center_over(window, parent):
    window.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - window.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - window.winfo_height()) // 3
    window.geometry('+%d+%d' % (max(x, 0), max(y, 0)))


class PatternDialog(tk.Toplevel):
    def __init__(self, parent, entries):
        super().__init__(parent)
        self.title('Выделить по шаблону')
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self.entries = entries

        self.pattern = tk.StringVar(value='*')
        self.kind = tk.StringVar(value='files')
        self.use_weight = tk.BooleanVar(value=False)
        self.weight_operator = tk.StringVar(value=SIZE_OPERATORS[0][0])
        self.weight_value = tk.StringVar(value='100')
        self.weight_unit = tk.StringVar(value='КБ')

        frame = ttk.Frame(self, padding=14)
        frame.grid(sticky='nsew')

        ttk.Label(frame, text='Шаблон имени:').grid(row=0, column=0, sticky='w', pady=(0, 2))
        self.pattern_entry = ttk.Entry(frame, textvariable=self.pattern, width=40)
        self.pattern_entry.grid(row=0, column=1, sticky='we', pady=(0, 2))
        ttk.Label(frame, text='* — любые символы, ? — один символ.\nНапример: *.txt, отчёт*, *копия*',
                  foreground='#555555').grid(row=1, column=1, sticky='w', pady=(0, 10))

        ttk.Label(frame, text='Выделять:').grid(row=2, column=0, sticky='w')
        kinds = ttk.Frame(frame)
        kinds.grid(row=2, column=1, sticky='w')
        ttk.Radiobutton(kinds, text='файлы', variable=self.kind, value='files').pack(side='left')
        ttk.Radiobutton(kinds, text='каталоги', variable=self.kind, value='folders').pack(side='left', padx=(12, 0))

        self.weight_check = ttk.Checkbutton(frame, text='Вес', variable=self.use_weight)
        self.weight_check.grid(row=3, column=0, sticky='w', pady=(10, 0))
        weight_row = ttk.Frame(frame)
        weight_row.grid(row=3, column=1, sticky='w', pady=(10, 0))
        ttk.Combobox(weight_row, textvariable=self.weight_operator, values=[name for name, _ in SIZE_OPERATORS],
                     state='readonly', width=11).pack(side='left')
        ttk.Spinbox(weight_row, textvariable=self.weight_value, from_=0, to=10 ** 9, width=10).pack(side='left', padx=6)
        ttk.Combobox(weight_row, textvariable=self.weight_unit, values=[name for name, _ in SIZE_UNITS],
                     state='readonly', width=6).pack(side='left')

        self.summary = ttk.Label(frame, text='')
        self.summary.grid(row=4, column=0, columnspan=2, sticky='w', pady=(14, 10))

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=2, sticky='e')
        self.select_button = ttk.Button(buttons, text='Выделить', command=self.accept, default='active')
        self.select_button.pack(side='left', padx=(0, 6))
        ttk.Button(buttons, text='Отмена', command=self.destroy).pack(side='left')

        for variable in (self.pattern, self.kind, self.use_weight, self.weight_operator, self.weight_value, self.weight_unit):
            variable.trace_add('write', lambda *args: self.update_summary())
        self.bind('<Return>', lambda event: self.accept())
        self.bind('<Escape>', lambda event: self.destroy())
        self.update_summary()

        center_over(self, parent)
        self.pattern_entry.focus_set()
        self.pattern_entry.select_range(0, 'end')
        self.grab_set()

    def matching(self):
        pattern = self.pattern.get().strip()
        if pattern == '':
            raise ValueError('Введите шаблон имени.')
        want_dir = self.kind.get() == 'folders'
        rules = []
        if self.use_weight.get() and not want_dir:
            try:
                value = float(self.weight_value.get().replace(',', '.'))
            except ValueError:
                raise ValueError('Вес должен быть числом.') from None
            if value < 0:
                raise ValueError('Вес не может быть отрицательным.')
            rules.append(core.SizeRule(dict(SIZE_OPERATORS)[self.weight_operator.get()],
                                       int(value * dict(SIZE_UNITS)[self.weight_unit.get()])))
        return [entry for entry in self.entries
                if entry.is_dir == want_dir and core.matches(entry.name, pattern) and core.size_fits(entry, rules)]

    def update_summary(self):
        self.weight_check.state(['disabled'] if self.kind.get() == 'folders' else ['!disabled'])
        try:
            found = self.matching()
        except ValueError as error:
            self.summary.configure(text=str(error), foreground='#c00000')
            self.select_button.state(['disabled'])
            return None
        self.summary.configure(text='Подходит: ' + core.entries_text(found), foreground='')
        self.select_button.state(['!disabled'])
        return found

    def accept(self):
        found = self.update_summary()
        if found is not None:
            self.result = found
            self.destroy()


class FolderQuestion(tk.Toplevel):
    def __init__(self, parent, entry, count):
        super().__init__(parent)
        self.title('Каталог не пуст')
        self.resizable(False, False)
        self.transient(parent)
        self.result = 4
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        frame = ttk.Frame(self, padding=16)
        frame.grid(sticky='nsew')
        ttk.Label(frame, text='Каталог «' + entry.name + '» не пуст: внутри ' + core.items_text(count) + '.\n'
                              'Удалить его вместе с содержимым?').grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 14))
        buttons = [
            ('Удалить', 1),
            ('Пропустить', 2),
            ('Удалить все', 3),
            ('Пропустить все', 4),
        ]
        for column, (text, value) in enumerate(buttons):
            button = ttk.Button(frame, text=text, command=lambda value=value: self.choose(value))
            button.grid(row=1, column=column, padx=(0 if column == 0 else 6, 0))
            if value == 1:
                button.focus_set()
        ttk.Label(frame, text='«Удалить все» и «Пропустить все» применяются к этому и всем следующим непустым каталогам.',
                  foreground='#555555').grid(row=2, column=0, columnspan=4, sticky='w', pady=(12, 0))
        self.bind('<Escape>', lambda event: self.choose(2))
        center_over(self, parent)
        self.grab_set()

    def choose(self, value):
        self.result = value
        self.destroy()


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.title('Настройки')
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self.non_empty = tk.StringVar(value=settings['non_empty'])
        self.confirm_recycle = tk.BooleanVar(value=settings['confirm_recycle'])
        self.confirm_permanent = tk.BooleanVar(value=settings['confirm_permanent'])

        frame = ttk.Frame(self, padding=14)
        frame.grid(sticky='nsew')

        folders = ttk.LabelFrame(frame, text='Непустые каталоги при удалении', padding=(10, 6))
        folders.grid(row=0, column=0, sticky='we')
        for text, value in [('спрашивать для каждого каталога', 'ask'),
                            ('удалять вместе с содержимым без вопроса', 'delete'),
                            ('пропускать без вопроса (удалять только пустые)', 'skip')]:
            ttk.Radiobutton(folders, text=text, variable=self.non_empty, value=value).pack(anchor='w', pady=1)

        confirm = ttk.LabelFrame(frame, text='Подтверждение удаления', padding=(10, 6))
        confirm.grid(row=1, column=0, sticky='we', pady=(10, 0))
        ttk.Checkbutton(confirm, text='спрашивать перед удалением в корзину',
                        variable=self.confirm_recycle).pack(anchor='w', pady=1)
        ttk.Checkbutton(confirm, text='спрашивать перед безвозвратным удалением',
                        variable=self.confirm_permanent).pack(anchor='w', pady=1)

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, sticky='e', pady=(14, 0))
        ttk.Button(buttons, text='ОК', command=self.accept, default='active').pack(side='left', padx=(0, 6))
        ttk.Button(buttons, text='Отмена', command=self.destroy).pack(side='left')
        self.bind('<Return>', lambda event: self.accept())
        self.bind('<Escape>', lambda event: self.destroy())
        center_over(self, parent)
        self.grab_set()

    def accept(self):
        self.result = {
            'non_empty': self.non_empty.get(),
            'confirm_recycle': self.confirm_recycle.get(),
            'confirm_permanent': self.confirm_permanent.get(),
        }
        self.destroy()


class Explorer:
    def __init__(self, root, directory):
        self.root = root
        self.directory = directory
        self.entries = []
        self.items = {}
        self.parent_item = None
        self.address = tk.StringVar()
        self.settings = load_settings()
        self.visible = {key: tk.BooleanVar(value=key in self.settings['columns']) for key, _, _, _ in COLUMNS}
        self.message = ''
        self.message_timer = None
        self.folder_icon = load_icon('folder-16.png')
        self.file_icon = load_icon('file-16.png')
        self.window_icon = load_icon('folder-32.png')

        root.title(TITLE)
        root.iconphoto(True, self.window_icon, self.folder_icon)
        root.geometry('900x580')
        root.minsize(600, 360)
        self.build_menu()
        self.build_toolbar()
        self.build_list()
        self.build_status()
        self.bind_keys()
        self.open_directory(directory)

    def build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label='Открыть каталог…', accelerator='Ctrl+O', command=self.choose_directory)
        file_menu.add_command(label='Вверх', accelerator='Backspace', command=self.go_up)
        file_menu.add_command(label='Обновить', accelerator='F5', command=self.refresh)
        file_menu.add_separator()
        file_menu.add_command(label='Выход', accelerator='Alt+F4', command=self.root.destroy)
        menubar.add_cascade(label='Файл', menu=file_menu, underline=0)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label='Удалить в корзину', accelerator='Delete', command=lambda: self.delete_selected(False))
        edit_menu.add_command(label='Удалить безвозвратно', accelerator='Shift+Delete', command=lambda: self.delete_selected(True))
        edit_menu.add_separator()
        edit_menu.add_command(label='Выделить всё', accelerator='Ctrl+A', command=self.select_all)
        edit_menu.add_command(label='Снять выделение', accelerator='Esc', command=self.clear_selection)
        edit_menu.add_command(label='Выделить по шаблону…', accelerator='Ctrl+F', command=self.select_by_pattern)
        menubar.add_cascade(label='Правка', menu=edit_menu, underline=0)

        view_menu = tk.Menu(menubar, tearoff=False)
        for key, title, _, _ in COLUMNS:
            view_menu.add_checkbutton(label=title, variable=self.visible[key], command=self.update_columns)
        view_menu.add_separator()
        view_menu.add_command(label='Показать всё', command=lambda: self.set_all_columns(True))
        view_menu.add_command(label='Только имена', command=lambda: self.set_all_columns(False))
        menubar.add_cascade(label='Вид', menu=view_menu, underline=0)

        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label='Настройки…', command=self.open_settings)
        menubar.add_cascade(label='Сервис', menu=tools_menu, underline=0)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label='Как пользоваться', accelerator='F1', command=self.show_help)
        help_menu.add_command(label='О программе', command=self.show_about)
        menubar.add_cascade(label='Справка', menu=help_menu, underline=0)

        self.root.configure(menu=menubar)

        self.context_menu = tk.Menu(self.root, tearoff=False)
        self.context_menu.add_command(label='Открыть', accelerator='Enter', command=self.open_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label='Удалить в корзину', accelerator='Delete', command=lambda: self.delete_selected(False))
        self.context_menu.add_command(label='Удалить безвозвратно', accelerator='Shift+Delete', command=lambda: self.delete_selected(True))
        self.context_menu.add_separator()
        self.context_menu.add_command(label='Выделить всё', accelerator='Ctrl+A', command=self.select_all)
        self.context_menu.add_command(label='Выделить по шаблону…', accelerator='Ctrl+F', command=self.select_by_pattern)
        self.context_menu.add_separator()
        self.context_menu.add_command(label='Обновить', accelerator='F5', command=self.refresh)

    def build_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=(6, 6, 6, 4))
        toolbar.pack(side='top', fill='x')
        ttk.Button(toolbar, text='Обновить', command=self.refresh).pack(side='left')
        ttk.Button(toolbar, text='Удалить', command=lambda: self.delete_selected(False)).pack(side='left', padx=(8, 0))
        ttk.Button(toolbar, text='Выделить по шаблону…', command=self.select_by_pattern).pack(side='left', padx=(4, 0))
        ttk.Label(toolbar, text='Адрес:').pack(side='left', padx=(16, 4))
        self.address_entry = ttk.Entry(toolbar, textvariable=self.address)
        self.address_entry.pack(side='left', fill='x', expand=True)
        self.address_entry.bind('<Return>', lambda event: self.go_to_address())
        ttk.Button(toolbar, text='Перейти', command=self.go_to_address).pack(side='left', padx=(4, 0))

    def build_list(self):
        frame = ttk.Frame(self.root, padding=(6, 0, 6, 0))
        frame.pack(side='top', fill='both', expand=True)
        self.tree = ttk.Treeview(frame, columns=[key for key, _, _, _ in COLUMNS], selectmode='extended')
        self.tree.heading('#0', text='Имя', anchor='w')
        self.tree.column('#0', width=380, anchor='w')
        for key, title, width, anchor in COLUMNS:
            self.tree.heading(key, text=title, anchor=anchor)
            self.tree.column(key, width=width, anchor=anchor, stretch=False)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.update_columns()

        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Return>', lambda event: self.open_selected())
        self.tree.bind('<Delete>', lambda event: self.delete_selected(False))
        self.tree.bind('<Shift-Delete>', lambda event: self.delete_selected(True))
        self.tree.bind('<BackSpace>', lambda event: self.go_up())
        self.tree.bind('<Escape>', lambda event: self.clear_selection())
        self.tree.bind('<Button-3>', self.show_context_menu)
        self.tree.bind('<<TreeviewSelect>>', lambda event: self.update_status())

    def build_status(self):
        self.status = ttk.Label(self.root, text='', anchor='w', padding=(8, 4), relief='sunken')
        self.status.pack(side='bottom', fill='x')

    def bind_keys(self):
        self.root.bind('<F5>', lambda event: self.refresh())
        self.root.bind('<F1>', lambda event: self.show_help())
        self.root.bind('<Control-KeyPress>', self.on_control_key)

    def on_control_key(self, event):
        action = CONTROL_KEYS.get(event.keycode)
        if action is None:
            return None
        if action == 'select_all' and event.widget is not self.tree:
            return None
        getattr(self, action)()
        return 'break'

    def update_columns(self):
        shown = [key for key, _, _, _ in COLUMNS if self.visible[key].get()]
        self.tree.configure(displaycolumns=shown if shown else ())
        if self.settings['columns'] != shown:
            self.settings['columns'] = shown
            save_settings(self.settings)

    def open_settings(self):
        dialog = SettingsDialog(self.root, self.settings)
        self.root.wait_window(dialog)
        if dialog.result is not None:
            self.settings.update(dialog.result)
            save_settings(self.settings)
            self.show_message('Настройки сохранены')

    def set_all_columns(self, value):
        for variable in self.visible.values():
            variable.set(value)
        self.update_columns()

    def open_directory(self, directory):
        try:
            entries = core.list_directory(directory)
        except OSError as error:
            messagebox.showerror(TITLE, 'Не удалось открыть каталог:\n' + directory + '\n\n' + (error.strerror or str(error)))
            self.address.set(self.directory)
            return False
        self.directory = directory
        self.entries = entries
        self.address.set(directory)
        self.root.title(TITLE + ' — ' + directory)
        self.show_entries()
        children = self.tree.get_children()
        if children:
            self.tree.focus(children[0])
        self.tree.focus_set()
        return True

    def refresh(self):
        selected = {entry.name for entry in self.selected_entries()}
        if self.open_directory(self.directory):
            for item, entry in self.items.items():
                if entry.name in selected:
                    self.tree.selection_add(item)
            self.update_status()

    def show_entries(self):
        self.tree.delete(*self.tree.get_children())
        self.items = {}
        self.parent_item = None
        if os.path.dirname(self.directory) != self.directory:
            self.parent_item = self.tree.insert('', 'end', text=' ' + PARENT_NAME, image=self.folder_icon)
        for entry in self.entries:
            item = self.tree.insert('', 'end', text=' ' + entry.name,
                                    image=self.folder_icon if entry.is_dir else self.file_icon,
                                    values=('Папка' if entry.is_dir else core.format_size(entry.size),
                                            entry.attributes, core.format_date(entry.modified)))
            self.items[item] = entry
        self.update_status()

    def update_status(self):
        text = 'Всего: ' + core.entries_text(self.entries)
        selected = self.selected_entries()
        if selected:
            text += '   Выделено: ' + core.entries_text(selected)
        if self.message:
            text += '   ' + self.message
        self.status.configure(text=text)

    def show_message(self, text):
        if self.message_timer is not None:
            self.root.after_cancel(self.message_timer)
        self.message = text
        self.update_status()
        self.message_timer = self.root.after(MESSAGE_TIME, self.clear_message)

    def clear_message(self):
        self.message_timer = None
        self.message = ''
        self.update_status()

    def selected_entries(self):
        return [self.items[item] for item in self.tree.selection() if item in self.items]

    def go_up(self):
        parent = os.path.dirname(self.directory)
        if parent == self.directory:
            return
        previous = os.path.basename(self.directory)
        if self.open_directory(parent):
            for item, entry in self.items.items():
                if entry.name == previous:
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    self.tree.see(item)

    def go_to_address(self):
        try:
            directory = core.resolve_directory(self.directory, self.address.get().strip())
        except ValueError as error:
            messagebox.showerror(TITLE, str(error))
            self.address.set(self.directory)
            return
        self.open_directory(directory)

    def choose_directory(self):
        directory = filedialog.askdirectory(parent=self.root, initialdir=self.directory, title='Выберите каталог')
        if directory:
            self.open_directory(os.path.normpath(directory))

    def on_double_click(self, event):
        if self.tree.identify_region(event.x, event.y) in ('tree', 'cell'):
            self.open_selected()

    def open_selected(self):
        if self.tree.focus() == self.parent_item and self.parent_item is not None:
            self.go_up()
            return
        selected = self.selected_entries()
        if len(selected) != 1:
            return
        entry = selected[0]
        if entry.is_dir:
            self.open_directory(entry.path)
            return
        try:
            os.startfile(entry.path)
        except OSError as error:
            messagebox.showerror(TITLE, 'Не удалось открыть файл «' + entry.name + '»:\n' + (error.strerror or str(error)))

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item and item not in self.tree.selection():
            self.tree.selection_set(item)
            self.tree.focus(item)
        self.tree.focus_set()
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def select_all(self):
        self.tree.selection_set(list(self.items))

    def clear_selection(self):
        self.tree.selection_remove(self.tree.selection())

    def select_by_pattern(self):
        dialog = PatternDialog(self.root, self.entries)
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        matched = [item for item, entry in self.items.items() if entry in dialog.result]
        self.tree.selection_set(matched)
        if matched:
            self.tree.focus(matched[0])
            self.tree.see(matched[0])
        self.tree.focus_set()
        if not matched:
            messagebox.showinfo(TITLE, 'Под шаблон ничего не подходит.')

    def delete_selected(self, permanent):
        selected = self.selected_entries()
        if not selected:
            messagebox.showinfo(TITLE, 'Выделите файлы или каталоги, которые нужно удалить.')
            return
        problems = [entry for entry in selected if entry.read_only]
        targets = [entry for entry in selected if not entry.read_only]
        place = 'безвозвратно' if permanent else 'в корзину'

        if problems:
            names = preview(problems)
            if not targets:
                messagebox.showerror(TITLE, 'Файлы «только для чтения» удалять нельзя:\n\n' + names)
                return
            question = ('Файлы «только для чтения» удалять нельзя:\n\n' + names +
                        '\n\nУдалить ' + place + ' остальные (' + core.entries_text(targets) + ')?\n'
                        'Если нажать «Нет», ничего не будет удалено.')
            if not messagebox.askyesno('Удаление', question, icon='warning'):
                return
        elif permanent and self.settings['confirm_permanent']:
            question = 'Удалить безвозвратно ' + core.entries_text(targets) + '?\n\n' + preview(targets) + \
                       '\n\nВосстановить их из корзины будет нельзя.'
            if not messagebox.askyesno('Удаление', question, icon='warning', default='no'):
                return
        elif not permanent and self.settings['confirm_recycle']:
            question = 'Переместить в корзину ' + core.entries_text(targets) + '?\n\n' + preview(targets)
            if not messagebox.askyesno('Удаление', question, icon='question'):
                return

        deleted = []
        skipped = []
        failed = []
        policy = {'ask': None, 'delete': 'delete', 'skip': 'skip'}[self.settings['non_empty']]
        for entry in targets:
            if entry.is_dir:
                count = core.count_items(entry.path)
                if count and policy is None:
                    dialog = FolderQuestion(self.root, entry, count)
                    self.root.wait_window(dialog)
                    if dialog.result == 3:
                        policy = 'delete'
                    elif dialog.result == 4:
                        policy = 'skip'
                    if dialog.result in (2, 4):
                        skipped.append(entry)
                        continue
                elif count and policy == 'skip':
                    skipped.append(entry)
                    continue
            error = core.delete_entry(entry, not permanent)
            if error is None:
                deleted.append(entry)
            else:
                failed.append((entry, error))

        self.refresh()
        message = 'Удалено ' + place + ': ' + core.entries_text(deleted)
        if skipped:
            message += ', пропущено: ' + core.entries_text(skipped)
        self.show_message(message)
        if failed:
            lines = '\n'.join(entry.name + ' — ' + error for entry, error in failed[:PREVIEW_LIMIT])
            messagebox.showwarning(TITLE, 'Не удалось удалить:\n\n' + lines)

    def show_help(self):
        messagebox.showinfo('Как пользоваться', HELP_TEXT)

    def show_about(self):
        messagebox.showinfo('О программе', TITLE + '\n\nЛабораторная работа №2, вариант 4: удаление файлов.\n'
                                          'Парадигма интерфейса — меню.')


def preview(entries):
    lines = [entry.name + ('\\' if entry.is_dir else '') for entry in entries[:PREVIEW_LIMIT]]
    if len(entries) > PREVIEW_LIMIT:
        lines.append('… и ещё ' + core.items_text(len(entries) - PREVIEW_LIMIT))
    return '\n'.join(lines)


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    directory = os.getcwd()
    if len(sys.argv) > 1:
        try:
            directory = core.resolve_directory(directory, sys.argv[1])
        except ValueError as error:
            print('Ошибка: ' + str(error))
            return
    root = tk.Tk()
    Explorer(root, directory)
    root.mainloop()


if __name__ == '__main__':
    main()
