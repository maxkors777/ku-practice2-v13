"""Проверки PlantUML и сохранения SVG."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from src.main import main
from src.render import render_svg, to_plantuml


SVG = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'


def prepare_files(directory):
    """Подготовить пути изображения и фиктивного JAR."""
    output = Path(directory) / "graph.svg"
    jar = Path(directory) / "plantuml.jar"
    jar.touch()
    return output, jar


def program_arguments(directory):
    """Создать тестовый граф и параметры визуализации."""
    path = Path(directory) / "graph.json"
    path.write_text('{"A": ["B"], "B": []}', encoding="utf-8")
    return [
        "--package", "A",
        "--repository", str(path),
        "--test",
        "--visualize",
        "--output", str(Path(directory) / "graph.svg"),
    ]


class RenderTests(unittest.TestCase):
    """Проверки формирования диаграммы и запуска отрисовки."""

    def test_source(self):
        """Создать компоненты, стрелку и изолированную вершину."""
        source = to_plantuml({"A": ["B"], "B": [], "C": []})
        self.assertTrue(source.startswith("@startuml\n"))
        self.assertTrue(source.endswith("@enduml\n"))
        self.assertIn("!pragma layout smetana", source)
        self.assertIn('component "A" as n0', source)
        self.assertIn('component "C" as n2', source)
        self.assertIn("n0 --> n1", source)

    def test_cycle_source(self):
        """Сохранить циклические связи и петлю."""
        source = to_plantuml({"A": ["A", "B"], "B": ["A"]})
        self.assertIn("n0 --> n0", source)
        self.assertIn("n0 --> n1", source)
        self.assertIn("n1 --> n0", source)

    def test_escaped_labels(self):
        """Экранировать кавычки и обратный слеш в подписях."""
        source = to_plantuml({'a"b\\c': []})
        self.assertIn('component "a\\"b\\\\c" as n0', source)

    def test_render_success(self):
        """Записать PUML и SVG после успешного ответа."""
        with tempfile.TemporaryDirectory() as directory:
            output, jar = prepare_files(directory)
            response = subprocess.CompletedProcess([], 0, SVG, b"")
            with patch(
                "src.render.subprocess.run", return_value=response
            ) as run:
                result = render_svg({"A": []}, output, jar)
            self.assertEqual(result, output)
            self.assertEqual(output.read_bytes(), SVG)
            self.assertEqual(
                output.with_suffix(".puml").read_text(encoding="utf-8"),
                to_plantuml({"A": []}),
            )
            self.assertIn("-tsvg", run.call_args.args[0])
            self.assertIn("-pipe", run.call_args.args[0])

    def test_missing_jar(self):
        """Сообщить об отсутствии PlantUML до запуска Java."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "graph.svg"
            jar = Path(directory) / "missing.jar"
            with patch("src.render.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "Не найден"):
                    render_svg({"A": []}, output, jar)
                run.assert_not_called()

    def test_invalid_responses(self):
        """Отклонить ошибку процесса, некорректный XML и не-SVG."""
        responses = [
            subprocess.CompletedProcess([], 1, b"", b"failed"),
            subprocess.CompletedProcess([], 0, b"not XML", b""),
            subprocess.CompletedProcess([], 0, b"<html/>", b""),
        ]
        for response in responses:
            with self.subTest(response=response):
                with tempfile.TemporaryDirectory() as directory:
                    output, jar = prepare_files(directory)
                    with patch(
                        "src.render.subprocess.run",
                        return_value=response,
                    ):
                        with self.assertRaises(ValueError):
                            render_svg({"A": []}, output, jar)
                    self.assertFalse(output.exists())

    def test_timeout(self):
        """Передать ошибку превышения времени ожидания."""
        with tempfile.TemporaryDirectory() as directory:
            output, jar = prepare_files(directory)
            with patch(
                "src.render.subprocess.run",
                side_effect=subprocess.TimeoutExpired("java", 60),
            ):
                with self.assertRaises(subprocess.TimeoutExpired):
                    render_svg({"A": []}, output, jar)

    def test_program_visualization(self):
        """Передать построенный граф функции отрисовки."""
        with tempfile.TemporaryDirectory() as directory:
            args = program_arguments(directory)
            output = Path(directory) / "graph.svg"
            captured = io.StringIO()
            with patch(
                "src.main.render_svg", return_value=output
            ) as render:
                with redirect_stdout(captured):
                    code = main(args)
            self.assertEqual(code, 0)
            render.assert_called_once_with(
                {"A": ["B"], "B": []},
                str(output),
                "tools/plantuml.jar",
            )
            self.assertIn("Создано изображение:", captured.getvalue())

    def test_program_render_error(self):
        """Обработать таймаут отрисовки с кодом 1."""
        with tempfile.TemporaryDirectory() as directory:
            args = program_arguments(directory)
            errors = io.StringIO()
            with patch(
                "src.main.render_svg",
                side_effect=subprocess.TimeoutExpired("java", 60),
            ):
                with redirect_stdout(io.StringIO()):
                    with redirect_stderr(errors):
                        code = main(args)
            self.assertEqual(code, 1)
            self.assertIn("Ошибка:", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
