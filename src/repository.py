"""Загрузка и чтение индекса пакетов Alpine Linux."""

import gzip
import io
import re
import tarfile
from urllib.request import urlopen


NETWORK_TIMEOUT = 30


def parse_index(text):
    """Прочитать сведения о пакетах из текста APKINDEX."""
    packages = {}
    for block in re.split(r"\n\s*\n", text.strip()):
        fields = {}
        for line in block.splitlines():
            if ":" in line:
                key, value = line.split(":", maxsplit=1)
                fields[key] = value
        if "P" not in fields:
            continue
        name = fields["P"]
        if name in packages:
            raise ValueError(f"В индексе несколько версий пакета {name}")
        packages[name] = {
            "version": fields.get("V", ""),
            "depends": fields.get("D", "").split(),
            "provides": fields.get("p", "").split(),
        }
    if not packages:
        raise ValueError("В APKINDEX нет записей пакетов")
    return packages


def unpack_index(data):
    """Прочитать APKINDEX из архива в памяти."""
    raw = gzip.decompress(data)
    with tarfile.open(
        fileobj=io.BytesIO(raw),
        mode="r:",
        ignore_zeros=True,
    ) as archive:
        for member in archive:
            if member.name == "APKINDEX" and member.isfile():
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError("Не удалось прочитать APKINDEX")
                text = stream.read().decode("utf-8")
                return parse_index(text)
    raise ValueError("В архиве отсутствует APKINDEX")


def load_repository(address):
    """Скачать индекс по URL файла или каталога репозитория."""
    url = address.rstrip("/")
    if not url.endswith("/APKINDEX.tar.gz"):
        url += "/APKINDEX.tar.gz"
    with urlopen(url, timeout=NETWORK_TIMEOUT) as response:
        data = response.read()
    return unpack_index(data)


def direct_dependencies(packages, name):
    """Вернуть прямые зависимости указанного пакета."""
    if name not in packages:
        raise ValueError(f"Пакет {name} не найден в репозитории")
    return packages[name]["depends"]
