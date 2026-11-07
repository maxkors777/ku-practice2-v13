"""Проверки построения графа настоящего репозитория."""

import unittest

from src.graph import bfs
from src.repository import (
    build_providers,
    dependency_name,
    repository_graph,
    resolve_dependency,
)


def package(depends=(), provides=()):
    """Создать небольшую запись пакета для теста."""
    return {
        "version": "1.0-r0",
        "depends": list(depends),
        "provides": list(provides),
    }


class ApkGraphTests(unittest.TestCase):
    """Проверки имён, поставщиков и неразрешённых зависимостей."""

    def test_dependency_names(self):
        """Отделить ограничения версий от имён требований."""
        examples = [
            ("lib>=1.0", "lib"),
            ("lib=1.0-r0", "lib"),
            ("lib~1.0", "lib"),
            ("so:libx.so.1", "so:libx.so.1"),
        ]
        for requirement, expected in examples:
            with self.subTest(requirement=requirement):
                self.assertEqual(dependency_name(requirement), expected)

    def test_provider_index(self):
        """Найти пакет, предоставляющий библиотеку."""
        packages = {
            "libx": package(provides=["so:libx.so.1=1"]),
        }
        providers = build_providers(packages)
        self.assertEqual(providers["so:libx.so.1"], {"libx"})

    def test_package_name_priority(self):
        """Предпочесть настоящее имя пакета дополнительному имени."""
        packages = {
            "lib": package(),
            "alternative": package(provides=["lib=1"]),
        }
        target = resolve_dependency(
            "lib>=1", packages, build_providers(packages)
        )
        self.assertEqual(target, "lib")

    def test_virtual_dependency(self):
        """Заменить требование библиотеки пакетом-поставщиком."""
        packages = {
            "app": package(depends=["so:libx.so.1"]),
            "libx": package(provides=["so:libx.so.1=1"]),
        }
        graph = repository_graph(packages)
        self.assertEqual(
            bfs(graph, "app"),
            {"app": ["libx"], "libx": []},
        )

    def test_conflicts(self):
        """Конфликт не должен становиться зависимостью."""
        packages = {
            "app": package(depends=["!blocked", "lib"]),
            "lib": package(),
        }
        graph = repository_graph(packages)
        self.assertEqual(graph["app"], ["lib"])
        self.assertNotIn("blocked", graph)

    def test_unresolved_dependency(self):
        """Ошибка нужна только при достижении неизвестного узла."""
        packages = {
            "app": package(),
            "other": package(depends=["missing"]),
        }
        graph = repository_graph(packages)
        self.assertEqual(bfs(graph, "app"), {"app": []})
        with self.assertRaisesRegex(ValueError, "пакет-поставщик"):
            bfs(graph, "other")

    def test_ambiguous_provider(self):
        """Не выбирать произвольно одного из двух поставщиков."""
        packages = {
            "app": package(depends=["so:libx.so.1"]),
            "first": package(provides=["so:libx.so.1=1"]),
            "second": package(provides=["so:libx.so.1=1"]),
        }
        graph = repository_graph(packages)
        self.assertIsNone(graph["so:libx.so.1"])
        with self.assertRaises(ValueError):
            bfs(graph, "app")

    def test_filter_unresolved_dependency(self):
        """Исключённую зависимость обходить не нужно."""
        packages = {
            "app": package(depends=["missing"]),
        }
        graph = repository_graph(packages)
        self.assertEqual(bfs(graph, "app", "missing"), {"app": []})

    def test_duplicate_edges(self):
        """Разные требования к одному пакету дают одно ребро."""
        packages = {
            "app": package(depends=["lib", "lib>=1", "so:libx.so.1"]),
            "lib": package(provides=["so:libx.so.1=1"]),
        }
        graph = repository_graph(packages)
        self.assertEqual(graph["app"], ["lib"])


if __name__ == "__main__":
    unittest.main()
