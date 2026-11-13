"""Проверки ленивого Python-источника и маркеров без интернета."""

import unittest
from unittest.mock import patch

from src.markers import marker_matches
from src.python_graph import PythonRepository, parse_requirement


def metadata(name, version, dependencies):
    """Сформировать явно тестовый ответ метаданных."""
    return {"info": {"name": name, "version": version,
                     "requires_dist": dependencies}}


class PythonGraphTests(unittest.TestCase):
    """Проверить разрешение версий и раннее отсечение требований."""

    def test_requirement(self):
        """Прочитать старую форму скобок, extras и маркер."""
        text = 'Demo_Name[fast] (>=1,<2); os_name == "x"'
        self.assertEqual(parse_requirement(text),
                         ("demo-name", ">=1,<2", ("fast",), ' os_name == "x"'))

    def test_markers(self):
        """Обработать AND, OR, скобки, версии и дополнительные возможности."""
        values = {"python_version": "3.12", "sys_platform": "linux"}
        cases = [('python_version >= "3.10"', True),
                 ('python_version < "3.10"', False),
                 ('sys_platform == "win32" or python_version >= "3.12"', True),
                 ('sys_platform == "linux" and python_version != "3.11"',
                  True),
                 ('extra == "fast"', False),
                 ('sys_platform not in "win32"', True)]
        for text, expected in cases:
            self.assertEqual(marker_matches(text, values=values), expected)
        self.assertTrue(marker_matches('extra == "fast"', ("fast",)))

    def test_bad_marker(self):
        """Неверный маркер нельзя молча принять."""
        for marker in ('unknown == "x"', 'os_name ==', '__import__("os")'):
            with self.assertRaises(ValueError):
                marker_matches(marker)

    def test_filter_before_http(self):
        """Не запрашивать версии исключённой зависимости."""
        repository = PythonRepository("https://pypi.org/pypi", "skip")
        repository.metadata[("root", "1")] = {
            "requires_dist": ["skip-me>=1", 'optional; extra == "fast"'],
        }
        with patch("src.python_graph.fetch_catalog") as mocked:
            self.assertEqual(repository.dependencies(("root", "1", ())), set())
            mocked.assert_not_called()

    def test_resolution_cache(self):
        """Каталог имени и метаданные релиза загружаются один раз."""
        repository = PythonRepository("https://pypi.org/pypi")
        releases = {"1": [{"yanked": False}], "2": [{"yanked": False}]}
        target = "src.python_graph.fetch_catalog"
        with patch(target, return_value=releases) as cat:
            self.assertEqual(repository.resolve("base", ">=1"), "2")
            self.assertEqual(repository.resolve("base", "<2"), "1")
            self.assertEqual(cat.call_count, 1)
        with patch("src.python_graph.fetch_metadata") as fetch:
            fetch.return_value = metadata("base", "1", [])
            repository.info(("base", "1", ()))
            repository.info(("base", "1", ("fast",)))
            self.assertEqual(fetch.call_count, 1)

    def test_conditional_extras(self):
        """Разрешить зависимость только при запрошенной дополнительной опции."""
        repository = PythonRepository("https://pypi.org/pypi")
        repository.metadata[("root", "1")] = {
            "requires_dist": ['child>=1; extra == "fast"'],
        }
        with patch.object(repository, "resolve", return_value="2"):
            self.assertEqual(repository.dependencies(("root", "1", ())), set())
            self.assertEqual(repository.dependencies(("root", "1", ("fast",))),
                             {("child", "2", ())})

    def test_filtered_unsupported_requirement(self):
        """Не разбирать версию зависимости, исключённой фильтром."""
        repository = PythonRepository("https://pypi.org/pypi", "skip")
        repository.metadata[("root", "1")] = {
            "requires_dist": ["skip @ https://example.test/file.whl"],
        }
        self.assertEqual(repository.dependencies(("root", "1", ())), set())
