"""Проверки максимальной глубины обхода."""

import unittest

from src.graph import bfs


class DepthTests(unittest.TestCase):
    """Проверить ограничение уровней обхода."""

    def setUp(self):
        """Подготовить цепочку."""
        self.graph = {"A": ["B"], "B": ["C"], "C": []}

    def test_depth_zero(self):
        """При глубине ноль оставить корень."""
        self.assertEqual(
            bfs(self.graph, "A", max_depth=0),
            {"A": []},
        )

    def test_depth_one(self):
        """Ограничить обход первым уровнем."""
        self.assertEqual(
            bfs(self.graph, "A", max_depth=1),
            {"A": ["B"], "B": []},
        )

    def test_depth_two(self):
        """Включить второй уровень."""
        self.assertEqual(
            bfs(self.graph, "A", max_depth=2),
            self.graph,
        )

    def test_cycle_and_filter(self):
        """Сохранить обработку циклов и фильтра."""
        graph = {"A": ["B"], "B": ["A"]}
        self.assertEqual(
            bfs(graph, "A", max_depth=1),
            {"A": ["B"], "B": []},
        )
        self.assertEqual(
            bfs(graph, "A", "B", max_depth=2),
            {"A": []},
        )

    def test_negative_depth(self):
        """Отклонить отрицательную глубину."""
        with self.assertRaises(ValueError):
            bfs(self.graph, "A", max_depth=-1)


if __name__ == "__main__":
    unittest.main()
