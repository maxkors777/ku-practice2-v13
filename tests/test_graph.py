"""Проверки BFS, фильтра, глубины, циклов и тестового JSON."""

from pathlib import Path
import tempfile
import unittest

from src.graph import bfs, load_test_graph


class GraphTests(unittest.TestCase):
    """Обойти известные графы с проверкой содержимого и порядка."""

    def test_chain_levels(self):
        """Проверить границы уровней 0, 1, 2 и полный обход."""
        graph = {"A": ["B"], "B": ["C"], "C": []}
        expected = [{"A": []}, {"A": ["B"], "B": []}, graph]
        for depth, result in enumerate(expected):
            self.assertEqual(bfs(graph, "A", max_depth=depth), result)
        self.assertEqual(bfs(graph, "A"), graph)

    def test_bfs_order(self):
        """Обработать соседей раньше их потомков."""
        graph = {"A": ["B", "C"], "B": ["D"], "C": [], "D": []}
        self.assertEqual(list(bfs(graph, "A")), ["A", "B", "C", "D"])

    def test_cycles(self):
        """Сохранить рёбра циклов и завершить обход."""
        for graph in ({"A": ["A"]}, {"A": ["B"], "B": ["A"]}):
            self.assertEqual(bfs(graph, "A"), graph)

    def test_diamond_filter(self):
        """Общий потомок остаётся доступен через разрешённую ветвь."""
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(
            bfs(graph, "A", "B", 2), {"A": ["C"], "C": ["D"], "D": []}
        )

    def test_isolated_and_chain_filter(self):
        """Сохранить корень при отсутствии доступных соседей."""
        self.assertEqual(bfs({"A": []}, "A"), {"A": []})
        self.assertEqual(bfs({"A": ["B"], "B": []}, "A", "B"), {"A": []})

    def test_invalid_start_and_depth(self):
        """Отклонить отсутствующий корень, исключение корня и глубину -1."""
        for start, excluded, depth in [("X", "", 1), ("A", "A", 1),
                                       ("A", "", -1)]:
            with self.assertRaises(ValueError):
                bfs({"A": []}, start, excluded, depth)

    def test_no_loading_boundary(self):
        """Не вызывать источник для вершин на предельном уровне."""
        visited = []

        def source(node):
            """Зафиксировать каждое раскрытие вершины."""
            visited.append(node)
            return ["B"]

        self.assertEqual(bfs(source, "A", max_depth=1), {"A": ["B"], "B": []})
        self.assertEqual(visited, ["A"])

    def test_deep_chain_without_recursion(self):
        """Обойти цепочку длиннее стандартного лимита рекурсии Python."""
        graph = {str(n): [str(n + 1)] for n in range(1500)}
        graph["1500"] = []
        self.assertEqual(len(bfs(graph, "0")), 1501)

    def test_json_validation(self):
        """Принять BOM и отклонить неверную структуру графа."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.json"
            path.write_text('{"A": []}', encoding="utf-8-sig")
            self.assertEqual(load_test_graph(path), {"A": []})
            for text in ('[]', '{}', '{"a":[]}', '{"A":1}', '{"A":["B"]}'):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_test_graph(path)
