"""Разбор версий и распространённых спецификаторов PEP 440 без библиотек."""

from dataclasses import dataclass
import re

PATTERN = re.compile(
    r"^v?(?:(?P<epoch>\d+)!)?(?P<release>\d+(?:\.\d+)*)"
    r"(?:[-_.]?(?P<pre>a|b|rc|alpha|beta|preview|pre|c)"
    r"[-_.]?(?P<pre_n>\d+)?)?"
    r"(?:(?:-(?P<post_n1>\d+))|"
    r"(?:[-_.]?(?P<post>post|rev|r)[-_.]?(?P<post_n2>\d+)?))?"
    r"(?:[-_.]?(?P<dev>dev)[-_.]?(?P<dev_n>\d+)?)?"
    r"(?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?$", re.I,
)


@dataclass(frozen=True)
class Version:
    """Компоненты версии и единый ключ упорядочивания."""

    epoch: int
    release: tuple
    pre: tuple
    post: int
    dev: tuple
    local: tuple
    unstable: bool

    def key(self, local=True):
        """Вернуть ключ с локальной частью либо без неё."""
        return (
            self.epoch, self.release, self.pre, self.post, self.dev,
            self.local if local else (),
        )


def release_tuple(text):
    """Убрать незначимые нули справа при сравнении релизов."""
    parts = [int(part) for part in text.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def pre_key(fields):
    """Упорядочить dev-only, alpha, beta, rc и финальный релиз."""
    name = fields["pre"]
    if name:
        stage = {"a": 0, "alpha": 0, "b": 1, "beta": 1}.get(name, 2)
        return stage, int(fields["pre_n"] or 0)
    if fields["dev"] and not fields["post"] and not fields["post_n1"]:
        return -1, 0
    return 3, 0


def post_number(fields):
    """Вернуть номер post-релиза либо -1."""
    if fields["post"] or fields["post_n1"]:
        return int(fields["post_n1"] or fields["post_n2"] or 0)
    return -1


def dev_key(fields):
    """Разместить dev перед соответствующим релизом."""
    if fields["dev"]:
        return 0, int(fields["dev_n"] or 0)
    return 1, 0


def local_key(text):
    """Числовые компоненты local выше буквенных."""
    if not text:
        return ()
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part)
        for part in re.split(r"[-_.]", text)
    )


def parse_version(text):
    """Прочитать публичную, предварительную и локальную версии."""
    match = PATTERN.fullmatch(text.strip().lower())
    if not match:
        raise ValueError(f"Неподдерживаемая версия: {text}")
    fields = match.groupdict()
    return Version(
        int(fields["epoch"] or 0), release_tuple(fields["release"]),
        pre_key(fields), post_number(fields), dev_key(fields),
        local_key(fields["local"]), bool(fields["pre"] or fields["dev"]),
    )


def split_specifier(text):
    """Разделить оператор и его значение."""
    match = re.fullmatch(r"\s*(===|~=|==|!=|<=|>=|<|>)\s*(\S+)\s*", text)
    if not match:
        raise ValueError(f"Неподдерживаемое требование версии: {text}")
    return match.groups()


def equal_version(candidate, target):
    """Сравнить релизы с учётом правил локальной части и wildcard."""
    if target.endswith(".*"):
        prefix = target[:-2]
        wanted = parse_version(prefix)
        if wanted.unstable or wanted.post >= 0 or wanted.local:
            raise ValueError("Wildcard допустим только после номера релиза")
        precision = len(prefix.split("!")[-1].split("."))
        parts = candidate.release + (0,) * precision
        expected = wanted.release + (0,) * precision
        return candidate.epoch == wanted.epoch and (
            parts[:precision] == expected[:precision]
        )
    wanted = parse_version(target)
    return candidate.key(bool(wanted.local)) == wanted.key(bool(wanted.local))


def compatible(candidate, target):
    """Проверить совместимый диапазон ~= с заданной точностью."""
    wanted = parse_version(target)
    match = PATTERN.fullmatch(target.strip().lower())
    parts = [int(part) for part in match["release"].split(".")]
    if len(parts) < 2:
        raise ValueError("Оператор ~= требует минимум две части версии")
    upper = parts[:-1]
    upper[-1] += 1
    limit = Version(wanted.epoch, tuple(upper), (3, 0), -1, (1, 0), (), False)
    return wanted.key(False) <= candidate.key(False) < limit.key(False)


def ordered_comparison(candidate, operator, target):
    """Проверить неравенства и особые границы pre/post-релизов."""
    wanted = parse_version(target)
    same_release = (candidate.epoch, candidate.release) == (
        wanted.epoch, wanted.release
    )
    if operator == "<" and same_release and not wanted.unstable:
        if candidate.unstable:
            return False
    if operator == ">" and same_release and wanted.post < 0:
        if candidate.post >= 0 or candidate.local:
            return False
    left, right = candidate.key(False), wanted.key(False)
    comparisons = {"<": left < right, "<=": left <= right,
                   ">": left > right, ">=": left >= right}
    return comparisons[operator]


def matches_specifier(version, operator, target):
    """Проверить один спецификатор."""
    if operator == "===":
        return version.lower() == target.lower()
    candidate = parse_version(version)
    if operator in ("==", "!="):
        equal = equal_version(candidate, target)
        return equal if operator == "==" else not equal
    if operator == "~=":
        return compatible(candidate, target)
    return ordered_comparison(candidate, operator, target)


def satisfies(version, requirement):
    """Проверить все части AND; неподдерживаемые записи не игнорируются."""
    parts = [part.strip() for part in requirement.split(",") if part.strip()]
    return all(matches_specifier(version, *split_specifier(p)) for p in parts)


def allows_prereleases(requirement):
    """Проверить явное упоминание предварительной версии."""
    specs = [split_specifier(p) for p in requirement.split(",") if p.strip()]
    for operator, target in specs:
        if target.endswith(".*") or operator == "!=":
            continue
        if parse_version(target).unstable:
            return True
    return False


def eligible_versions(versions, allow_pre):
    """Отбросить некорректные записи и не запрошенные prerelease."""
    for version in versions:
        try:
            parsed = parse_version(version)
        except ValueError:
            continue
        if parsed.unstable and not allow_pre:
            continue
        yield version


def choose_version(versions, requirement):
    """Выбрать максимальный релиз; prerelease только при явном запросе."""
    allow_pre = allows_prereleases(requirement)
    candidates = [
        version for version in eligible_versions(versions, allow_pre)
        if satisfies(version, requirement)
    ]
    if not candidates:
        raise ValueError(f"Нет подходящей версии для {requirement or '*'}")
    return max(candidates, key=lambda value: parse_version(value).key())
