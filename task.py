#!/usr/bin/env python3
import configparser
import argparse
import sys
import os
import re

def run_stage1(config_path):
    """Выполнение этапа 1: Минимальный прототип с конфигурацией"""
    print("=== ЭТАП 1: МИНИМАЛЬНЫЙ ПРОТОТИП С КОНФИГУРАЦИЕЙ ===")
    
    # 1. Чтение INI конфигурации
    if not os.path.exists(config_path):
        print(f"Ошибка: файл {config_path} не найден")
        return 1
    
    config = configparser.ConfigParser()
    try:
        config.read(config_path)
    except Exception as e:
        print(f"Ошибка чтения конфигурации: {e}")
        return 1
    
    if 'DEFAULT' not in config:
        print("Ошибка: не найден раздел [DEFAULT]")
        return 1
    
    # 2. Извлечение параметров
    config_dict = dict(config['DEFAULT'])
    package_name = config_dict.get('package_name', '')
    repository_url = config_dict.get('repository_url', '')
    package_version = config_dict.get('package_version', '')
    max_depth = config_dict.get('max_depth', '')
    filter_substring = config_dict.get('filter_substring', '')
    test_mode_str = config_dict.get('test_mode', 'false').lower()
    
    # 3. Валидация параметров
    errors = []
    
    # Обязательные поля
    if not package_name:
        errors.append("Не указано имя пакета")
    if not repository_url:
        errors.append("Не указан URL репозитория")
    
    # test_mode validation
    if test_mode_str not in ['true', 'false']:
        errors.append("test_mode должен быть 'true' или 'false'")
    test_mode = test_mode_str == 'true'
    
    # package_version validation
    if package_version and not re.match(r'^\d+\.\d+(\.\d+)?$', package_version):
        errors.append("package_version должен быть в формате X.Y или X.Y.Z")
    
    # max_depth validation
    if max_depth:
        try:
            depth = int(max_depth)
            if depth <= 0:
                errors.append("max_depth должен быть положительным числом")
        except ValueError:
            errors.append("max_depth должен быть числом")
    
    # URL validation
    if not test_mode and not repository_url.startswith(('http://', 'https://')):
        errors.append("В реальном режиме repository_url должен быть HTTP/HTTPS URL")
    
    if errors:
        print("Ошибки конфигурации:")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    # 4. Вывод параметров в формате ключ-значение
    print("Параметры конфигурации (ключ-значение):")
    print(f"  package_name: {package_name}")
    print(f"  repository_url: {repository_url}")
    print(f"  test_mode: {test_mode}")
    print(f"  package_version: {package_version}")
    print(f"  max_depth: {max_depth}")
    print(f"  filter_substring: {filter_substring}")
    
    print("Конфигурация загружена успешно")
    return 0

def main():
    parser = argparse.ArgumentParser(description='Визуализатор графа зависимостей для менеджера пакетов Rust/Cargo')
    parser.add_argument('--config', required=True, help='Путь к INI-файлу конфигурации')
    parser.add_argument('--stage', type=int, default=1, help='Номер этапа для выполнения (1-5)')
    args = parser.parse_args()
    
    if args.stage == 1:
        return run_stage1(args.config)
    else:
        print(f"Этап {args.stage} еще не реализован")
        return 1

if __name__ == "__main__":
    sys.exit(main())