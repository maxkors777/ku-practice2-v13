"""Чтение тестового графа и обход зависимостей в ширину."""

from collections import deque
import json
from pathlib import Path
import re


def load_test_graph(path):
    """Прочитать JSON и проверить описание тестового графа."""
    text = Path(path).read_text(encoding="utf-8-sig")
    graph = json.loads(text)
    if not isinstance(graph, dict) or not graph:
        raise ValueError("Нужен непустой JSON-объект с пакетами")
    for name, dependencies in graph.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Z]+", name):
            raise ValueError("Имена тестовых пакетов: только буквы A-Z")
        if not isinstance(dependencies, list):
            raise ValueError(f"{name}: зависимости должны быть списком")
        for dependency in dependencies:
            if not isinstance(dependency, str) or dependency not in graph:
                raise ValueError(f"{name}: неизвестная зависимость")
    return graph


def filtered_dependencies(graph, current, excluded):
    """Проверить вершину и отфильтровать её зависимости."""
    if graph[current] is None:
        raise ValueError(
            f"Не найден однозначный пакет-поставщик: {current}"
        )
    return [
        name for name in sorted(graph[current])
        if not excluded or excluded not in name
    ]


def validate_start(graph, start, excluded, max_depth):
    """Проверить корень, фильтр и допустимость глубины."""
    if start not in graph:
        raise ValueError(f"Пакет {start} не найден")
    if excluded and excluded in start:
        raise ValueError("Фильтр исключает начальный пакет")
    if max_depth is not None and max_depth < 0:
        raise ValueError("Глубина не может быть отрицательной")


def dependencies_at_depth(graph, current, excluded, depth, max_depth):
    """Не раскрывать зависимости на предельном уровне."""
    if max_depth is not None and depth >= max_depth:
        return []
    return filtered_dependencies(graph, current, excluded)


def bfs(graph, start, excluded="", max_depth=None):
    """Обойти граф очередью с учётом максимальной глубины."""
    validate_start(graph, start, excluded, max_depth)
    queue = deque([(start, 0)])
    visited = {start}
    result = {}
    while queue:
        current, depth = queue.popleft()
        dependencies = dependencies_at_depth(
            graph, current, excluded, depth, max_depth
        )
        result[current] = dependencies
        for dependency in dependencies:
            if dependency not in visited:
                visited.add(dependency)
                queue.append((dependency, depth + 1))
    return result


def reverse_graph(graph):
    """Развернуть рёбра всего доступного графа."""
    result = {name: [] for name in graph}
    for name, dependencies in graph.items():
        for dependency in dependencies or []:
            result[dependency].append(name)
    return {
        name: sorted(set(dependencies))
        for name, dependencies in result.items()
    }
