import os
import sys
import uuid
import shutil
import re
import zipfile


def extract_archive(archive_path, extract_to):
    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return extract_to


def create_archive(directory, output_filename):
    shutil.make_archive(output_filename, 'zip', directory)
    return f"{output_filename}.zip"


def move_files(directory):
    # Проверяем, что указанный путь существует и является папкой
    if not os.path.exists(directory):
        print(f"Указанный путь {directory} не существует.")
        return

    if not os.path.isdir(directory):
        print(f"Указанный путь {directory} не является папкой.")
        return

    # Создаем папку uploads, если она не существует
    uploads_dir = os.path.join(directory, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    # Создаем папку с uuid4 внутри uploads
    new_uploads_dir = os.path.join(uploads_dir, str(uuid.uuid4()))
    os.makedirs(new_uploads_dir)

    # Перебираем все файлы в указанной папке
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        # Пропускаем папки и файлы .md
        if os.path.isdir(file_path) or filename.endswith(".md"):
            continue
        # Перемещаем файлы в новую папку
        shutil.move(file_path, new_uploads_dir)
        print(f"Файл {filename} перемещен в {new_uploads_dir}")

    return new_uploads_dir


def update_md_files(directory, uploads_dir):
    # Регулярное выражение для поиска ссылок в формате ![](filename)
    pattern = re.compile(r'!\[.*?\]\((.+?)\)(\s*\{.*?\})?')

    # Перебираем все .md файлы в указанной папке
    for filename in os.listdir(directory):
        if filename.endswith(".md"):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Ищем все ссылки на файлы
            matches = pattern.findall(content)
            for match in matches:
                link = match[0]
                base_md_name = re.sub(r'^\d+\s*', '', os.path.splitext(filename)[0])
                expected_file_name = f"{base_md_name}_{os.path.basename(link)}"
                original_file_path = find_file_in_uploads(uploads_dir, expected_file_name)

                if original_file_path:
                    # Создаем новую папку рядом с файлом с uuid4 в названии
                    new_dir = os.path.join(os.path.dirname(original_file_path), str(uuid.uuid4()))
                    os.makedirs(new_dir)

                    # Перемещаем файл в новую папку
                    new_file_path = os.path.join(new_dir, expected_file_name)
                    shutil.move(original_file_path, new_file_path)
                    print(f"Файл {expected_file_name} перемещен в {new_file_path}")

                    # Обновляем ссылку в .md файле и удаляем настройки
                    new_link = f"![]({os.path.relpath(new_file_path, directory)})"
                    content = re.sub(re.escape(f"![]({link})") + r'(\s*\{.*?\})?', new_link, content)

            # Записываем обновленный контент обратно в .md файл
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)


def find_file_in_uploads(uploads_dir, expected_file_name):
    # Рекурсивно ищем файл в папке uploads
    for root, _, files in os.walk(uploads_dir):
        if expected_file_name in files:
            return os.path.join(root, expected_file_name)
    return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python script.py <путь_до_архива>")
        sys.exit(1)

    archive_path = sys.argv[1]
    archive_dir = os.path.dirname(archive_path)
    archive_name = os.path.splitext(os.path.basename(archive_path))[0]
    output_archive_name = os.path.join(archive_dir, f"{archive_name}_converted")

    # Временная директория для извлечения архива
    temp_dir = os.path.join(archive_dir, str(uuid.uuid4()))
    os.makedirs(temp_dir)

    try:
        extracted_dir = extract_archive(archive_path, temp_dir)
        uploads_dir = move_files(extracted_dir)
        update_md_files(extracted_dir, uploads_dir)
        new_archive = create_archive(extracted_dir, output_archive_name)
        print(f"Новый архив создан: {new_archive}")
    finally:
        # Удаляем временную директорию
        shutil.rmtree(temp_dir)
