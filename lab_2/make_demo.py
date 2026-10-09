import os
import shutil
import stat
import sys
from datetime import datetime

FILES = [
    ('отчёт по практике.docx', 118_000, '20.09.2026 18:40', False),
    ('презентация.pptx', 2_450_000, '24.09.2026 21:15', False),
    ('заметки.txt', 3_200, '05.10.2026 09:12', False),
    ('список покупок.txt', 640, '08.10.2026 19:03', False),
    ('readme.txt', 1_800, '15.06.2026 12:00', True),
    ('лицензия.txt', 5_100, '15.06.2026 12:00', True),
    ('пустой.txt', 0, '01.10.2026 10:30', False),
    ('черновик.tmp', 0, '02.10.2026 11:47', False),
    ('cache_01.tmp', 15_400, '12.08.2026 14:20', False),
    ('cache_02.tmp', 230_000, '18.08.2026 16:05', False),
    ('cache_03.tmp', 612_000, '03.09.2026 08:55', False),
    ('cache_04.tmp', 1_340_000, '29.09.2026 22:10', False),
    ('install.log', 41_000, '11.03.2026 10:02', False),
    ('update.log', 96_000, '27.07.2026 03:14', False),
    ('error.log', 2_100_000, '30.08.2026 23:59', False),
    ('архив фото.zip', 8_700_000, '14.05.2026 17:36', False),
    ('backup.bak', 12_300_000, '02.02.2026 02:00', False),
    ('old_backup.bak', 9_800_000, '15.12.2025 02:00', False),
]

FOLDERS = {
    'Документы': [
        ('договор.pdf', 340_000, '10.09.2026 15:20', False),
        ('резюме.docx', 64_000, '01.09.2026 11:00', False),
    ],
    'Фото': [
        ('IMG_0001.jpg', 3_100_000, '07.07.2026 13:45', False),
        ('IMG_0002.jpg', 2_900_000, '07.07.2026 13:46', False),
        ('IMG_0003.jpg', 3_400_000, '07.07.2026 13:48', False),
    ],
    'Загрузки': [
        ('setup.exe', 5_600_000, '22.09.2026 20:00', False),
        ('setup.tmp', 120_000, '22.09.2026 20:01', False),
    ],
    'Пустая папка': [],
    'Temp_1': [
        ('log_1.tmp', 45_000, '01.10.2026 09:00', False),
    ],
    'Temp_2': [],
    'Старое': [
        ('план 2025.docx', 52_000, '10.01.2025 10:00', False),
    ],
    'Старое/2024': [
        ('фото 2024.jpg', 2_200_000, '31.12.2024 23:00', False),
    ],
}


def make_file(folder, name, size, moment, read_only):
    path = os.path.join(folder, name)
    with open(path, 'wb') as file:
        if name.endswith(('.txt', '.log')):
            line = ('Строка текстового файла ' + name + '\n').encode('utf-8')
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
        os.makedirs(path, exist_ok=True)
        for name, size, moment, read_only in files:
            make_file(path, name, size, moment, read_only)
    print('Тестовый каталог создан: ' + target)


if __name__ == '__main__':
    main()
