import difflib
import os
import sys

import files_core as core

COMMANDS = ['dir', 'cd', 'del', 'deldir', 'cls', 'help', 'exit']

OPTIONS = {
    'dir': {
        '-s': 'size', '--size': 'size',
        '-a': 'attributes', '--attributes': 'attributes',
        '-d': 'date', '--date': 'date',
        '-l': 'long', '--long': 'long',
        '-w': 'weight', '--weight': 'weight',
    },
    'del': {
        '-w': 'weight', '--weight': 'weight',
        '-p': 'permanent', '--permanent': 'permanent',
        '-y': 'yes', '--yes': 'yes',
    },
    'deldir': {
        '-p': 'permanent', '--permanent': 'permanent',
        '-f': 'force', '--force': 'force',
        '-e': 'empty_only', '--empty-only': 'empty_only',
        '-y': 'yes', '--yes': 'yes',
    },
}

HELP_OPTIONS = ['-h', '--help']

SUMMARY = {
    'dir': 'показать содержимое каталога',
    'cd': 'перейти в другой каталог',
    'del': 'удалить файлы',
    'deldir': 'удалить каталоги',
    'cls': 'очистить экран',
    'help': 'справка',
    'exit': 'выход',
}

HELP = {
    'dir': (
        'dir [имя или шаблон ...] [ключи]',
        'Выводит содержимое текущего каталога: сначала каталоги (с \\ в конце имени), затем файлы.\n'
        'По умолчанию выводятся только имена. Если указаны имена или шаблоны, выводятся только\n'
        'подходящие файлы и каталоги.\n'
        '  -s, --size           показать размер файлов\n'
        '  -a, --attributes     показать атрибуты: R — только чтение, H — скрытый,\n'
        '                       S — системный, A — архивный\n'
        '  -d, --date           показать дату и время изменения\n'
        '  -l, --long           показать всё: размер, атрибуты и дату\n'
        '  -w, --weight ВЕС     показать только файлы подходящего веса',
        ['dir', 'dir -l', 'dir *.txt -s', 'dir отчёт* --date', 'dir -w >1M -s', 'dir *.log --weight <100K --long'],
    ),
    'cd': (
        'cd путь',
        'Делает текущим указанный каталог. Без параметра выводит текущий каталог.\n'
        'Путь может быть относительным или полным: .. — на уровень выше,\n'
        '\\ — корень диска, D: — корень диска D, ~ — домашний каталог.',
        ['cd Документы', 'cd ..', 'cd "Новая папка"', 'cd C:\\Users'],
    ),
    'del': (
        'del имя или шаблон ... [ключи]',
        'Удаляет файлы текущего каталога. Можно указать несколько имён и шаблонов.\n'
        'По умолчанию файлы перемещаются в корзину.\n'
        '  -w, --weight ВЕС     удалять только файлы подходящего веса\n'
        '  -p, --permanent      удалить безвозвратно, минуя корзину\n'
        '  -y, --yes            не спрашивать подтверждение при удалении по шаблону или весу',
        ['del заметки.txt', 'del a.txt b.txt "мой файл.txt"', 'del *', 'del *.tmp *.log',
         'del cache* -w >100K', 'del *копия* --permanent', 'del * -w =0'],
    ),
    'deldir': (
        'deldir имя или шаблон ... [ключи]',
        'Удаляет каталоги текущего каталога вместе с содержимым. Можно указать несколько\n'
        'имён и шаблонов. Для каждого непустого каталога программа спрашивает, удалять ли его.\n'
        'По умолчанию каталоги перемещаются в корзину.\n'
        '  -p, --permanent      удалить безвозвратно, минуя корзину\n'
        '  -f, --force          удалять непустые каталоги без вопроса\n'
        '  -e, --empty-only     удалять только пустые каталоги, непустые пропускать без вопроса\n'
        '  -y, --yes            не спрашивать подтверждение при удалении по шаблону',
        ['deldir Старое', 'deldir Загрузки "Пустая папка"', 'deldir *', 'deldir Temp* -p',
         'deldir * --empty-only', 'deldir Temp* -f -y'],
    ),
    'cls': (
        'cls',
        'Очищает экран.',
        ['cls'],
    ),
    'help': (
        'help [команда]',
        'Без параметра выводит список команд, с параметром — справку по команде.\n'
        'Справку по команде также выводит ключ -h или --help: del --help.',
        ['help', 'help del', 'deldir -h'],
    ),
    'exit': (
        'exit',
        'Завершает работу программы.',
        ['exit'],
    ),
}

GENERAL_HELP = (
    'Шаблон имени: * — любое число любых символов, ? — ровно один любой символ.\n'
    '  *          все файлы (для deldir — все каталоги)\n'
    '  *.txt      файлы с расширением .txt\n'
    '  отчёт*     имена, которые начинаются на «отчёт»\n'
    '  *копия*    имена, в которых есть «копия»\n'
    '  file?.log  file1.log, fileA.log и т. п.\n'
    'Вес (размер) файла: знак >, <, >=, <= или = и число с единицей B, K, M, G\n'
    '(байты, КБ, МБ, ГБ), например >10K, <2M, =0. Ключ можно указать дважды: -w >1K -w <1M.\n'
    'Имена с пробелами заключаются в кавычки: "мой файл.txt".\n'
    'Регистр букв в командах, ключах и именах не учитывается.\n'
    'Если в списке на удаление есть отсутствующие или неподходящие объекты, программа\n'
    'сообщает о них и предлагает удалить остальные или отменить команду целиком.\n'
    'Если удаление задано шаблоном или весом, программа сначала показывает, что будет удалено.'
)


class CommandError(Exception):
    pass


def split_words(line):
    words = []
    word = ''
    quoted = False
    has_word = False
    for char in line:
        if char == '"':
            quoted = not quoted
            has_word = True
        elif char.isspace() and not quoted:
            if has_word:
                words.append(word)
            word = ''
            has_word = False
        else:
            word += char
            has_word = True
    if quoted:
        raise CommandError('Не закрыта кавычка.')
    if has_word:
        words.append(word)
    return words


def parse_arguments(command, words):
    allowed = OPTIONS.get(command, {})
    names = []
    options = {'weight': []}
    index = 0
    while index < len(words):
        word = words[index]
        key = word.lower()
        if key.startswith('-') and len(key) > 1:
            option = allowed.get(key)
            if option is None:
                raise CommandError('У команды ' + command + ' нет ключа «' + word + '». Справка: help ' + command + '.')
            if option == 'weight':
                if index + 1 >= len(words):
                    raise CommandError('После ключа ' + word + ' нужен вес, например >10K.')
                try:
                    options['weight'].append(core.parse_size(words[index + 1]))
                except ValueError as error:
                    raise CommandError(str(error)) from None
                index += 2
                continue
            options[option] = True
        else:
            names.append(word)
        index += 1
    return names, options


def ask_choice(echo, variants):
    print('Что сделать?')
    for number, text in enumerate(variants, start=1):
        print('  ' + str(number) + ' — ' + text)
    while True:
        try:
            answer = input('Введите номер: ')
        except (EOFError, KeyboardInterrupt):
            print()
            return len(variants)
        if echo:
            print(answer)
        answer = answer.strip()
        if answer.isdigit() and 1 <= int(answer) <= len(variants):
            return int(answer)
        print('Введите число от 1 до ' + str(len(variants)) + '.')


def display_name(entry):
    return entry.name + ('\\' if entry.is_dir else '')


def print_entries(entries, show_size, show_attributes, show_date):
    if not (show_size or show_attributes or show_date):
        for entry in entries:
            print(display_name(entry))
        return
    width = max([len('Имя')] + [len(display_name(entry)) for entry in entries])
    header = 'Имя'.ljust(width)
    if show_size:
        header += '  ' + 'Размер'.rjust(9)
    if show_attributes:
        header += '  ' + 'Атр.'
    if show_date:
        header += '  ' + 'Изменён'
    print(header)
    for entry in entries:
        line = display_name(entry).ljust(width)
        if show_size:
            line += '  ' + ('' if entry.is_dir else core.format_size(entry.size)).rjust(9)
        if show_attributes:
            line += '  ' + entry.attributes.ljust(4)
        if show_date:
            line += '  ' + core.format_date(entry.modified)
        print(line.rstrip())


class Shell:
    def __init__(self, directory):
        self.directory = directory
        self.running = True
        self.echo = not sys.stdin.isatty()

    def run(self):
        print('Управление файловыми каталогами. Командный язык.')
        print('Введите help, чтобы увидеть список команд.')
        print()
        while self.running:
            try:
                line = input(self.directory + '> ')
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if self.echo:
                print(line)
            cleared = self.execute(line)
            if self.running and not cleared:
                print()

    def execute(self, line):
        try:
            words = split_words(line)
            if not words:
                return True
            command = words[0].lower()
            if command not in COMMANDS:
                raise CommandError(unknown_command_text(words[0]))
            arguments = words[1:]
            if any(word.lower() in HELP_OPTIONS for word in arguments):
                self.command_help([command])
                return False
            if command == 'cls':
                self.command_cls()
                return True
            getattr(self, 'command_' + command)(arguments)
        except CommandError as error:
            print('Ошибка: ' + str(error))
        return False

    def read_directory(self):
        try:
            return core.list_directory(self.directory)
        except OSError as error:
            raise CommandError('Не удалось прочитать каталог: ' + (error.strerror or str(error))) from None

    def command_dir(self, words):
        names, options = parse_arguments('dir', words)
        entries = self.read_directory()
        if names:
            entries = [entry for entry in entries if any(core.matches(entry.name, name) for name in names)]
        if options['weight']:
            entries = [entry for entry in entries if core.size_fits(entry, options['weight'])]
        print('Каталог ' + self.directory)
        print()
        if not entries:
            print('Ничего не найдено.' if names or options['weight'] else 'Каталог пуст.')
            return
        long = options.get('long', False)
        print_entries(entries, long or options.get('size', False), long or options.get('attributes', False),
                      long or options.get('date', False))
        print()
        print('Всего: ' + core.entries_text(entries) + '.')

    def command_cd(self, words):
        if not words:
            print(self.directory)
            return
        if len(words) > 1:
            raise CommandError('Команда cd принимает один путь. Если в имени есть пробелы, заключите его в кавычки.')
        try:
            self.directory = core.resolve_directory(self.directory, words[0])
        except ValueError as error:
            raise CommandError(str(error)) from None
        print('Текущий каталог: ' + self.directory)

    def command_del(self, words):
        self.remove('del', words, False)

    def command_deldir(self, words):
        self.remove('deldir', words, True)

    def collect(self, names, want_dir, weight):
        entries = self.read_directory()
        targets = []
        problems = []
        noun = 'каталог' if want_dir else 'файл'
        for name in names:
            if core.is_pattern(name):
                found = [entry for entry in entries
                         if entry.is_dir == want_dir and core.matches(entry.name, name) and core.size_fits(entry, weight)]
                if not found:
                    problems.append('под шаблон «' + name + '» не подходит ни один ' + noun
                                    + (' нужного веса' if weight else ''))
                for entry in found:
                    if entry not in targets:
                        targets.append(entry)
                continue
            entry = core.find_entry(entries, name)
            if entry is None:
                problems.append(noun + ' «' + name + '» не найден')
            elif entry.is_dir and not want_dir:
                problems.append('«' + entry.name + '» — это каталог, а не файл (каталоги удаляет команда deldir)')
            elif not entry.is_dir and want_dir:
                problems.append('«' + entry.name + '» — это файл, а не каталог (файлы удаляет команда del)')
            elif not core.size_fits(entry, weight):
                problems.append('файл «' + entry.name + '» не подходит по весу (' + core.format_size(entry.size) + ')')
            elif entry not in targets:
                targets.append(entry)
        for entry in list(targets):
            if entry.read_only:
                problems.append('файл «' + entry.name + '» только для чтения, его удаление запрещено')
                targets.remove(entry)
        return targets, problems

    def remove(self, command, words, want_dir):
        names, options = parse_arguments(command, words)
        if not names:
            raise CommandError('Укажите, что удалить: имена или шаблон. Пример: ' + HELP[command][2][0] + '.')
        if options.get('force') and options.get('empty_only'):
            raise CommandError('Ключи --force и --empty-only нельзя указывать вместе.')
        weight = options['weight']
        targets, problems = self.collect(names, want_dir, weight)
        uncertain = bool(weight) or any(core.is_pattern(name) for name in names)
        place = 'безвозвратно' if options.get('permanent') else 'в корзину'

        if problems and not targets:
            if len(problems) == 1:
                raise CommandError(problems[0][0].upper() + problems[0][1:] + '.')
            print('Ошибка: удалять нечего.')
            for problem in problems:
                print('  — ' + problem)
            return

        skipped = []
        if options.get('empty_only'):
            skipped = [entry for entry in targets if core.count_items(entry.path)]
            targets = [entry for entry in targets if entry not in skipped]
            if not targets:
                print('Пустых каталогов нет, удалять нечего. Непустые пропущены: '
                      + ', '.join(entry.name for entry in skipped) + '.')
                return

        if problems or (uncertain and not options.get('yes')):
            if problems:
                print('Обнаружены проблемы:')
                for problem in problems:
                    print('  — ' + problem)
                print()
            print('Будут удалены ' + place + ' (' + core.entries_text(targets) + '):')
            for entry in targets:
                print('  ' + display_name(entry))
            if skipped:
                print('Непустые каталоги будут пропущены: ' + ', '.join(entry.name for entry in skipped) + '.')
            print()
            first = ('удалить остальные' if problems else 'удалить') + ' (' + core.entries_text(targets) + ')'
            if ask_choice(self.echo, [first, 'отменить команду, ничего не удалять']) != 1:
                print('Команда отменена, ничего не удалено.')
                return
            print()

        deleted = []
        failed = []
        policy = 'delete' if options.get('force') else 'skip' if options.get('empty_only') else None
        for entry in targets:
            if entry.is_dir:
                count = core.count_items(entry.path)
                if count and policy is None:
                    print('Каталог «' + entry.name + '» не пуст: внутри ' + core.items_text(count) + '.')
                    choice = ask_choice(self.echo, [
                        'удалить его вместе с содержимым',
                        'пропустить его',
                        'удалить его и все следующие непустые каталоги',
                        'пропустить его и все следующие непустые каталоги',
                    ])
                    print()
                    if choice == 3:
                        policy = 'delete'
                    elif choice == 4:
                        policy = 'skip'
                    if choice in (2, 4):
                        skipped.append(entry)
                        continue
                elif count and policy == 'skip':
                    skipped.append(entry)
                    continue
            error = core.delete_entry(entry, not options.get('permanent'))
            if error is None:
                deleted.append(entry)
            else:
                failed.append((entry, error))

        if deleted:
            print('Удалено ' + place + ': ' + core.entries_text(deleted) + '.')
        else:
            print('Ничего не удалено.')
        if skipped:
            print('Пропущено: ' + core.entries_text(skipped) + ' (' + ', '.join(entry.name for entry in skipped) + ').')
        for entry, error in failed:
            print('Не удалось удалить «' + entry.name + '»: ' + error + '.')

    def command_help(self, words):
        if words:
            name = words[0].lower()
            if name not in COMMANDS:
                raise CommandError(unknown_command_text(words[0]))
            usage, description, examples = HELP[name]
            print('Формат: ' + usage)
            print()
            print(description)
            print()
            print('Примеры:')
            for example in examples:
                print('  ' + example)
            return
        print('Команды:')
        for name in COMMANDS:
            print('  ' + HELP[name][0].ljust(36) + SUMMARY[name])
        print()
        print(GENERAL_HELP)
        print()
        print('Подробнее о команде: help <команда> или <команда> --help.')

    def command_cls(self):
        if not self.echo:
            os.system('cls' if os.name == 'nt' else 'clear')

    def command_exit(self, words):
        self.running = False


def unknown_command_text(word):
    text = 'Неизвестная команда «' + word + '».'
    guesses = difflib.get_close_matches(word.lower(), COMMANDS, n=1, cutoff=0.5)
    if guesses:
        text += ' Возможно, вы имели в виду ' + guesses[0] + '?'
    return text + ' Список команд: help.'


def main():
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding='utf-8')
    if not sys.stdin.isatty():
        sys.stdin.reconfigure(encoding='utf-8')
    directory = os.getcwd()
    if len(sys.argv) > 1:
        try:
            directory = core.resolve_directory(directory, sys.argv[1])
        except ValueError as error:
            print('Ошибка: ' + str(error))
            return
    Shell(directory).run()


if __name__ == '__main__':
    main()
