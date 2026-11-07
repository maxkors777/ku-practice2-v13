"""Проверки тестового репозитория и обхода BFS."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from src.graph import bfs, load_test_graph
from src.main import main


DIAMOND = {
    "A": ["B", "C"],
    "B": ["D"],
    "C": ["D"],
    "D": [],
}


def write_graph(directory, graph):
    """Записать тестовый граф во временный файл."""
    path = Path(directory) / "graph.json"
    path.write_text(json.dumps(graph), encoding="utf-8")
    return path


class GraphTests(unittest.TestCase):
    """Проверки обхода, фильтрации и формата графа."""

    def test_breadth_first_order(self):
        """Соседи должны обрабатываться до следующего уровня."""
        result = bfs(DIAMOND, "A")
        self.assertEqual(list(result), ["A", "B", "C", "D"])
        self.assertEqual(result, DIAMOND)

    def test_cycle(self):
        """Обход должен завершаться и сохранять рёбра цикла."""
        graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
        self.assertEqual(bfs(graph, "A"), graph)

    def test_self_cycle(self):
        """Обработать зависимость пакета от самого себя."""
        graph = {"A": ["A"]}
        self.assertEqual(bfs(graph, "A"), graph)

    def test_filter_chain(self):
        """Исключение вершины должно отсекать путь через неё."""
        graph = {"A": ["B"], "B": ["C"], "C": []}
        self.assertEqual(bfs(graph, "A", "B"), {"A": []})

    def test_filter_diamond(self):
        """Сохранить общий узел, доступный по другой ветви."""
        expected = {"A": ["C"], "C": ["D"], "D": []}
        self.assertEqual(bfs(DIAMOND, "A", "B"), expected)

    def test_isolated(self):
        """Сохранить пакет без зависимостей."""
        self.assertEqual(bfs({"A": []}, "A"), {"A": []})

    def test_invalid_start(self):
        """Отклонить отсутствующий или исключённый корень."""
        for start, excluded in [("Z", ""), ("A", "A")]:
            with self.subTest(start=start, excluded=excluded):
                with self.assertRaises(ValueError):
                    bfs(DIAMOND, start, excluded)

    def test_read_json(self):
        """Прочитать правильный граф из файла."""
        with tempfile.TemporaryDirectory() as directory:
            path = write_graph(directory, DIAMOND)
            self.assertEqual(load_test_graph(path), DIAMOND)

    def test_invalid_json(self):
        """Отклонить неверные типы и неизвестные зависимости."""
        examples = [
            [],
            {},
            {"a": []},
            {"A": "B"},
            {"A": ["B"]},
            {"A": [1]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            for graph in examples:
                with self.subTest(graph=graph):
                    path = write_graph(directory, graph)
                    with self.assertRaises(ValueError):
                        load_test_graph(path)
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_test_graph(path)

    def test_test_mode_output(self):
        """Проверить подключение JSON, BFS и фильтра к main."""
        with tempfile.TemporaryDirectory() as directory:
            path = write_graph(directory, DIAMOND)
            output = io.StringIO()
            with redirect_stdout(output):
                code = main([
                    "--package", "A",
                    "--repository", str(path),
                    "--test",
                    "--filter", "B",
                ])
        self.assertEqual(code, 0)
        self.assertEqual(
            output.getvalue(),
            "A -> C\nC -> D\nD -> (нет)\n",
        )


if __name__ == "__main__":
    unittest.main()
