"""Проверки получения прямых зависимостей Alpine APK."""

from contextlib import redirect_stderr, redirect_stdout
import io
import tarfile
import unittest
from unittest.mock import patch

from src.main import main
from src.repository import (
    direct_dependencies,
    load_repository,
    parse_index,
    unpack_index,
)


INDEX = (
    "P:app\n"
    "V:1.0-r0\n"
    "D:lib>=1.0\n"
    "p:cmd:app=1.0\n"
    "\n"
    "P:lib\n"
    "V:1.0-r0\n"
)


def make_archive(text):
    """Создать маленький архив APKINDEX.tar.gz в памяти."""
    buffer = io.BytesIO()
    data = text.encode("utf-8")
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        member = tarfile.TarInfo("APKINDEX")
        member.size = len(data)
        archive.addfile(member, io.BytesIO(data))
    return buffer.getvalue()


class RepositoryTests(unittest.TestCase):
    """Проверки индекса и запуска программы второго этапа."""

    def test_parse_and_dependencies(self):
        """Прочитать поля и сохранить ограничение версии."""
        packages = parse_index(INDEX)
        self.assertEqual(packages["app"]["version"], "1.0-r0")
        self.assertEqual(
            packages["app"]["provides"], ["cmd:app=1.0"]
        )
        self.assertEqual(
            direct_dependencies(packages, "app"), ["lib>=1.0"]
        )
        self.assertEqual(direct_dependencies(packages, "lib"), [])

    def test_missing_package(self):
        """Сообщить об отсутствии запрошенного пакета."""
        packages = parse_index(INDEX)
        with self.assertRaisesRegex(ValueError, "не найден"):
            direct_dependencies(packages, "missing")

    def test_invalid_index(self):
        """Отклонить пустой индекс и повтор имени пакета."""
        examples = ["", "P:app\n\nP:app\n"]
        for text in examples:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_index(text)

    def test_unpack_archive(self):
        """Прочитать настоящий архив, созданный в памяти."""
        packages = unpack_index(make_archive(INDEX))
        self.assertEqual(
            direct_dependencies(packages, "app"), ["lib>=1.0"]
        )

    def test_download(self):
        """Проверить адрес загрузки и чтение ответа сервера."""
        response = io.BytesIO(make_archive(INDEX))
        with patch(
            "src.repository.urlopen", return_value=response
        ) as opened:
            packages = load_repository("https://example.com/main")
        opened.assert_called_once_with(
            "https://example.com/main/APKINDEX.tar.gz",
            timeout=30,
        )
        self.assertIn("app", packages)

    def test_program_output(self):
        """Программа должна выводить прямые зависимости."""
        output = io.StringIO()
        with patch(
            "src.main.load_repository",
            return_value=parse_index(INDEX),
        ):
            with redirect_stdout(output):
                code = main([
                    "--package", "app",
                    "--repository", "https://example.com/main",
                ])
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue(), "lib>=1.0\n")

    def test_network_error(self):
        """Ошибка сети должна давать сообщение и код 1."""
        output = io.StringIO()
        with patch(
            "src.main.load_repository",
            side_effect=OSError("Нет соединения"),
        ):
            with redirect_stderr(output):
                code = main([
                    "--package", "app",
                    "--repository", "https://example.com/main",
                ])
        self.assertEqual(code, 1)
        self.assertIn("Нет соединения", output.getvalue())


if __name__ == "__main__":
    unittest.main()
