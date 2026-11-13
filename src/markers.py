"""Безопасное вычисление маркеров окружения без eval и сторонних библиотек."""

import ast
import os
import platform
import re
import sys

from .versions import matches_specifier

TOKEN = re.compile(
    r'''\s*("[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*'|'''
    r"===|~=|==|!=|<=|>=|<|>|\(|\)|[A-Za-z_][A-Za-z_0-9]*)"
)


def environment(extra=""):
    """Сформировать стандартные переменные текущего окружения."""
    return {
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "python_full_version": platform.python_version(),
        "os_name": os.name, "sys_platform": sys.platform,
        "platform_machine": platform.machine(),
        "platform_python_implementation": platform.python_implementation(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "implementation_name": sys.implementation.name,
        "implementation_version": platform.python_version(), "extra": extra,
    }


def tokenize(text):
    """Разбить маркер, отклоняя неизвестные символы."""
    tokens, position = [], 0
    text = text.strip()
    while position < len(text):
        match = TOKEN.match(text, position)
        if not match:
            raise ValueError(f"Неподдерживаемый маркер: {text}")
        tokens.append(match[1])
        position = match.end()
    return tokens


def compare_values(left, operator, right):
    """Применить версионное сравнение или сравнение строк."""
    allowed = ("in", "not in", "==", "!=", "<", "<=", ">", ">=", "~=", "===")
    if operator not in allowed:
        raise ValueError(f"Неподдерживаемый оператор: {operator}")
    if operator == "in":
        return left in right
    if operator == "not in":
        return left not in right
    try:
        return matches_specifier(left, operator, right)
    except ValueError:
        comparisons = {
            "==": left == right, "!=": left != right,
            "<": left < right, "<=": left <= right,
            ">": left > right, ">=": left >= right,
        }
        if operator not in comparisons:
            raise ValueError(f"Неподдерживаемое сравнение: {operator}")
        return comparisons[operator]


class MarkerParser:
    """Рекурсивный разбор выражения маркера; это не обход графа."""

    def __init__(self, text, values):
        """Сохранить токены и переменные окружения."""
        self.tokens = tokenize(text)
        self.position = 0
        self.values = values

    def peek(self):
        """Посмотреть следующий токен."""
        if self.position == len(self.tokens):
            return None
        return self.tokens[self.position]

    def take(self):
        """Прочитать обязательный токен."""
        token = self.peek()
        if token is None:
            raise ValueError("Незавершённый маркер окружения")
        self.position += 1
        return token

    def value(self):
        """Получить строковую константу или известную переменную."""
        token = self.take()
        if token.startswith(('"', "'")):
            return ast.literal_eval(token)
        if token not in self.values:
            raise ValueError(f"Неизвестная переменная маркера: {token}")
        return self.values[token]

    def atom(self):
        """Обработать скобки либо одно сравнение."""
        if self.peek() == "(":
            self.take()
            result = self.expression()
            if self.take() != ")":
                raise ValueError("Не закрыта скобка маркера")
            return result
        left_token = self.peek()
        left = self.value()
        operator = self.take()
        if operator == "not":
            if self.take() != "in":
                raise ValueError("После not требуется in")
            operator = "not in"
        right_token = self.peek()
        right = self.value()
        if "extra" in (left_token, right_token):
            left = re.sub(r"[-_.]+", "-", left).lower()
            right = re.sub(r"[-_.]+", "-", right).lower()
        return compare_values(left, operator, right)

    def conjunction(self):
        """Разобрать AND с приоритетом перед OR."""
        result = self.atom()
        while self.peek() == "and":
            self.take()
            following = self.atom()
            result = result and following
        return result

    def expression(self):
        """Разобрать OR."""
        result = self.conjunction()
        while self.peek() == "or":
            self.take()
            following = self.conjunction()
            result = result or following
        return result

    def evaluate(self):
        """Проверить, что разобрано всё выражение."""
        result = self.expression()
        if self.peek() is not None:
            raise ValueError("Лишние токены маркера")
        return result


def marker_matches(text, extras=(), values=None):
    """Включить требование для текущего окружения и запрошенных extras."""
    if not text.strip():
        return True
    for extra in extras or ("",):
        current = dict(values) if values is not None else environment()
        current["extra"] = extra
        if MarkerParser(text, current).evaluate():
            return True
    return False
