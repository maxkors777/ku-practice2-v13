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


def bfs(graph, start, excluded=""):
    """Обойти зависимости очередью, без рекурсии."""
    if start not in graph:
        raise ValueError(f"Пакет {start} не найден")
    if excluded and excluded in start:
        raise ValueError("Фильтр исключает начальный пакет")
    queue = deque([start])
    visited = {start}
    result = {}
    while queue:
        current = queue.popleft()
        if graph[current] is None:
            raise ValueError(
                f"Не найден однозначный пакет-поставщик: {current}"
            )
        dependencies = [
            name for name in sorted(graph[current])
            if not excluded or excluded not in name
        ]
        result[current] = dependencies
        for dependency in dependencies:
            if dependency not in visited:
                visited.add(dependency)
                queue.append(dependency)
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
