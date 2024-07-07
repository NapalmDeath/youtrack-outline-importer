import os
import sys
import uuid
import shutil
import re
import zipfile
from transliterate import translit


def extract_archive(archive_path, extract_to):
    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return extract_to


def create_archive(directory, output_filename):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.join(directory, '..'))
                zipf.write(file_path, arcname)

    return output_filename


def sanitize_filename(filename):
    # Транслитерация русских букв
    transliterated = translit(filename, 'ru', reversed=True)
    name, ext = os.path.splitext(transliterated)
    # Заменяем все символы, кроме точки перед расширением, на _
    sanitized_name = re.sub(r'[^\w-]', '_', name) + ext
    return sanitized_name


def move_files_to_single_folder(directory):
    # Создаем папку uploads, если она не существует
    uploads_dir = os.path.join(directory, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    # Создаем единую папку с uuid4 внутри uploads
    single_uploads_dir = os.path.join(uploads_dir, str(uuid.uuid4()).replace("-", ""))
    os.makedirs(single_uploads_dir)

    path_mapping = {}

    # Перебираем все файлы в указанной папке
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            # Пропускаем файлы .md и файлы в уже созданных папках
            if filename.endswith(".md") or uploads_dir in root:
                continue
            # Создаем папку с uuid4 для каждого файла
            new_file_dir = os.path.join(single_uploads_dir, str(uuid.uuid4()).replace("-", ""))
            os.makedirs(new_file_dir)

            # Перемещаем файл в новую папку
            sanitized_filename = sanitize_filename(filename)
            new_file_path = os.path.join(new_file_dir, sanitized_filename)
            shutil.move(file_path, new_file_path)
            print(f"Файл {filename} перемещен в {new_file_path}")

            # Сохраняем исходный и новый пути в словарь
            path_mapping[file_path] = new_file_path

    return single_uploads_dir, path_mapping


def update_md_files(directory, path_mapping):
    # Регулярное выражение для поиска ссылок в формате ![](filename)
    pattern = re.compile(r'!\[.*?\]\((.+?)\)(\s*\{.*?\})?')

    # Перебираем все .md файлы в указанной папке
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".md"):
                file_path = os.path.join(root, filename)
                base_md_name = re.sub(r'^\d+\s*', '', os.path.splitext(filename)[0])
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                # Ищем все ссылки на файлы и обновляем пути
                matches = pattern.findall(content)
                for match in matches:
                    link = match[0]
                    sanitized_link = sanitize_filename(link)
                    abs_link_path = find_file_in_uploads(path_mapping, sanitized_link)

                    if abs_link_path:
                        new_link = os.path.relpath(abs_link_path, directory).replace("\\", "/")
                        ext = os.path.splitext(sanitized_link)[1].lower()
                        if ext in ['.mov', '.mp4']:
                            new_text = f"[{sanitized_link} 640x480]"
                        else:
                            new_text = f"![]"
                        content = re.sub(re.escape(f"![]({link})") + r'(\s*\{.*?\})?', f"{new_text}({new_link})",
                                         content)

                # Записываем обновленный контент обратно в .md файл
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)


def find_file_in_uploads(path_mapping, expected_file_name):
    for original_path, new_path in path_mapping.items():
        if expected_file_name in new_path:
            return new_path
    return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python script.py <путь_до_архива>")
        sys.exit(1)

    archive_path = sys.argv[1]
    archive_dir = os.path.dirname(archive_path)
    archive_name = os.path.splitext(os.path.basename(archive_path))[0]
    output_archive_name = os.path.join(archive_dir, f"{archive_name}_converted.zip")

    # Временная директория для извлечения архива
    temp_dir = os.path.join(archive_dir, str(uuid.uuid4()).replace("-", ""))
    os.makedirs(temp_dir)

    try:
        extracted_dir = extract_archive(archive_path, temp_dir)
        uploads_dir, path_mapping = move_files_to_single_folder(extracted_dir)
        update_md_files(extracted_dir, path_mapping)
        new_archive = create_archive(extracted_dir, output_archive_name)
        print(f"Новый архив создан: {new_archive}")
    finally:
        # Удаляем временную директорию
        shutil.rmtree(temp_dir)
