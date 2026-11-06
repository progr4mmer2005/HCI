import ctypes
import os
import re
import shutil
import stat
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime

ATTRIBUTE_FLAGS = [
    ('R', None),
    ('H', getattr(stat, 'FILE_ATTRIBUTE_HIDDEN', 2)),
    ('S', getattr(stat, 'FILE_ATTRIBUTE_SYSTEM', 4)),
    ('A', getattr(stat, 'FILE_ATTRIBUTE_ARCHIVE', 32)),
]

SIZE_UNITS = {
    '': 1, 'b': 1, 'б': 1,
    'k': 1024, 'kb': 1024, 'к': 1024, 'кб': 1024,
    'm': 1024 ** 2, 'mb': 1024 ** 2, 'м': 1024 ** 2, 'мб': 1024 ** 2,
    'g': 1024 ** 3, 'gb': 1024 ** 3, 'г': 1024 ** 3, 'гб': 1024 ** 3,
}

SIZE_OPERATORS = ['>=', '<=', '>', '<', '=']

FO_DELETE = 3
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_ALLOWUNDO = 0x0040
FOF_NOERRORUI = 0x0400


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ('hwnd', wintypes.HWND),
        ('wFunc', wintypes.UINT),
        ('pFrom', wintypes.LPCWSTR),
        ('pTo', wintypes.LPCWSTR),
        ('fFlags', ctypes.c_ushort),
        ('fAnyOperationsAborted', wintypes.BOOL),
        ('hNameMappings', ctypes.c_void_p),
        ('lpszProgressTitle', wintypes.LPCWSTR),
    ]


@dataclass
class Entry:
    name: str
    path: str
    is_dir: bool
    size: int
    modified: datetime
    attributes: str

    @property
    def read_only(self):
        return 'R' in self.attributes


@dataclass
class SizeRule:
    operator: str
    limit: int

    def check(self, size):
        if self.operator == '>':
            return size > self.limit
        if self.operator == '<':
            return size < self.limit
        if self.operator == '>=':
            return size >= self.limit
        if self.operator == '<=':
            return size <= self.limit
        return size == self.limit


def is_pattern(text):
    return '*' in text or '?' in text


def pattern_to_regex(pattern):
    regex = ''
    for char in pattern:
        if char == '*':
            regex += '.*'
        elif char == '?':
            regex += '.'
        else:
            regex += re.escape(char)
    return re.compile(regex, re.IGNORECASE | re.DOTALL)


def matches(name, pattern):
    return pattern_to_regex(pattern).fullmatch(name) is not None


def size_fits(entry, rules):
    if not rules:
        return True
    if entry.is_dir:
        return False
    return all(rule.check(entry.size) for rule in rules)


def make_entry(path):
    info = os.stat(path)
    flags = getattr(info, 'st_file_attributes', 0)
    is_dir = stat.S_ISDIR(info.st_mode)
    attributes = ''
    for letter, flag in ATTRIBUTE_FLAGS:
        if flag is None:
            if not is_dir and not info.st_mode & stat.S_IWRITE:
                attributes += letter
        elif flags & flag:
            attributes += letter
    return Entry(
        name=os.path.basename(path),
        path=path,
        is_dir=is_dir,
        size=0 if is_dir else info.st_size,
        modified=datetime.fromtimestamp(info.st_mtime),
        attributes=attributes,
    )


def list_directory(directory):
    entries = []
    with os.scandir(directory) as scan:
        for item in scan:
            try:
                entries.append(make_entry(item.path))
            except OSError:
                continue
    entries.sort(key=lambda entry: (not entry.is_dir, entry.name.lower()))
    return entries


def find_entry(entries, name):
    for entry in entries:
        if entry.name.lower() == name.lower():
            return entry
    return None


def count_items(directory):
    try:
        with os.scandir(directory) as scan:
            return sum(1 for _ in scan)
    except OSError:
        return 0


def unlock_and_retry(function, path, error):
    os.chmod(path, stat.S_IWRITE)
    function(path)


def move_to_recycle_bin(path):
    operation = SHFILEOPSTRUCTW()
    operation.wFunc = FO_DELETE
    operation.pFrom = os.path.abspath(path) + '\0'
    operation.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    if result != 0 or operation.fAnyOperationsAborted:
        raise PermissionError(path)


def delete_entry(entry, to_recycle_bin):
    try:
        if not os.path.exists(entry.path):
            raise FileNotFoundError(entry.path)
        if to_recycle_bin:
            move_to_recycle_bin(entry.path)
        elif entry.is_dir:
            shutil.rmtree(entry.path, onexc=unlock_and_retry)
        else:
            os.remove(entry.path)
        return None
    except FileNotFoundError:
        return 'не найден, возможно, уже удалён'
    except PermissionError:
        return 'нет доступа или объект открыт другой программой'
    except OSError as error:
        return error.strerror or str(error)


def parse_size(text):
    value = text.strip().replace(',', '.')
    operator = '='
    for candidate in SIZE_OPERATORS:
        if value.startswith(candidate):
            operator = candidate
            value = value[len(candidate):]
            break
    number = ''
    while value and (value[0].isdigit() or value[0] == '.'):
        number += value[0]
        value = value[1:]
    unit = value.strip().lower()
    if number == '' or number.count('.') > 1 or unit not in SIZE_UNITS:
        raise ValueError('Неверный размер «' + text + '». Пример: >10K, <2M, =0.')
    return SizeRule(operator, int(float(number) * SIZE_UNITS[unit]))


def format_size(size):
    if size < 1024:
        return str(size) + ' Б'
    for unit in ['КБ', 'МБ', 'ГБ']:
        size /= 1024
        if size < 1024 or unit == 'ГБ':
            text = ('%.1f' % size).replace('.', ',')
            if text.endswith(',0'):
                text = text[:-2]
            return text + ' ' + unit
    return str(size)


def format_date(moment):
    return moment.strftime('%d.%m.%Y %H:%M')


def word_form(count, one, few, many):
    if 11 <= count % 100 <= 14:
        return many
    if count % 10 == 1:
        return one
    if 2 <= count % 10 <= 4:
        return few
    return many


def count_text(count, one, few, many):
    return str(count) + ' ' + word_form(count, one, few, many)


def files_text(count):
    return count_text(count, 'файл', 'файла', 'файлов')


def folders_text(count):
    return count_text(count, 'каталог', 'каталога', 'каталогов')


def items_text(count):
    return count_text(count, 'объект', 'объекта', 'объектов')


def entries_text(entries):
    files = sum(1 for entry in entries if not entry.is_dir)
    folders = len(entries) - files
    parts = []
    if folders:
        parts.append(folders_text(folders))
    if files:
        parts.append(files_text(files))
    return ', '.join(parts) if parts else 'ничего'


def resolve_directory(current, target):
    if target == '~':
        path = os.path.expanduser('~')
    elif len(target) == 2 and target[1] == ':':
        path = target + '\\'
    else:
        path = os.path.join(current, target)
    path = os.path.normpath(os.path.abspath(path))
    if not os.path.exists(path):
        raise ValueError('Каталог «' + target + '» не найден.')
    if not os.path.isdir(path):
        raise ValueError('«' + target + '» — это файл, а не каталог.')
    try:
        os.scandir(path).close()
    except PermissionError:
        raise ValueError('Нет доступа к каталогу «' + target + '».') from None
    return path
