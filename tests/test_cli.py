"""Автоматические проверки первого этапа."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

from main import arguments, main


REPOSITORY = (
    "https://dl-cdn.alpinelinux.org/alpine/"
    "v3.22/main/x86_64/APKINDEX.tar.gz"
)


class CliTests(unittest.TestCase):
    """Проверки настроек и сообщений об ошибках."""

    def base_args(self):
        """Вернуть правильные обязательные параметры."""
        return [
            "--package", "zlib",
            "--repository", REPOSITORY,
            "--version", "1.2.3-r0",
            "--max-depth", "2",
        ]
    
    def assert_rejected(self, args, message):
        """Проверить код ошибки и пояснение пользователю."""
        output = io.StringIO()
        with redirect_stderr(output):
            with self.assertRaises(SystemExit) as caught:
                arguments(args)
        self.assertEqual(caught.exception.code, 2)
        self.assertIn(message, output.getvalue())

    def test_normal_output(self):
        """Проверить успешный запуск и все семь настроек."""
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(self.base_args())
        self.assertEqual(code, 0)
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "package=zlib",
                f"repository={REPOSITORY}",
                "test=False",
                "output=graph.svg",
                "filter=",
                "version=1.2.3-r0",
                "max_depth=2",
            ],
        )

    def test_invalid_package(self):
        """Имя пакета с пробелом должно отклоняться."""
        args = self.base_args() + ["--package", "bad name"]
        self.assert_rejected(args, "--package: недопустимое имя")

    def test_invalid_repository(self):
        """В сетевом режиме требуется HTTP(S) URL."""
        args = self.base_args() + ["--repository", "not-a-url"]
        self.assert_rejected(args, "--repository: нужен полный")

    def test_invalid_output(self):
        """Для изображения требуется расширение SVG."""
        args = self.base_args() + ["--output", "graph.png"]
        self.assert_rejected(args, "--output: нужен путь")

    def test_invalid_filter(self):
        """Фильтр с пробелом должен отклоняться."""
        args = self.base_args() + ["--filter", "bad filter"]
        self.assert_rejected(args, "--filter: нужны символы")

    def test_missing_test_file(self):
        """В тестовом режиме файл должен существовать."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            args = self.base_args() + [
                "--package", "A",
                "--repository", str(path),
                "--test",
            ]
            self.assert_rejected(args, "--repository: файл не найден")

    def test_valid_test_mode(self):
        """Переключатель --test должен включать тестовый режим."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.json"
            path.write_text('{"A": []}', encoding="utf-8")
            args = arguments(self.base_args() + [
                "--package", "A",
                "--repository", str(path),
                "--test",
            ])
            self.assertTrue(args.test)
            self.assertEqual(args.package, "A")

    def test_zero_depth(self):
        """Глубина ноль должна приниматься."""
        args = arguments(self.base_args() + ["--max-depth", "0"])
        self.assertEqual(args.max_depth, 0)

    def test_negative_depth(self):
        """Отрицательная глубина должна отклоняться."""
        args = self.base_args() + ["--max-depth", "-1"]
        self.assert_rejected(args, "--max-depth: глубина")

    def test_non_integer_depth(self):
        """Вместо глубины нельзя передавать текст."""
        args = self.base_args() + ["--max-depth", "abc"]
        self.assert_rejected(args, "--max-depth")

    def test_invalid_version(self):
        """Версия с пробелом должна отклоняться."""
        args = self.base_args() + ["--version", "bad version"]
        self.assert_rejected(args, "--version: версия")

    def test_missing_version(self):
        """Версия является обязательным параметром."""
        args = self.base_args()
        position = args.index("--version")
        del args[position:position + 2]
        self.assert_rejected(args, "--version")

    def test_missing_depth(self):
        """Глубина является обязательным параметром."""
        args = self.base_args()
        position = args.index("--max-depth")
        del args[position:position + 2]
        self.assert_rejected(args, "--max-depth")


if __name__ == "__main__":
    unittest.main()