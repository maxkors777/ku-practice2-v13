"""Ленивый источник транзитивных зависимостей из PyPI."""

import json
import platform
import re
from urllib.request import Request, urlopen

from .markers import marker_matches
from .repository import (
    NAME_PATTERN, NETWORK_TIMEOUT, fetch_metadata, metadata_url,
    normalize_name, read_dependencies, validate_metadata,
)
from .versions import choose_version, satisfies, split_specifier


def parse_requirement(text):
    """Выделить имя, extras, ограничение версии и маркер PEP 508."""
    declaration, separator, marker = text.partition(";")
    pattern = r"\s*(" + NAME_PATTERN + r")\s*(?:\[([^\]]+)\])?\s*(.*)"
    match = re.fullmatch(pattern, declaration)
    if not match:
        raise ValueError(f"Не разобрано требование: {text}")
    name, extras, specifier = match.groups()
    specifier = specifier.strip()
    if specifier.startswith("(") and specifier.endswith(")"):
        specifier = specifier[1:-1].strip()
    features = tuple(sorted({
        normalize_name(extra.strip()) for extra in (extras or "").split(",")
        if extra.strip()
    }))
    return normalize_name(name), specifier, features, marker


def validate_specifiers(requirement):
    """Отклонить неподдерживаемое требование до сетевых запросов."""
    for part in requirement.split(","):
        if part.strip():
            split_specifier(part)


def fetch_catalog(address, name):
    """Получить каталог релизов, не вызывая менеджер пакетов."""
    versioned = metadata_url(address, name, "0")
    url = versioned[:-len("0/json")] + "json"
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=NETWORK_TIMEOUT) as response:
        document = json.loads(response.read().decode("utf-8"))
    if not isinstance(document, dict) or not isinstance(
        document.get("releases"), dict
    ):
        raise ValueError("Репозиторий не предоставил каталог releases")
    return document["releases"]


def usable_files(files):
    """Исключить отозванные и несовместимые с текущим Python файлы."""
    if not isinstance(files, list):
        raise ValueError("Неверное описание файлов релиза")
    for file in files:
        if not isinstance(file, dict) or file.get("yanked", False):
            continue
        requirement = file.get("requires_python") or ""
        if satisfies(platform.python_version(), requirement):
            return True
    return False


class PythonRepository:
    """Кэшировать каталоги, метаданные версий и результаты разрешения."""

    def __init__(self, address, excluded=""):
        """Сохранить репозиторий и фильтр до выполнения запросов."""
        self.address, self.excluded = address, excluded
        self.catalogs, self.metadata, self.resolutions = {}, {}, {}

    def info(self, node):
        """Проверить и кэшировать конкретный релиз."""
        name, version, extras = node
        key = name, version
        if key not in self.metadata:
            document = fetch_metadata(self.address, name, version)
            info = validate_metadata(document, name, version)
            requirement = info.get("requires_python") or ""
            if not satisfies(platform.python_version(), requirement):
                message = f"{name} {version}: несовместимая версия Python"
                raise ValueError(message)
            self.metadata[key] = info
        return self.metadata[key]

    def resolve(self, name, requirement):
        """Выбрать максимальную совместимую версию из каталога."""
        validate_specifiers(requirement)
        key = name, requirement
        if key not in self.resolutions:
            if name not in self.catalogs:
                releases = fetch_catalog(self.address, name)
                self.catalogs[name] = [
                    version for version, files in releases.items()
                    if usable_files(files)
                ]
            self.resolutions[key] = choose_version(
                self.catalogs[name], requirement
            )
        return self.resolutions[key]

    def dependencies(self, node):
        """Разрешить только активные и не исключённые прямые требования."""
        info = self.info(node)
        result = set()
        for text in read_dependencies(info):
            name, requirement, extras, marker = parse_requirement(text)
            if self.excluded and self.excluded in name:
                continue
            if not marker_matches(marker, node[2]):
                continue
            version = self.resolve(name, requirement)
            result.add((name, version, extras))
        return result
