#!/usr/bin/env python3
import configparser
import argparse
import sys
import os
import re
import urllib.request
import json
import ssl

def load_config(config_path):
    """Загрузка и валидация конфигурации"""
    # ===== ЭТАП 1: Условие 1 - Источником параметров является конфигурационный файл формата INI =====
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file {config_path} not found")
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    if 'DEFAULT' not in config:
        raise ValueError("No [DEFAULT] section in config")
    
    config_dict = dict(config['DEFAULT'])
    
    # ===== ЭТАП 1: Условие 2 - Извлечение всех настраиваемых параметров =====
    package_name = config_dict.get('package_name', '')
    repository_url = config_dict.get('repository_url', '')
    package_version = config_dict.get('package_version', '')
    max_depth_str = config_dict.get('max_depth', '')
    filter_substring = config_dict.get('filter_substring', '')
    test_mode_str = config_dict.get('test_mode', 'false').lower()
    
    # ===== ЭТАП 1: Условие 4 - Обработка ошибок для всех параметров =====
    errors = []
    
    # Проверка обязательных полей
    if not package_name:
        errors.append("Не указано имя пакета")
    if not repository_url:
        errors.append("Не указан URL репозитория")
    
    # Валидация test_mode
    if test_mode_str not in ['true', 'false']:
        errors.append("test_mode должен быть 'true' или 'false'")
    test_mode = test_mode_str == 'true'
    
    # Валидация package_version
    if package_version and not re.match(r'^\d+\.\d+(\.\d+)?$', package_version):
        errors.append("package_version должен быть в формате X.Y или X.Y.Z")
    
    # Валидация max_depth
    max_depth = 0
    if max_depth_str:
        try:
            max_depth = int(max_depth_str)
            if max_depth <= 0:
                errors.append("max_depth должен быть положительным числом")
        except ValueError:
            errors.append("max_depth должен быть числом")
    
    # Валидация URL в реальном режиме
    if not test_mode and not repository_url.startswith(('http://', 'https://')):
        errors.append("В реальном режиме repository_url должен быть HTTP/HTTPS URL")
    
    if errors:
        raise ValueError("; ".join(errors))
    
    return {
        'package_name': package_name,
        'repository_url': repository_url,
        'test_mode': test_mode,
        'package_version': package_version,
        'max_depth': max_depth,
        'filter_substring': filter_substring
    }

def run_stage1(config_path):
    """Выполнение этапа 1: Минимальный прототип с конфигурацией"""
    print("=== ЭТАП 1: МИНИМАЛЬНЫЙ ПРОТОТИП С КОНФИГУРАЦИЕЙ ===")
    
    try:
        config = load_config(config_path)
        
        # ===== ЭТАП 1: Условие 3 - Вывод всех параметров в формате ключ-значение =====
        print("Параметры конфигурации (ключ-значение):")
        print(f"  package_name: {config['package_name']}")           # Имя анализируемого пакета
        print(f"  repository_url: {config['repository_url']}")       # URL-адрес репозитория
        print(f"  test_mode: {config['test_mode']}")                 # Режим работы с тестовым репозиторием
        print(f"  package_version: {config['package_version']}")     # Версия пакета
        print(f"  max_depth: {config['max_depth']}")                 # Максимальная глубина анализа зависимостей
        print(f"  filter_substring: {config['filter_substring']}")   # Подстрока для фильтрации пакетов
        
        print("Конфигурация загружена успешно")
        return 0
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

def get_dependencies_from_crates(repository_url, package_name, package_version):
    """Получение зависимостей из Crates.io API"""
    
    # ===== ЭТАП 2: Условие 1 - Использовать формат пакетов Rust (Cargo) =====
    # ===== ЭТАП 2: Условие 3 - Извлечь информацию используя URL-адрес репозитория =====
    url = f"{repository_url}/api/v1/crates/{package_name}/{package_version}/dependencies"
    
    try:
        # Запрещено использовать менеджеры пакетов и сторонние библиотеки - используем только стандартный urllib
        
        # Создаем SSL контекст для обхода проблем с сертификатами на macOS
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'DependencyGraphTool/1.0'}
        )
        
        # Выполняем HTTP запрос к API crates.io с SSL контекстом
        with urllib.request.urlopen(req, context=context) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        # Извлекаем информацию о прямых зависимостях
        dependencies = []
        for dep in data.get('dependencies', []):
            dependencies.append({
                'name': dep['crate_id'],
                'version_req': dep.get('req', '*'),
                'kind': dep.get('kind', 'normal')
            })
        
        return dependencies
        
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Пакет {package_name} версии {package_version} не найден")
        else:
            raise ValueError(f"Ошибка API: {e.code} {e.reason}")
    except Exception as e:
        raise ValueError(f"Ошибка при получении зависимостей: {e}")

def run_stage2(config_path):
    """Выполнение этапа 2: Сбор данных"""
    print("=== ЭТАП 2: СБОР ДАННЫХ ===")
    
    try:
        config = load_config(config_path)
        
        # Проверка что используем реальный режим (не тестовый)
        if config['test_mode']:
            print("Ошибка: Для этапа 2 должен использоваться реальный режим (test_mode=false)")
            return 1
        
        # ===== ЭТАП 2: Условие 2 - Информация получается для заданной пользователем версии пакета =====
        if not config['package_version']:
            print("Ошибка: Для этапа 2 необходимо указать package_version")
            return 1
        
        # Проверка что используется правильный репозиторий для Rust/Cargo
        if "crates.io" not in config['repository_url']:
            print("Ошибка: Для Rust/Cargo пакетов должен использоваться репозиторий crates.io")
            return 1
        
        print(f"Получение зависимостей для пакета {config['package_name']} версии {config['package_version']}...")
        
        # Получаем зависимости из Crates.io API
        dependencies = get_dependencies_from_crates(
            config['repository_url'],
            config['package_name'], 
            config['package_version']
        )
        
        # ===== ЭТАП 2: Условие 4 - Вывести на экран все прямые зависимости заданного пакета =====
        print(f"Прямые зависимости пакета {config['package_name']}:")
        if not dependencies:
            print("  (нет зависимостей)")
        else:
            for dep in dependencies:
                kind_info = f" ({dep['kind']})" if dep['kind'] != 'normal' else ""
                print(f"  - {dep['name']} {dep['version_req']}{kind_info}")
        
        print("Зависимости успешно получены")
        return 0
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

def main():
    # ===== ЭТАП 1: Условие 1 - CLI приложение с настраиваемыми параметрами =====
    parser = argparse.ArgumentParser(description='Визуализатор графа зависимостей для менеджера пакетов Rust/Cargo')
    parser.add_argument('--config', required=True, help='Путь к INI-файлу конфигурации')
    parser.add_argument('--stage', type=int, choices=[1, 2, 3, 4, 5], default=1, 
                       help='Номер этапа для выполнения')
    
    args = parser.parse_args()
    
    if args.stage == 1:
        return run_stage1(args.config)
    elif args.stage == 2:
        return run_stage2(args.config)
    else:
        print(f"Этап {args.stage} еще не реализован")
        return 1

if __name__ == "__main__":
    sys.exit(main())