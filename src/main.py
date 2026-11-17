"""Stage 4: прямые и транзитивные обратные зависимости Python."""

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

from .repository import normalize_name
from .graph import bfs, load_test_graph, node_label, print_graph
from .reverse import read_roots, reverse_graph, universe_graph
from .python_graph import PythonRepository


def build_parser():
    """Описать семь параметров принятого первого этапа."""
    parser = argparse.ArgumentParser(
        description="Python dependencies: stage 4"
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
        help="Читать тестовый JSON-граф"
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
        help="Максимальная глубина: 0 — только начальный пакет"
    )
    parser.add_argument(
        "--reverse", action="store_true", help="Обратные зависимости"
    )
    parser.add_argument(
        "--roots", help="JSON исходных пакетов для обратного поиска в PyPI"
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


def validate_reverse_options(args):
    """Проверить явно определённую область обратного анализа."""
    if args.roots and (not args.reverse or args.test):
        raise ValueError("--roots используется только с --reverse без --test")
    if args.reverse and not args.test and not args.roots:
        raise ValueError("Для обратного поиска в PyPI укажите --roots")
    if args.roots and not Path(args.roots).is_file():
        raise ValueError("--roots: файл не найден")


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
        validate_reverse_options(args)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return args


def root_node(args):
    """Вернуть буквенную вершину либо конкретный Python-релиз."""
    if args.test:
        return args.package
    return normalize_name(args.package), args.version, ()


def selected_graph(args):
    """Выбрать источник, развернуть весь граф и выполнить прежний BFS."""
    root = root_node(args)
    if args.test:
        source = load_test_graph(args.repository)
    else:
        repository = PythonRepository(args.repository, args.filter)
        repository.info(root)
        source = repository.dependencies
        if args.reverse:
            source = universe_graph(
                repository, root, read_roots(args.roots), args.filter
            )
    if args.reverse:
        source = reverse_graph(source)
    return bfs(source, root, args.filter, args.max_depth)


def execute(args):
    """Показать выбранный граф и итог обратного поиска."""
    selected = selected_graph(args)
    print_graph(selected)
    if args.reverse:
        root = root_node(args)
        dependents = [node_label(node) for node in selected if node != root]
        print("Обратные зависимости: " + (", ".join(dependents) or "(нет)"))


def main(argv=None):
    """Выполнить stage 4 и обработать ошибки данных и сети."""
    args = arguments(argv)
    try:
        execute(args)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
