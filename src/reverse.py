"""Обратные рёбра и явно заданная область поиска Python-пакетов."""

import json
from pathlib import Path

from .graph import bfs, node_label, node_name
from .repository import normalize_name, validate_identity_values


def reverse_graph(graph):
    """Развернуть весь граф, сохранив изолированные вершины."""
    result = {node: set() for node in graph}
    for node, dependencies in graph.items():
        for dependency in dependencies:
            if dependency not in result:
                raise ValueError("Граф содержит необъявленную вершину")
            result[dependency].add(node)
    return {
        node: sorted(dependents, key=node_label)
        for node, dependents in result.items()
    }


def read_root(record):
    """Прочитать имя и точную версию одного исходного пакета."""
    if not isinstance(record, dict) or set(record) != {"package", "version"}:
        raise ValueError("Исходный пакет: объект с package и version")
    package, version = record["package"], record["version"]
    if not isinstance(package, str) or not isinstance(version, str):
        raise ValueError("Имя и версия исходного пакета должны быть строками")
    validate_identity_values(package, version)
    return normalize_name(package), version, ()


def read_roots(path):
    """Получить непустой список исходных релизов без повторов."""
    records = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(records, list) or not records:
        raise ValueError("Файл --roots должен содержать непустой JSON-список")
    return sorted({read_root(record) for record in records}, key=node_label)


def universe_graph(repository, target, roots, excluded=""):
    """Объединить полные графы исходных пакетов до разворота рёбер."""
    result = {}
    for root in [target] + list(roots):
        if excluded and excluded in node_name(root):
            continue
        selected = bfs(repository.dependencies, root, excluded)
        result.update(selected)
    return result
