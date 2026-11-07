"""Формирование PlantUML и сохранение изображения SVG."""

from pathlib import Path
import subprocess
import xml.etree.ElementTree as element_tree


RENDER_TIMEOUT = 60


def to_plantuml(graph):
    """Преобразовать граф зависимостей в текст PlantUML."""
    names = sorted(graph)
    aliases = {
        name: f"n{index}"
        for index, name in enumerate(names)
    }
    lines = [
        "@startuml",
        "!pragma layout smetana",
        "left to right direction",
        "skinparam componentStyle rectangle",
    ]
    for name in names:
        safe = name.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'component "{safe}" as {aliases[name]}')
    for name in names:
        for dependency in sorted(graph[name]):
            lines.append(
                f"{aliases[name]} --> {aliases[dependency]}"
            )
    return "\n".join(lines + ["@enduml", ""])


def render_svg(graph, output, jar="tools/plantuml.jar"):
    """Запустить PlantUML и сохранить описание и изображение."""
    output = Path(output)
    jar = Path(jar)
    if not jar.is_file():
        raise ValueError(f"Не найден PlantUML: {jar}")
    source = to_plantuml(graph)
    output.with_suffix(".puml").write_text(
        source, encoding="utf-8"
    )
    command = [
        "java", "-Djava.awt.headless=true",
        "-jar", str(jar), "-charset", "UTF-8",
        "-tsvg", "-pipe",
    ]
    process = subprocess.run(
        command, input=source.encode("utf-8"),
        capture_output=True, timeout=RENDER_TIMEOUT,
    )
    if process.returncode:
        message = process.stderr.decode("utf-8", errors="replace")
        raise ValueError(f"Ошибка PlantUML: {message}")
    try:
        document = element_tree.fromstring(process.stdout)
    except element_tree.ParseError as error:
        raise ValueError("PlantUML не вернул корректный SVG") from error
    if document.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("Ответ PlantUML не является изображением SVG")
    output.write_bytes(process.stdout)
    return output
