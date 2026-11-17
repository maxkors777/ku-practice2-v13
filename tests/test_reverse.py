"""Обратный граф, повторное использование BFS и интеграция stage 4."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.graph import bfs
from src.main import arguments, main
from src.reverse import read_roots, reverse_graph, universe_graph


class ReverseTests(unittest.TestCase):
    """Проверить прямых и транзитивных зависимых на известных графах."""

    def base_args(self):
        """Вернуть обычный запуск реального Python-источника."""
        return ["--package", "base", "--version", "1.0",
                "--repository", "https://pypi.org/pypi", "--max-depth", "2"]

    def assert_cli_rejected(self, args):
        """Отклонить неправильную комбинацию настроек кодом 2."""
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                arguments(args)
        self.assertEqual(caught.exception.code, 2)

    def test_edges(self):
        """Развернуть рёбра, сохранив изолированные вершины."""
        graph = {"A": ["B"], "B": [], "C": []}
        self.assertEqual(reverse_graph(graph), {"A": [], "B": ["A"], "C": []})

    def test_transitive(self):
        """Найти прямых и косвенных зависимых прежним BFS."""
        graph = {"A": ["B"], "B": ["C"], "C": []}
        self.assertEqual(bfs(reverse_graph(graph), "C"),
                         {"C": ["B"], "B": ["A"], "A": []})

    def test_depth(self):
        """Применить глубину после разворота, а не до него."""
        graph = reverse_graph({"A": ["B"], "B": ["C"], "C": []})
        self.assertEqual(bfs(graph, "C", max_depth=0), {"C": []})
        self.assertEqual(bfs(graph, "C", max_depth=1), {"C": ["B"], "B": []})

    def test_diamond_filter(self):
        """Сохранить альтернативный обратный путь через C."""
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(bfs(reverse_graph(graph), "D", "B", 2),
                         {"D": ["C"], "C": ["A"], "A": []})

    def test_cycle(self):
        """Завершить цикл и сохранить его обратные рёбра."""
        graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
        self.assertEqual(bfs(reverse_graph(graph), "A"),
                         {"A": ["C"], "C": ["B"], "B": ["A"]})

    def test_self_cycle(self):
        """Корректно обработать зависимость от самого себя."""
        self.assertEqual(bfs(reverse_graph({"A": ["A"]}), "A"), {"A": ["A"]})

    def test_no_dependents(self):
        """Сохранить корень с пустым списком обратных зависимостей."""
        self.assertEqual(bfs(reverse_graph({"A": ["B"], "B": []}), "A"),
                         {"A": []})

    def test_unknown_target(self):
        """Отклонить граф с необъявленной целью ребра."""
        with self.assertRaises(ValueError):
            reverse_graph({"A": ["B"]})

    def test_version_identity(self):
        """Не смешивать зависимых разных версий одного имени."""
        first, second, parent = ("base", "1", ()), ("base", "2", ()), (
            "parent", "1", (),
        )
        result = reverse_graph({first: [], second: [], parent: [second]})
        self.assertEqual(result[first], [])
        self.assertEqual(result[second], [parent])

    def test_roots(self):
        """Нормализовать имена исходных пакетов и убрать повторы."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "roots.json"
            path.write_text(json.dumps([
                {"package": "Demo_Name", "version": "1"},
                {"package": "demo-name", "version": "1"},
            ]), encoding="utf-8")
            self.assertEqual(read_roots(path), [("demo-name", "1", ())])

    def test_invalid_roots(self):
        """Отклонить неправильный JSON-список и записи пакетов."""
        values = [{}, [], ["A"], [{"package": "a"}],
                  [{"package": "a", "version": 1}],
                  [{"package": "bad name", "version": "1"}]]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "roots.json"
            for value in values:
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.subTest(value=value), self.assertRaises(ValueError):
                    read_roots(path)

    def test_entire_universe(self):
        """Найти родителя вне исходящего подграфа выбранной вершины."""
        target, mid, parent = ("base", "1", ()), ("mid", "1", ()), (
            "parent", "1", (),
        )
        graph = {target: [], mid: [target], parent: [mid]}

        class Source:
            """Предоставить известный граф без HTTP."""

            def dependencies(self, node):
                """Вернуть соседей тестовой Python-вершины."""
                return graph[node]

        combined = universe_graph(Source(), target, [parent])
        self.assertEqual(bfs(reverse_graph(combined), target, max_depth=1),
                         {target: [mid], mid: []})
        self.assertIn(parent, combined)

    def test_filtered_seed(self):
        """Исключённый исходный пакет не должен загружаться."""
        target, seed = ("base", "1", ()), ("skip", "1", ())

        class Source:
            """Источник, запрещающий обращение к исключённому пакету."""

            def dependencies(self, node):
                """Проверить, что посещается только начальный пакет."""
                if node != target:
                    raise AssertionError("Исключённый пакет был загружен")
                return []

        self.assertEqual(universe_graph(Source(), target, [seed], "skip"),
                         {target: []})

    def test_real_reverse_requires_roots(self):
        """Потребовать явную область вместо мнимого глобального поиска."""
        self.assert_cli_rejected(self.base_args() + ["--reverse"])

    def test_roots_need_reverse(self):
        """Параметр области не используется в обычном прямом режиме."""
        self.assert_cli_rejected(self.base_args() + ["--roots", "missing.json"])

    def test_cli_reverse_full_json(self):
        """Взять весь JSON и вывести список зависимых без самого корня."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.json"
            path.write_text('{"A":["B"],"B":["C"],"C":[]}', encoding="utf-8")
            args = self.base_args() + ["--package", "C", "--test",
                                       "--repository", str(path), "--reverse"]
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(args), 0)
            self.assertEqual(output.getvalue().splitlines(), [
                "C -> B", "B -> A", "A -> (нет)",
                "Обратные зависимости: B, A",
            ])

    def test_cli_self_not_in_summary(self):
        """Петля не должна добавлять корень в итоговый список зависимых."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.json"
            path.write_text('{"A":["A"]}', encoding="utf-8")
            args = self.base_args() + ["--package", "A", "--test",
                                       "--repository", str(path), "--reverse"]
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(args), 0)
            self.assertIn("Обратные зависимости: (нет)", output.getvalue())

    def test_cli_real_explicit_scope(self):
        """Связать чтение области, полный граф и обратный BFS."""
        target, parent = ("base", "1.0", ()), ("parent", "1", ())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "roots.json"
            path.write_text('[{"package":"parent","version":"1"}]')
            with patch("src.main.PythonRepository") as mocked:
                mocked.return_value.dependencies.side_effect = lambda n: (
                    [target] if n == parent else []
                )
                args = self.base_args() + ["--reverse", "--roots", str(path)]
                with redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(args), 0)
            self.assertIn("base@1.0 -> parent@1", output.getvalue())
