import argparse  # для работы с аргументами командной строки
import os        # для работы с файловой системой
import time      # для измерения времени выполнения (benchmark)
import tarfile   # для создания и распаковки tar-архивов
import bz2       # для работы с сжатием/распаковкой bzip2
from compression import zstd  # стандартная библиотека Python 3.14 для zstd
import sys       # для завершения программы с sys.exit
import tempfile  # для создания временных файлов

# Функция для отображения прогресс-бара в консоли
def print_progress_bar(completed, total, length=30):
    percent = completed / total  # доля завершенной работы
    filled = int(length * percent)  # количество символов '='
    bar = '=' * filled + ' ' * (length - filled)  # формируем строку прогресс-бара
    print(f"\r[{bar}] {percent*100:.1f}%", end='\r')  # выводим на одной строке
    if completed >= total:
        print()  # перенос строки после завершения

# Сжатие отдельного файла
def compress_file(input_path, output_path, method, benchmark=False):
    start = time.time()  # старт таймера
    if method == 'zstd':
        with open(input_path, 'rb') as fi, open(output_path, 'wb') as fo:
            data = fi.read()               # читаем данные
            compressed = zstd.compress(data)  # сжимаем zstd
            fo.write(compressed)           # записываем сжатое
            if benchmark:
                print_progress_bar(len(data), len(data))  # прогресс 100%
    elif method == 'bz2':
        with open(input_path, 'rb') as fi, bz2.open(output_path, 'wb') as fo:
            fo.write(fi.read())            # сжимаем bzip2
            if benchmark:
                print_progress_bar(1, 1)   # один раз, 100%
    if benchmark:
        print(f"Compression time: {time.time() - start:.2f}s")  # вывод времени

# Распаковка отдельного файла
def decompress_file(input_path, output_path, method, benchmark=False):
    start = time.time()
    if method == 'zstd':
        with open(input_path, 'rb') as fi, open(output_path, 'wb') as fo:
            data = fi.read()               # читаем сжатые данные
            fo.write(zstd.decompress(data))  # распаковываем
            if benchmark:
                print_progress_bar(len(data), len(data))  # прогресс 100%
    elif method == 'bz2':
        with bz2.open(input_path, 'rb') as fi, open(output_path, 'wb') as fo:
            fo.write(fi.read())            # распаковка bzip2
            if benchmark:
                print_progress_bar(1, 1)   # один раз, 100%
    if benchmark:
        print(f"Decompression time: {time.time() - start:.2f}s")  # вывод времени

# Сжатие директории (через tar)
def compress_directory(input_dir, output_path, method, benchmark=False):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as temp_tar:
            tar_path = temp_tar.name  # создаем временный tar файл
        with tarfile.open(tar_path, 'w') as tar:
            tar.add(input_dir, arcname=os.path.basename(input_dir))  # добавляем директорию
        compress_file(tar_path, output_path, method, benchmark)  # сжимаем tar
        os.remove(tar_path)  # удаляем временный файл
    except Exception as e:
        print(f"\nОшибка при архивации директории '{input_dir}': {e}")
        sys.exit(1)

# Распаковка директории
def decompress_directory(input_path, output_dir, method, benchmark=False):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as temp_tar:
            tar_path = temp_tar.name  # временный tar для распаковки
        decompress_file(input_path, tar_path, method, benchmark)  # распаковываем архив
        with tarfile.open(tar_path, 'r') as tar:
            tar.extractall(path=output_dir)  # извлекаем содержимое
        os.remove(tar_path)  # удаляем временный файл
    except Exception as e:
        print(f"\nОшибка при распаковке директории '{input_path}': {e}")
        sys.exit(1)

# Основная функция программы
def main():
    # Создание парсера аргументов командной строки
    parser = argparse.ArgumentParser(description="Консольный архиватор/распаковщик (.zst, .bz2)")
    parser.add_argument("src", help="Исходный файл/папка или архив для распаковки")  # исходный путь
    parser.add_argument("dst", help="Целевой файл или директория")  # целевой путь
    parser.add_argument("-b", "--benchmark", action="store_true", help="Показать время выполнения")  # ключ бенчмарка
    args = parser.parse_args()

    src, dst, bench = args.src, args.dst, args.benchmark  # извлечение значений

    # Проверка существования исходного пути
    if not os.path.exists(src):
        print(f"Ошибка: исходный путь '{src}' не существует")
        sys.exit(1)

    # Определяем режим: True = архивирование, False = распаковка
    compress_mode = not (src.endswith('.zst') or src.endswith('.bz2'))

    if compress_mode:  # архивирование
        # Определяем метод сжатия по расширению
        if dst.endswith('.zst'):
            method = 'zstd'
        elif dst.endswith('.bz2'):
            method = 'bz2'
        else:
            print("Ошибка: расширение .zst или .bz2 обязательно для архивации")
            sys.exit(1)
        # Архивируем директорию или файл
        if os.path.isdir(src):
            compress_directory(src, dst, method, bench)
        else:
            compress_file(src, dst, method, bench)
    else:  # распаковка
        # Определяем метод по расширению архива
        if src.endswith('.zst'):
            method = 'zstd'
        elif src.endswith('.bz2'):
            method = 'bz2'
        else:
            print("Ошибка: неизвестный формат архива")
            sys.exit(1)

        try:
            # Пробуем открыть архив как tar (для директории)
            tar_check = tarfile.open(src)
            tar_check.close()
            os.makedirs(dst, exist_ok=True)  # создаем директорию если не существует
            decompress_directory(src, dst, method, bench)
        except tarfile.ReadError:
            # Если не tar, значит это обычный файл
            decompress_file(src, dst, method, bench)

# Точка входа в программу
if __name__ == "__main__":
    main()