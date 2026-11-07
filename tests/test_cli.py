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
        """Проверить успешный запуск и все пять настроек."""
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
            args = [
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
            args = arguments([
                "--package", "A",
                "--repository", str(path),
                "--test",
            ])
            self.assertTrue(args.test)
            self.assertEqual(args.package, "A")


if __name__ == "__main__":
    unittest.main()
