"""Проверки принятого CLI и поведения второго этапа."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from main import arguments, main

REPOSITORY = "https://pypi.org/pypi"


class CliTests(unittest.TestCase):
    """Сохранить проверки параметров и проверить новый вывод stage 2."""

    def base_args(self):
        """Вернуть правильные обязательные параметры."""
        return [
            "--package", "requests", "--repository", REPOSITORY,
            "--version", "2.32.3", "--max-depth", "2",
        ]

    def assert_rejected(self, args, message):
        """Проверить код ошибки и пояснение пользователю."""
        output = io.StringIO()
        with redirect_stderr(output):
            with self.assertRaises(SystemExit) as caught:
                arguments(args)
        self.assertEqual(caught.exception.code, 2)
        self.assertIn(message, output.getvalue())

    def test_valid_parameters(self):
        """Прочитать все семь настроек принятого первого этапа."""
        args = arguments(self.base_args())
        self.assertEqual(args.package, "requests")
        self.assertEqual(args.repository, REPOSITORY)
        self.assertEqual(args.version, "2.32.3")
        self.assertEqual(args.max_depth, 2)
        self.assertEqual(args.output, "graph.svg")
        self.assertEqual(args.filter, "")
        self.assertFalse(args.test)

    def test_invalid_package(self):
        """Отклонить имя с пробелом."""
        self.assert_rejected(
            self.base_args() + ["--package", "bad name"], "--package:"
        )

    def test_invalid_repository(self):
        """Отклонить неполный HTTP(S) URL."""
        self.assert_rejected(
            self.base_args() + ["--repository", "not-a-url"], "--repository:"
        )

    def test_invalid_output(self):
        """Для изображения требуется расширение SVG."""
        self.assert_rejected(
            self.base_args() + ["--output", "graph.png"], "--output:"
        )

    def test_invalid_filter(self):
        """Фильтр не должен содержать пробелы."""
        self.assert_rejected(
            self.base_args() + ["--filter", "bad filter"], "--filter:"
        )

    def test_missing_test_file(self):
        """Проверить существование тестового файла."""
        with tempfile.TemporaryDirectory() as directory:
            args = self.base_args() + [
                "--package", "A", "--test", "--repository",
                str(Path(directory) / "missing.json"),
            ]
            self.assert_rejected(args, "--repository: файл не найден")

    def test_valid_test_mode(self):
        """Сохранить чтение переключателя тестового режима."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.json"
            path.write_text('{"A": []}', encoding="utf-8")
            args = arguments(self.base_args() + [
                "--package", "A", "--repository", str(path), "--test",
            ])
            self.assertTrue(args.test)
            self.assertEqual(args.package, "A")

    def test_zero_depth(self):
        """Принять нулевую глубину."""
        args = arguments(self.base_args() + ["--max-depth", "0"])
        self.assertEqual(args.max_depth, 0)

    def test_negative_depth(self):
        """Отклонить отрицательную глубину."""
        self.assert_rejected(
            self.base_args() + ["--max-depth", "-1"], "--max-depth:"
        )

    def test_non_integer_depth(self):
        """Вместо глубины нельзя передавать текст."""
        self.assert_rejected(
            self.base_args() + ["--max-depth", "abc"], "--max-depth"
        )

    def test_invalid_version(self):
        """Отклонить версию с пробелом."""
        self.assert_rejected(
            self.base_args() + ["--version", "bad version"], "--version:"
        )

    def test_missing_version(self):
        """Версия остаётся обязательным параметром."""
        args = self.base_args()
        position = args.index("--version")
        del args[position:position + 2]
        self.assert_rejected(args, "--version")

    def test_missing_depth(self):
        """Глубина остаётся обязательным параметром первого этапа."""
        args = self.base_args()
        position = args.index("--max-depth")
        del args[position:position + 2]
        self.assert_rejected(args, "--max-depth")

    def test_direct_output_and_version(self):
        """Передать выбранную версию и вывести прямые требования целиком."""
        dependencies = ["base>=2", 'optional; extra == "feature"']
        with patch("src.main.direct_dependencies") as mocked:
            mocked.return_value = dependencies
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(self.base_args()), 0)
            mocked.assert_called_once_with(REPOSITORY, "requests", "2.32.3")
        self.assertEqual(output.getvalue().splitlines(), dependencies)

    def test_empty_output(self):
        """Пояснить отсутствие объявленных зависимостей."""
        with patch("src.main.direct_dependencies", return_value=[]):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(self.base_args()), 0)
        self.assertIn("нет объявленных прямых зависимостей", output.getvalue())

    def test_network_failure(self):
        """Ошибка сети должна возвращать код 1."""
        with patch("src.main.direct_dependencies", side_effect=OSError):
            with redirect_stderr(io.StringIO()) as output:
                self.assertEqual(main(self.base_args()), 1)
        self.assertIn("Ошибка:", output.getvalue())

    def test_test_execution_deferred(self):
        """Явно объяснить, что тестовые графы относятся к stage 3."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.json"
            path.write_text('{"A": []}', encoding="utf-8")
            args = self.base_args() + [
                "--package", "A", "--repository", str(path), "--test",
            ]
            with redirect_stderr(io.StringIO()) as output:
                self.assertEqual(main(args), 1)
            self.assertIn("stage 3", output.getvalue())


if __name__ == "__main__":
    unittest.main()
