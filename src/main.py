"""Этап 2: получение прямых зависимостей Alpine APK."""

import argparse
from pathlib import Path
import re
import sys
import tarfile
from urllib.parse import urlparse
from .repository import direct_dependencies, load_repository


def build_parser():
    """Описать параметры, которые принимает программа."""
    parser = argparse.ArgumentParser(
        description="Alpine dependencies: этап 2"
    )
    parser.add_argument(
        "--package", required=True, help="Имя пакета"
    )
    parser.add_argument(
        "--repository", required=True,
        help="URL репозитория или путь к тестовому JSON"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Использовать тестовый JSON"
    )
    parser.add_argument(
        "--output", default="graph.svg",
        help="Имя выходного файла SVG"
    )
    parser.add_argument(
        "--filter", default="",
        help="Исключать имена с указанной подстрокой"
    )
    return parser


def validate_package(args):
    """Проверить имя обычного или тестового пакета."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+_.-]*", args.package):
        raise ValueError("--package: недопустимое имя")
    if args.test and not re.fullmatch(r"[A-Z]+", args.package):
        raise ValueError(
            "--package: в тестовом режиме нужны большие латинские буквы"
        )


def validate_repository(args):
    """Проверить существование файла либо формат URL."""
    if args.test:
        if not Path(args.repository).is_file():
            raise ValueError("--repository: файл не найден")
    else:
        url = urlparse(args.repository)
        if url.scheme not in ("http", "https") or not url.netloc:
            raise ValueError("--repository: нужен полный HTTP(S) URL")


def validate_output(args):
    """Проверить расширение файла и родительскую папку."""
    output = Path(args.output)
    if output.suffix.lower() != ".svg" or not output.stem:
        raise ValueError("--output: нужен путь к файлу .svg")
    if output.is_dir():
        raise ValueError("--output: нужен путь к файлу .svg")
    if not output.parent.is_dir():
        raise ValueError("--output: родительская папка не существует")


def validate_filter(args):
    """Проверить символы фильтра и исключение корневого пакета."""
    if args.filter and not re.fullmatch(
        r"[A-Za-z0-9+_.-]+", args.filter
    ):
        raise ValueError(
            "--filter: нужны символы имени пакета, без пробелов"
        )
    if args.filter and args.filter in args.package:
        raise ValueError("--filter: исключает сам анализируемый пакет")


def arguments(argv=None):
    """Прочитать параметры и сообщить об ошибках ввода."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_package(args)
        validate_repository(args)
        validate_output(args)
        validate_filter(args)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return args


def main(argv=None):
    """Загрузить репозиторий и вывести прямые зависимости."""
    args = arguments(argv)
    try:
        if args.test:
            raise ValueError(
                "Чтение тестового графа будет добавлено на этапе 3"
            )
        packages = load_repository(args.repository)
        dependencies = direct_dependencies(packages, args.package)
        if dependencies:
            for dependency in dependencies:
                print(dependency)
        else:
            print("(нет прямых зависимостей)")
    except (OSError, ValueError, tarfile.TarError, EOFError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
