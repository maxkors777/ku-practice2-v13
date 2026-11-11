"""Проверить версии и спецификаторы, необходимые для графа Python."""

import unittest

from src.versions import choose_version, parse_version, satisfies


class VersionTests(unittest.TestCase):
    """Числа, prerelease, post/dev, epoch, local и диапазоны."""

    def test_order(self):
        """Проверить порядок dev, alpha, beta, rc, final и post."""
        versions = ["1.0.dev1", "1.0a1", "1.0b1", "1.0rc1", "1.0",
                    "1.0.post1", "1.1", "1.10", "2!1.0"]
        self.assertEqual(sorted(versions, key=lambda v: parse_version(v).key()),
                         versions)

    def test_release_zeros(self):
        """Не различать незначимые нули релиза."""
        self.assertEqual(
            parse_version("1.0").key(), parse_version("1.0.0").key()
        )

    def test_ranges(self):
        """Проверить AND, исключения, wildcard и совместимый релиз."""
        cases = [("1.5", ">=1,<2", True), ("2", ">=1,<2", False),
                 ("1.5", "!=1.5", False), ("1.5.2", "==1.5.*", True),
                 ("1.6", "==1.5.*", False), ("1.9", "~=1.4", True),
                 ("2", "~=1.4", False), ("1.5", "~=1.4.5", False),
                 ("1.4.9", "~=1.4.5", True)]
        for version, specifier, expected in cases:
            with self.subTest(version=version, specifier=specifier):
                self.assertEqual(satisfies(version, specifier), expected)

    def test_local(self):
        """Локальная часть учитывается при явном сравнении локальной версии."""
        self.assertTrue(satisfies("1.0+linux", "==1.0"))
        self.assertFalse(satisfies("1.0+linux", "==1.0+windows"))

    def test_selection(self):
        """Выбирать максимальный совместимый финальный релиз."""
        self.assertEqual(choose_version(["1.2", "1.10", "2.0rc1"], ">=1"),
                         "1.10")
        self.assertEqual(choose_version(["1", "2.0rc1"], ">=2.0rc1"), "2.0rc1")

    def test_failure(self):
        """Сообщать об отсутствии решения и неподдерживаемой записи."""
        for versions, specifier in [(["1"], ">2"), (["1"], "^1")]:
            with self.assertRaises(ValueError):
                choose_version(versions, specifier)
