"""Тестовый граф и BFS без рекурсии с глубиной и фильтром."""

from collections import deque
import json
from pathlib import Path
import re


def node_name(node):
    """Отделить имя пакета от версии и extras."""
    return node[0] if isinstance(node, tuple) else node


def node_label(node):
    """Показать версию и дополнительные возможности Python-пакета."""
    if not isinstance(node, tuple):
        return node
    name, version, extras = node
    suffix = "[" + ",".join(extras) + "]" if extras else ""
    return f"{name}{suffix}@{version}"


def load_test_graph(path):
    """Прочитать замкнутый JSON-граф с именами A-Z."""
    graph = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(graph, dict) or not graph:
        raise ValueError("Нужен непустой JSON-объект с пакетами")
    for name, dependencies in graph.items():
        if not re.fullmatch(r"[A-Z]+", name):
            raise ValueError("Имена тестовых пакетов: только буквы A-Z")
        if not isinstance(dependencies, list):
            raise ValueError(f"{name}: зависимости должны быть списком")
        for dependency in dependencies:
            if not isinstance(dependency, str) or dependency not in graph:
                raise ValueError(f"{name}: неизвестная зависимость")
    return graph


def validate_start(source, start, excluded, max_depth):
    """Проверить исходную вершину и глубину."""
    if not callable(source) and start not in source:
        raise ValueError(f"Пакет {start} не найден")
    if excluded and excluded in node_name(start):
        raise ValueError("Фильтр исключает начальный пакет")
    if max_depth is not None and max_depth < 0:
        raise ValueError("Глубина не может быть отрицательной")


def neighbors(source, node, excluded):
    """Получить соседей из словаря либо ленивого источника."""
    dependencies = source(node) if callable(source) else source[node]
    return sorted({
        dependency for dependency in dependencies
        if not excluded or excluded not in node_name(dependency)
    }, key=node_label)


def bfs(source, start, excluded="", max_depth=None):
    """Обойти уровни через очередь; глубина корня равна нулю."""
    validate_start(source, start, excluded, max_depth)
    queue = deque([(start, 0)])
    visited, result = {start}, {}
    while queue:
        node, depth = queue.popleft()
        dependencies = []
        if max_depth is None or depth < max_depth:
            dependencies = neighbors(source, node, excluded)
        result[node] = dependencies
        for dependency in dependencies:
            if dependency not in visited:
                visited.add(dependency)
                queue.append((dependency, depth + 1))
    return result


def print_graph(graph):
    """Вывести граф в порядке BFS."""
    for node, dependencies in graph.items():
        text = ", ".join(node_label(value) for value in dependencies) or "(нет)"
        print(node_label(node) + " -> " + text)
