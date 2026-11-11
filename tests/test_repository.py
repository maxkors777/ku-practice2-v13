"""Офлайн-проверки stage 2 для Python/pip и заданной версии."""

from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from src import repository

ADDRESS = "https://pypi.org/pypi"


def document(dependencies=None, package="demo", version="1.0.0"):
    """Создать явно тестовый ответ JSON API."""
    return {"info": {
        "name": package, "version": version, "requires_dist": dependencies,
    }}


class PyPIRepositoryTests(unittest.TestCase):
    """Проверить URL, JSON, конкретную версию и ошибки HTTP."""

    def test_versioned_url(self):
        """В URL обязательно включена версия и нормализованное имя."""
        self.assertEqual(
            repository.metadata_url(ADDRESS, "Demo_Name", "1.2.3"),
            ADDRESS + "/demo-name/1.2.3/json",
        )

    def test_host_root_and_custom_path(self):
        """Поддержать корень PyPI и собственный корень JSON API."""
        self.assertEqual(
            repository.metadata_url("https://pypi.org/", "demo", "1.0"),
            ADDRESS + "/demo/1.0/json",
        )
        self.assertEqual(
            repository.metadata_url("https://mirror.test/api/", "demo", "1"),
            "https://mirror.test/api/demo/1/json",
        )

    def test_local_version(self):
        """Закодировать плюс локальной версии в URL."""
        self.assertTrue(
            repository.metadata_url(ADDRESS, "demo", "1.0+local").endswith(
                "/1.0%2Blocal/json"
            )
        )

    def test_bad_address(self):
        """Отклонить неправильные и несовместимые адреса."""
        addresses = [
            "bad", "ftp://pypi.org", "https://pypi.org/simple/",
            "https://pypi.org/pypi?q=1", "https://u:p@pypi.org",
            "https://pypi.org:bad", "https://pypi.org/a b",
        ]
        for address in addresses:
            with self.subTest(address=address), self.assertRaises(ValueError):
                repository.metadata_url(address, "demo", "1.0")

    def test_bad_identity(self):
        """Отклонить неправильную запись имени или версии."""
        for package, version in [("a b", "1"), ("a", ""), ("a", "a/b")]:
            with self.subTest(package=package, version=version):
                with self.assertRaises(ValueError):
                    repository.metadata_url(ADDRESS, package, version)

    def test_response_identity(self):
        """Не подменять запрошенный релиз другим пакетом или версией."""
        responses = [
            [], {}, {"info": []},
            document(package="other"), document(version="2.0.0"),
        ]
        for response in responses:
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    repository.validate_metadata(response, "demo", "1.0.0")

    def test_requirements_are_preserved(self):
        """Сохранить версии, extras и условия без транзитивного обхода."""
        dependencies = [
            "base>=2", 'compat; python_version < "3.10"',
            'optional[fast]>=1; extra == "speed"',
        ]
        info = repository.validate_metadata(
            document(dependencies), "demo", "1.0.0"
        )
        self.assertEqual(repository.read_dependencies(info), dependencies)

    def test_no_requirements(self):
        """Принять пустой список и null как отсутствие объявлений."""
        for dependencies in (None, []):
            self.assertEqual(
                repository.read_dependencies({"requires_dist": dependencies}),
                [],
            )

    def test_missing_requirement_field(self):
        """Не выдавать отсутствующие метаданные за пустой список."""
        with self.assertRaises(ValueError):
            repository.read_dependencies({})

    def test_bad_requirement_field(self):
        """Отклонить неправильный тип и многострочные требования."""
        for value in ("base", [1], [""], ["base\nother"]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                repository.read_dependencies({"requires_dist": value})

    def test_http_request(self):
        """Получить ответ одним HTTP-запросом конкретного релиза."""
        payload = json.dumps(document(["base>=2"])).encode()
        with patch.object(repository, "urlopen") as mocked:
            mocked.return_value.__enter__.return_value = BytesIO(payload)
            result = repository.direct_dependencies(ADDRESS, "demo", "1.0.0")
        self.assertEqual(result, ["base>=2"])
        self.assertEqual(mocked.call_count, 1)
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, ADDRESS + "/demo/1.0.0/json")
        self.assertEqual(mocked.call_args.kwargs["timeout"], 30)

    def test_missing_release(self):
        """Объяснить отсутствие пакета или версии по HTTP 404."""
        error = HTTPError(ADDRESS, 404, "not found", None, None)
        with patch.object(repository, "urlopen", side_effect=error):
            with self.assertRaisesRegex(ValueError, "не найдены"):
                repository.direct_dependencies(ADDRESS, "demo", "1.0.0")

    def test_network_failure(self):
        """Передать сетевую ошибку в обработчик командной строки."""
        with patch.object(repository, "urlopen", side_effect=URLError("down")):
            with self.assertRaises(OSError):
                repository.direct_dependencies(ADDRESS, "demo", "1.0.0")

    def test_invalid_json(self):
        """Отклонить ответ, не являющийся JSON."""
        with patch.object(repository, "urlopen") as mocked:
            mocked.return_value.__enter__.return_value = BytesIO(b"not JSON")
            with self.assertRaises(ValueError):
                repository.direct_dependencies(ADDRESS, "demo", "1.0.0")


if __name__ == "__main__":
    unittest.main()
