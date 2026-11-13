"""Прямые требования Python-пакета через версионный JSON API PyPI."""

import json
import re
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

NETWORK_TIMEOUT = 30
NAME_PATTERN = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"


def normalize_name(name):
    """Привести имя дистрибутива к форме сравнения PyPI."""
    return re.sub(r"[-_.]+", "-", name).lower()


def validate_address(address):
    """Проверить адрес корня JSON API совместимого репозитория."""
    parsed = urlsplit(address)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("--repository: нужен полный HTTP(S) URL")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError("--repository: лишние части URL")
    if any(char.isspace() for char in address):
        raise ValueError("--repository: URL содержит пробелы")
    parsed.port
    if parsed.path.rstrip("/").endswith("/simple"):
        message = "Нужен корень JSON API: https://pypi.org/pypi"
        raise ValueError(message)


def validate_identity_values(package, version):
    """Проверить имя и безопасную запись конкретной версии."""
    if not re.fullmatch(NAME_PATTERN, package, flags=re.ASCII):
        raise ValueError("--package: недопустимое имя Python-пакета")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]*", version):
        raise ValueError("--version: недопустимая запись версии")


def metadata_url(address, package, version):
    """Сформировать URL конкретного релиза, без обращения к latest."""
    validate_address(address)
    validate_identity_values(package, version)
    base = address.rstrip("/")
    if not urlsplit(base).path:
        base += "/pypi"
    name = quote(normalize_name(package), safe="")
    release = quote(version, safe="")
    return f"{base}/{name}/{release}/json"


def validate_metadata(document, package, version):
    """Проверить принадлежность ответа запрошенному релизу."""
    if not isinstance(document, dict):
        raise ValueError("Репозиторий вернул не JSON-объект")
    info = document.get("info")
    if not isinstance(info, dict):
        raise ValueError("В ответе отсутствует объект info")
    name = info.get("name")
    if not isinstance(name, str) or normalize_name(name) != normalize_name(
        package
    ):
        raise ValueError("Репозиторий вернул другой пакет")
    if info.get("version") != version:
        raise ValueError("Репозиторий вернул другую запись версии")
    return info


def read_dependencies(info):
    """Прочитать все объявленные требования, сохранив условия и extras."""
    if "requires_dist" not in info:
        raise ValueError("Репозиторий не предоставил поле requires_dist")
    dependencies = info["requires_dist"]
    if dependencies is None:
        return []
    if not isinstance(dependencies, list):
        raise ValueError("Поле requires_dist должно быть списком либо null")
    for requirement in dependencies:
        if not isinstance(requirement, str) or not requirement.strip():
            raise ValueError("Требования должны быть непустыми строками")
        if "\n" in requirement or "\r" in requirement:
            raise ValueError("Требование не должно содержать переносы строк")
    return list(dependencies)

HTTP_NOT_FOUND = 404

def fetch_metadata(address, package, version):
    """Получить JSON по HTTP без pip и сторонних библиотек."""
    request = Request(
        metadata_url(address, package, version),
        headers={"Accept": "application/json", "User-Agent": "ku-stage2/1.0"},
    )
    try:
        with urlopen(request, timeout=NETWORK_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code == HTTP_NOT_FOUND:
            raise ValueError("Пакет или указанная версия не найдены") from error
        raise


def direct_dependencies(address, package, version):
    """Вернуть требования строго запрошенного релиза Python-пакета."""
    document = fetch_metadata(address, package, version)
    info = validate_metadata(document, package, version)
    return read_dependencies(info)
