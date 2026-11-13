"""Stage 2: прямые зависимости указанной версии Python-пакета."""

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

from .repository import direct_dependencies


def build_parser():
    """Описать семь параметров принятого первого этапа."""
    parser = argparse.ArgumentParser(
        description="Python dependencies: stage 2"
    )
    parser.add_argument(
        "--package", required=True, help="Имя Python-пакета"
    )
    parser.add_argument(
        "--repository", required=True,
        help="Корень JSON API PyPI или путь к тестовому JSON"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Тестовый режим: обработка графа добавляется в stage 3"
    )
    parser.add_argument(
        "--output", default="graph.svg", help="Имя будущего SVG"
    )
    parser.add_argument(
        "--filter", default="", help="Фильтр для stage 3"
    )
    parser.add_argument(
        "--version", required=True, help="Точная запись версии пакета"
    )
    parser.add_argument(
        "--max-depth", required=True, type=int,
        help="Глубина от 0: применяется начиная со stage 3"
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
    if args.filter and not re.fullmatch(r"[A-Za-z0-9+_.-]+", args.filter):
        raise ValueError(
            "--filter: нужны символы имени пакета, без пробелов"
        )
    if args.filter and args.filter in args.package:
        raise ValueError("--filter: исключает сам анализируемый пакет")


def validate_version(args):
    """Проверить запись версии, не реализуя весь стандарт PEP 440."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]*", args.version):
        raise ValueError("--version: версия содержит недопустимые символы")


def validate_depth(args):
    """Проверить неотрицательную глубину анализа."""
    if args.max_depth < 0:
        raise ValueError("--max-depth: глубина не может быть отрицательной")


def arguments(argv=None):
    """Прочитать параметры и сообщить об ошибках ввода."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_package(args)
        validate_repository(args)
        validate_output(args)
        validate_filter(args)
        validate_version(args)
        validate_depth(args)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return args


def execute(args):
    """Получить и вывести только прямые требования данного релиза."""
    if args.test:
        raise ValueError("Обработка тестового графа добавляется в stage 3")
    dependencies = direct_dependencies(
        args.repository, args.package, args.version
    )
    print("\n".join(dependencies) or "(нет объявленных прямых зависимостей)")


def main(argv=None):
    """Выполнить второй этап и обработать ошибки данных и сети."""
    args = arguments(argv)
    try:
        execute(args)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
