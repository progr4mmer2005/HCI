import msvcrt
import os
import shutil
import sys
import time

import files_core as core

TITLE = 'Управление каталогами — меню'
CLEAR = '\x1b[2J\x1b[H'
REVERSE = '\x1b[7m'
RESET = '\x1b[27m'
HIDE_CURSOR = '\x1b[?25l'
SHOW_CURSOR = '\x1b[?25h'
SEARCH_PAUSE = 1.0
LINE = '─' * 60

ARROWS = {'H': 'up', 'P': 'down', 'G': 'home', 'O': 'end', 'I': 'pageup', 'Q': 'pagedown', 'K': 'left', 'M': 'right'}
SPECIAL = {'\r': 'enter', '\x1b': 'esc', ' ': 'space', '\x08': 'backspace', '\t': 'tab'}

MAIN_ITEMS = [
    ('1', 'Содержимое каталога'),
    ('2', 'Сменить каталог'),
    ('3', 'Удалить файлы'),
    ('4', 'Удалить файлы по шаблону'),
    ('5', 'Удалить каталоги'),
    ('6', 'Справка'),
    ('0', 'Выход'),
]

HELP_TEXT = [
    'Программа управляет файлами текущего каталога через меню.',
    '',
    'Выбор пункта меню: стрелки ↑ ↓ и Enter или сразу цифра пункта.',
    'Esc — вернуться назад.',
    '',
    '1 — содержимое каталога: имена, размер, атрибуты, дата изменения.',
    '2 — смена каталога: выберите каталог из списка, «..» — на уровень выше.',
    '3 — удаление файлов: отметьте файлы пробелом и нажмите Enter;',
    '    если ничего не отмечено, удаляется файл под курсором.',
    '4 — удаление по шаблону: * — любые символы, ? — один символ,',
    '    вес задаётся так: >50K, <2M, =0.',
    '5 — удаление каталогов: так же, как файлов.',
    '',
    'В списках можно набрать начало имени — курсор перейдёт к нему.',
    'Файлы «только для чтения» не удаляются.',
]


def read_key():
    char = msvcrt.getwch()
    if char in ('\x00', '\xe0'):
        return ARROWS.get(msvcrt.getwch(), '')
    return SPECIAL.get(char, char)


def screen_height():
    return shutil.get_terminal_size((100, 30)).lines


class App:
    def __init__(self, directory):
        self.directory = directory
        self.message = ''

    def header(self, title):
        print(CLEAR + TITLE)
        print('Каталог: ' + self.directory)
        print(LINE)
        print(title)
        print()

    def menu(self, title, items, text_lines=(), selected=0):
        while True:
            self.header(title)
            for line in text_lines:
                print(line)
            if text_lines:
                print()
            for index, (key, label) in enumerate(items):
                line = ' ' + key + '. ' + label + ' '
                print((REVERSE + line + RESET) if index == selected else line)
            print()
            print(LINE)
            if self.message:
                print(self.message)
            print('↑↓ и Enter — выбор, цифра — сразу выполнить пункт, Esc — назад')
            key = read_key()
            if key == 'up':
                selected = (selected - 1) % len(items)
            elif key == 'down':
                selected = (selected + 1) % len(items)
            elif key == 'home':
                selected = 0
            elif key == 'end':
                selected = len(items) - 1
            elif key == 'enter':
                return items[selected][0]
            elif key == 'esc':
                return None
            else:
                for item_key, label in items:
                    if key == item_key:
                        return item_key

    def pick(self, title, entries, multi, numbered=False):
        cursor = 0
        marked = set()
        search = ''
        last_key = 0.0
        while True:
            self.header(title)
            visible = max(5, screen_height() - 12)
            top = min(max(0, cursor - visible + 1), max(0, len(entries) - visible))
            top = min(top, cursor)
            for index in range(top, min(len(entries), top + visible)):
                entry = entries[index]
                mark = ''
                if multi:
                    mark = '[x] ' if index in marked else '[ ] '
                number = (str(index) + '. ') if numbered and index < 10 else ('   ' if numbered else '')
                name = (entry.name + '\\') if entry.is_dir and entry.name != '..' else entry.name
                note = '  (только чтение)' if entry.read_only else ''
                line = ' ' + number + mark + name + note + ' '
                print((REVERSE + line + RESET) if index == cursor else line)
            print()
            print(LINE)
            if multi:
                print('Отмечено: ' + str(len(marked)) + '   Поиск: ' + search)
                print('↑↓ — курсор, пробел — отметить, Enter — выполнить, буквы — поиск, Esc — назад')
            else:
                print('Поиск: ' + search)
                print('↑↓ и Enter — открыть, цифра — сразу открыть, буквы — поиск, Esc — назад')
            key = read_key()
            now = time.monotonic()
            if key not in ('backspace',) and len(key) == 1 and (key.isalnum() or key in '._-') and not (numbered and key.isdigit()):
                search = (search if now - last_key < SEARCH_PAUSE else '') + key.lower()
                last_key = now
                for index, entry in enumerate(entries):
                    if entry.name.lower().startswith(search):
                        cursor = index
                        break
                continue
            search = ''
            if key == 'up':
                cursor = max(0, cursor - 1)
            elif key == 'down':
                cursor = min(len(entries) - 1, cursor + 1)
            elif key == 'pageup':
                cursor = max(0, cursor - visible)
            elif key == 'pagedown':
                cursor = min(len(entries) - 1, cursor + visible)
            elif key == 'home':
                cursor = 0
            elif key == 'end':
                cursor = len(entries) - 1
            elif key == 'space' and multi:
                marked.symmetric_difference_update({cursor})
                cursor = min(len(entries) - 1, cursor + 1)
            elif key == 'enter':
                if multi and marked:
                    return [entries[index] for index in sorted(marked)]
                return [entries[cursor]]
            elif key == 'esc':
                return None
            elif numbered and key.isdigit() and int(key) < len(entries):
                return [entries[int(key)]]

    def wait(self, title, lines):
        self.header(title)
        for line in lines:
            print(line)
        print()
        print(LINE)
        print('Нажмите любую клавишу, чтобы вернуться')
        read_key()

    def read_line(self, title, lines, prompt):
        self.header(title)
        for line in lines:
            print(line)
        print()
        sys.stdout.write(SHOW_CURSOR)
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return ''
        finally:
            sys.stdout.write(HIDE_CURSOR)

    def entries(self):
        try:
            return core.list_directory(self.directory)
        except OSError as error:
            self.message = 'Не удалось прочитать каталог: ' + (error.strerror or str(error))
            return []

    def show_contents(self):
        entries = self.entries()
        width = max([len('Имя')] + [len(entry.name) + 1 for entry in entries])
        lines = ['Имя'.ljust(width) + '  ' + 'Размер'.rjust(9) + '  Атр.  Изменён']
        for entry in entries:
            name = (entry.name + '\\') if entry.is_dir else entry.name
            size = '' if entry.is_dir else core.format_size(entry.size)
            lines.append(name.ljust(width) + '  ' + size.rjust(9) + '  ' + entry.attributes.ljust(4) + '  ' + core.format_date(entry.modified))
        lines.append('')
        lines.append('Всего: ' + core.entries_text(entries) + '.')
        self.wait('Содержимое каталога', lines)

    def change_directory(self):
        while True:
            folders = [entry for entry in self.entries() if entry.is_dir]
            parent = os.path.dirname(self.directory)
            options = []
            if parent != self.directory:
                options.append(core.Entry('..', parent, True, 0, None, ''))
            options.extend(folders)
            if not options:
                self.message = 'В каталоге нет вложенных каталогов.'
                return
            chosen = self.pick('Сменить каталог', options, multi=False, numbered=True)
            if chosen is None:
                return
            self.directory = os.path.normpath(chosen[0].path)

    def confirm(self, entries):
        names = [(entry.name + '\\') if entry.is_dir else entry.name for entry in entries[:10]]
        if len(entries) > 10:
            names.append('… и ещё ' + core.items_text(len(entries) - 10))
        choice = self.menu('Удалить ' + core.entries_text(entries) + '?',
                           [('1', 'Удалить в корзину'), ('2', 'Удалить безвозвратно'), ('0', 'Отмена')],
                           ['  ' + name for name in names])
        if choice in ('1', '2'):
            return choice == '2'
        return None

    def check_read_only(self, entries):
        blocked = [entry for entry in entries if entry.read_only]
        rest = [entry for entry in entries if not entry.read_only]
        if not blocked:
            return rest
        lines = ['Файлы «только для чтения» удалять нельзя:'] + ['  ' + entry.name for entry in blocked]
        if not rest:
            self.wait('Удаление невозможно', lines)
            return []
        choice = self.menu('Удаление', [('1', 'Удалить остальные (' + core.entries_text(rest) + ')'), ('0', 'Отменить, ничего не удалять')], lines)
        return rest if choice == '1' else []

    def remove(self, entries):
        permanent = self.confirm(entries)
        if permanent is None:
            self.message = 'Удаление отменено.'
            return
        deleted = []
        skipped = []
        failed = []
        policy = None
        for entry in entries:
            if entry.is_dir:
                count = core.count_items(entry.path)
                if count and policy is None:
                    choice = self.menu('Каталог «' + entry.name + '» не пуст: внутри ' + core.items_text(count) + '.',
                                       [('1', 'Удалить вместе с содержимым'), ('2', 'Пропустить'),
                                        ('3', 'Удалить этот и все следующие непустые'), ('4', 'Пропустить этот и все следующие непустые')])
                    if choice == '3':
                        policy = 'delete'
                    elif choice in ('4', None):
                        policy = 'skip'
                    if choice in ('2', '4', None):
                        skipped.append(entry)
                        continue
                elif count and policy == 'skip':
                    skipped.append(entry)
                    continue
            error = core.delete_entry(entry, not permanent)
            if error is None:
                deleted.append(entry)
            else:
                failed.append(entry.name + ' — ' + error)
        place = 'безвозвратно' if permanent else 'в корзину'
        self.message = 'Удалено ' + place + ': ' + core.entries_text(deleted) + '.'
        if skipped:
            self.message += ' Пропущено: ' + core.entries_text(skipped) + '.'
        if failed:
            self.wait('Не удалось удалить', failed)

    def delete_files(self):
        files = [entry for entry in self.entries() if not entry.is_dir]
        if not files:
            self.message = 'В каталоге нет файлов.'
            return
        chosen = self.pick('Удалить файлы', files, multi=True)
        if chosen is None:
            return
        chosen = self.check_read_only(chosen)
        if chosen:
            self.remove(chosen)

    def delete_by_pattern(self):
        hint = ['Шаблон: * — любые символы, ? — один символ. Например: *.log, draft*, *copy*.']
        pattern = self.read_line('Удалить файлы по шаблону', hint, 'Шаблон имени: ')
        if not pattern:
            return
        weight_text = self.read_line('Удалить файлы по шаблону', hint + ['Шаблон имени: ' + pattern, '',
                                     'Вес: знак и число с единицей B, K, M, G, например >50K. Enter — без условия.'], 'Вес: ')
        rules = []
        if weight_text:
            try:
                rules.append(core.parse_size(weight_text))
            except ValueError as error:
                self.message = str(error)
                return
        found = [entry for entry in self.entries()
                 if not entry.is_dir and core.matches(entry.name, pattern) and core.size_fits(entry, rules)]
        if not found:
            self.message = 'Под шаблон «' + pattern + '» не подходит ни один файл.'
            return
        found = self.check_read_only(found)
        if found:
            self.remove(found)

    def delete_folders(self):
        folders = [entry for entry in self.entries() if entry.is_dir]
        if not folders:
            self.message = 'В каталоге нет вложенных каталогов.'
            return
        chosen = self.pick('Удалить каталоги', folders, multi=True)
        if chosen:
            self.remove(chosen)

    def run(self):
        sys.stdout.write(HIDE_CURSOR)
        selected = 0
        actions = {
            '1': self.show_contents,
            '2': self.change_directory,
            '3': self.delete_files,
            '4': self.delete_by_pattern,
            '5': self.delete_folders,
            '6': lambda: self.wait('Справка', HELP_TEXT),
        }
        try:
            while True:
                choice = self.menu('Главное меню', MAIN_ITEMS, selected=selected)
                if choice in (None, '0'):
                    break
                selected = [key for key, _ in MAIN_ITEMS].index(choice)
                self.message = ''
                actions[choice]()
        finally:
            sys.stdout.write(SHOW_CURSOR + CLEAR)


def main():
    os.system('')
    directory = os.getcwd()
    if len(sys.argv) > 1:
        try:
            directory = core.resolve_directory(directory, sys.argv[1])
        except ValueError as error:
            print('Ошибка: ' + str(error))
            return
    App(directory).run()


if __name__ == '__main__':
    main()
