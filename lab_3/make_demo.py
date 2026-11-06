import os
import shutil
import stat
import sys
from datetime import datetime

FILES = [
    ('report.txt', 4_200, '02.11.2026 10:15', False),
    ('draft1.txt', 1_100, '20.10.2026 18:02', False),
    ('draft2.txt', 1_900, '21.10.2026 19:40', False),
    ('draft3.txt', 2_600, '23.10.2026 09:12', False),
    ('readme.txt', 1_800, '15.06.2026 12:00', True),
    ('empty.txt', 0, '01.10.2026 10:30', False),
    ('budget.xlsx', 48_000, '28.10.2026 16:45', False),
    ('slides.pptx', 2_450_000, '24.09.2026 21:15', False),
    ('cache1.tmp', 230_000, '18.08.2026 16:05', False),
    ('cache2.tmp', 612_000, '03.09.2026 08:55', False),
    ('error.log', 2_100_000, '30.08.2026 23:59', False),
    ('update.log', 96_000, '27.07.2026 03:14', False),
    ('system.log', 12_000, '11.03.2026 10:02', False),
]

FOLDERS = {
    'photos': [
        ('img001.jpg', 3_100_000, '07.07.2026 13:45', False),
        ('img002.jpg', 2_900_000, '07.07.2026 13:46', False),
    ],
    'backup': [
        ('old.zip', 9_800_000, '15.12.2025 02:00', False),
        ('list.txt', 3_000, '15.12.2025 02:01', False),
    ],
    'music': [
        ('track1.mp3', 5_200_000, '01.05.2026 20:00', False),
    ],
    'temp01': [],
}


def make_file(folder, name, size, moment, read_only):
    path = os.path.join(folder, name)
    with open(path, 'wb') as file:
        if name.endswith(('.txt', '.log')):
            line = ('Line of text file ' + name + '\n').encode('utf-8')
            file.write((line * (size // len(line) + 1))[:size])
        else:
            file.write(bytes(size))
    timestamp = datetime.strptime(moment, '%d.%m.%Y %H:%M').timestamp()
    os.utime(path, (timestamp, timestamp))
    if read_only:
        os.chmod(path, stat.S_IREAD)


def clear(folder):
    def unlock(function, path, error):
        os.chmod(path, stat.S_IWRITE)
        function(path)
    shutil.rmtree(folder, onexc=unlock)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo')
    if os.path.exists(target):
        clear(target)
    os.makedirs(target)
    for name, size, moment, read_only in FILES:
        make_file(target, name, size, moment, read_only)
    for folder, files in FOLDERS.items():
        path = os.path.join(target, folder)
        os.makedirs(path)
        for name, size, moment, read_only in files:
            make_file(path, name, size, moment, read_only)
    print('Тестовый каталог создан: ' + target)


if __name__ == '__main__':
    main()
