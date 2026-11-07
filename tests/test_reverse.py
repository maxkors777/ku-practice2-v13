"""Проверки обратных зависимостей."""

from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from src.graph import bfs, reverse_graph
from src.main import main


CHAIN = {
    "A": ["B"],
    "B": ["C"],
    "C": [],
}

DIAMOND = {
    "A": ["B", "C"],
    "B": ["D"],
    "C": ["D"],
    "D": [],
}


def package(depends=()):
    """Создать запись пакета для проверки запуска."""
    return {
        "version": "1.0-r0",
        "depends": list(depends),
        "provides": [],
    }


class ReverseTests(unittest.TestCase):
    """Проверки обратного графа и повторного применения BFS."""

    def test_reverse_edges(self):
        """Развернуть связи и сохранить изолированную вершину."""
        graph = dict(CHAIN)
        graph["D"] = []
        self.assertEqual(
            reverse_graph(graph),
            {"A": [], "B": ["A"], "C": ["B"], "D": []},
        )

    def test_transitive_dependents(self):
        """Найти непосредственные и косвенные зависимости."""
        result = bfs(reverse_graph(CHAIN), "C")
        self.assertEqual(list(result), ["C", "B", "A"])
        self.assertEqual(
            result, {"C": ["B"], "B": ["A"], "A": []}
        )

    def test_branching(self):
        """Обойти обе обратные ветви и общий узел."""
        result = bfs(reverse_graph(DIAMOND), "D")
        self.assertEqual(list(result), ["D", "B", "C", "A"])
        self.assertEqual(result["B"], ["A"])
        self.assertEqual(result["C"], ["A"])

    def test_cycle(self):
        """Завершить обратный обход цикла."""
        graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
        result = bfs(reverse_graph(graph), "A")
        self.assertEqual(
            result, {"A": ["C"], "C": ["B"], "B": ["A"]}
        )

    def test_filter_chain(self):
        """Отсечь обратную ветвь через исключённый пакет."""
        result = bfs(reverse_graph(CHAIN), "C", "B")
        self.assertEqual(result, {"C": []})

    def test_filter_diamond(self):
        """Сохранить зависимый пакет через другую ветвь."""
        result = bfs(reverse_graph(DIAMOND), "D", "B")
        self.assertEqual(
            result, {"D": ["C"], "C": ["A"], "A": []}
        )

    def test_no_dependents(self):
        """Вернуть только корень, если от него никто не зависит."""
        self.assertEqual(
            bfs(reverse_graph(CHAIN), "A"), {"A": []}
        )

    def test_unresolved_node(self):
        """Развернуть известные связи при наличии значения None."""
        graph = {"app": ["missing"], "missing": None}
        self.assertEqual(
            reverse_graph(graph),
            {"app": [], "missing": ["app"]},
        )

    def test_program_uses_full_repository(self):
        """Искать обратные связи во всём загруженном индексе."""
        packages = {
            "app": package(depends=["lib"]),
            "lib": package(),
        }
        output = io.StringIO()
        with patch(
            "src.main.load_repository", return_value=packages
        ):
            with redirect_stdout(output):
                code = main([
                    "--package", "lib",
                    "--repository", "https://example.com/main",
                    "--reverse",
                ])
        self.assertEqual(code, 0)
        self.assertEqual(
            output.getvalue(),
            "lib -> app\n"
            "app -> (нет)\n"
            "Обратные зависимости: app\n",
        )


if __name__ == "__main__":
    unittest.main()
