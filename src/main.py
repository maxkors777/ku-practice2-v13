"""Этап 5: визуализация графа зависимостей."""
import argparse
from pathlib import Path
import subprocess
import re
import sys
import tarfile
from urllib.parse import urlparse
from .repository import load_repository, repository_graph
from .graph import bfs, load_test_graph, reverse_graph
from .render import render_svg


def build_parser():
    """Описать параметры, которые принимает программа."""
    parser = argparse.ArgumentParser(
        description="Alpine dependencies: этап 5"
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
    parser.add_argument(
        "--reverse", action="store_true",
        help="Найти прямые и транзитивные обратные зависимости"
    )
    parser.add_argument(
        "--visualize", action="store_true",
        help="Сохранить PlantUML и изображение SVG"
    )
    parser.add_argument(
        "--jar", default="tools/plantuml.jar",
        help="Путь к файлу PlantUML JAR"
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


def load_graph(args):
    """Получить граф из тестового файла или индекса Alpine."""
    if args.test:
        return load_test_graph(args.repository)
    packages = load_repository(args.repository)
    if args.package not in packages:
        raise ValueError(
            f"Пакет {args.package} не найден в репозитории"
        )
    return repository_graph(packages)


def print_graph(graph):
    """Вывести вершины и связи в порядке обхода."""
    for name, dependencies in graph.items():
        text = ", ".join(dependencies) or "(нет)"
        print(name + " -> " + text)


def execute(args):
    """Выполнить выбранный анализ и необязательную отрисовку."""
    graph = load_graph(args)
    if args.reverse:
        graph = reverse_graph(graph)
    selected = bfs(graph, args.package, args.filter)
    print_graph(selected)
    if args.reverse:
        dependents = [name for name in selected if name != args.package]
        text = ", ".join(dependents) or "(нет)"
        print("Обратные зависимости: " + text)
    if args.visualize:
        output = render_svg(selected, args.output, args.jar)
        print(f"Создано изображение: {output}")


def main(argv=None):
    """Запустить анализ и обработать ошибки выполнения."""
    args = arguments(argv)
    try:
        execute(args)
    except (
        OSError, ValueError, tarfile.TarError, EOFError,
        subprocess.SubprocessError,
    ) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
