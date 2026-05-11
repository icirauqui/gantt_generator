from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT / "exports"
DEFAULT_DATA_FILE = ROOT / "gantt_data.json"
SAMPLES_DIR = ROOT / "samples"

WHITE = (255, 255, 255, 255)
GRID = (242, 242, 242, 255)
PURPLE = (115, 87, 115, 255)
TEXT = (38, 38, 38, 255)
HEADER_TEXT = (64, 64, 64, 255)
RED = (192, 0, 0, 255)
CURRENT_FILL = (247, 222, 185, 255)
CURRENT_EDGE = (233, 171, 81, 255)
OVERDUE = (233, 171, 81, 255)
HATCH = (85, 85, 85, 255)


@dataclass(frozen=True)
class Task:
    name: str
    plan_start: int
    plan_duration: int
    actual_start: int
    actual_duration: int

    @property
    def plan_end(self) -> int:
        return self.plan_start + self.plan_duration

    @property
    def actual_end(self) -> int:
        return self.actual_start + self.actual_duration


@dataclass(frozen=True)
class ChartData:
    current_period: int
    periods: tuple[str, ...]
    tasks: tuple[Task, ...]


@dataclass(frozen=True)
class Layout:
    width: int
    height: int
    plot_left: int
    plot_right: int
    header_line_y: int
    bottom_line_y: int
    right_line_top_y: int
    row_tops: tuple[int, ...]
    bar_height: int
    month_label_bottom_y: int
    month_number_y: int
    activity_x: int
    start_x: int
    duration_x: int
    header_y: int
    row_label_x: int
    row_text_offset_y: int
    value_text_offset_y: int
    header_font_size: int
    row_font_size: int
    value_font_size: int
    month_font_size: int
    number_font_size: int
    current_top_y: int | None = None

    @property
    def grid_top(self) -> int:
        return self.row_tops[0] + 1

    @property
    def grid_bottom(self) -> int:
        return self.row_tops[-1] + self.bar_height


PLAN_LAYOUT = Layout(
    width=2726,
    height=615,
    plot_left=476,
    plot_right=2720,
    header_line_y=202,
    bottom_line_y=610,
    right_line_top_y=166,
    row_tops=(253, 305, 356, 407, 458, 509),
    bar_height=50,
    month_label_bottom_y=164,
    month_number_y=188,
    activity_x=37,
    start_x=255,
    duration_x=403,
    header_y=153,
    row_label_x=36,
    row_text_offset_y=27,
    value_text_offset_y=27,
    header_font_size=24,
    row_font_size=18,
    value_font_size=25,
    month_font_size=23,
    number_font_size=23,
)

ACTUAL_LAYOUT = Layout(
    width=1408,
    height=308,
    plot_left=252,
    plot_right=1404,
    header_line_y=96,
    bottom_line_y=305,
    right_line_top_y=78,
    row_tops=(122, 149, 176, 202, 228, 254),
    bar_height=25,
    month_label_bottom_y=78,
    month_number_y=88,
    activity_x=23,
    start_x=134,
    duration_x=213,
    header_y=66,
    row_label_x=23,
    row_text_offset_y=18,
    value_text_offset_y=17,
    header_font_size=11,
    row_font_size=12,
    value_font_size=12,
    month_font_size=8,
    number_font_size=11,
    current_top_y=78,
)


def layout_for_task_count(template: Layout, task_count: int) -> Layout:
    if task_count < 1:
        raise ValueError("At least one stage is required.")
    if task_count == len(template.row_tops):
        return template

    if len(template.row_tops) > 1:
        row_step = round((template.row_tops[-1] - template.row_tops[0]) / (len(template.row_tops) - 1))
    else:
        row_step = template.bar_height + 1

    first_top = template.row_tops[0]
    row_tops = tuple(first_top + index * row_step for index in range(task_count))
    bottom_gap = template.bottom_line_y - (template.row_tops[-1] + template.bar_height)
    bottom_line_y = row_tops[-1] + template.bar_height + bottom_gap
    height = template.height + (bottom_line_y - template.bottom_line_y)
    return replace(template, height=height, bottom_line_y=bottom_line_y, row_tops=row_tops)


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def sample_month_labels() -> list[str]:
    """Return labels matching the supplied reference images.

    The sample axis contains 60 periods from octubre-22 through octubre-27
    and skips febrero-27 near the end.  This function intentionally mirrors
    that source material instead of silently correcting the calendar.
    """

    labels = [
        "octubre-22",
        "noviembre-22",
        "diciembre-22",
        "enero-23",
        "febrero-23",
        "marzo-23",
        "abril-23",
        "mayo-23",
        "junio-23",
        "julio-23",
        "agosto-23",
        "septiembre-23",
        "octubre-23",
        "noviembre-23",
        "diciembre-23",
        "enero-24",
        "febrero-24",
        "marzo-24",
        "abril-24",
        "mayo-24",
        "junio-24",
        "julio-24",
        "agosto-24",
        "septiembre-24",
        "octubre-24",
        "noviembre-24",
        "diciembre-24",
        "enero-25",
        "febrero-25",
        "marzo-25",
        "abril-25",
        "mayo-25",
        "junio-25",
        "julio-25",
        "agosto-25",
        "septiembre-25",
        "octubre-25",
        "noviembre-25",
        "diciembre-25",
        "enero-26",
        "febrero-26",
        "marzo-26",
        "abril-26",
        "mayo-26",
        "junio-26",
        "julio-26",
        "agosto-26",
        "septiembre-26",
        "octubre-26",
        "noviembre-26",
        "diciembre-26",
        "enero-27",
        "marzo-27",
        "abril-27",
        "mayo-27",
        "junio-27",
        "julio-27",
        "agosto-27",
        "septiembre-27",
        "octubre-27",
    ]
    if len(labels) != 60:
        raise ValueError(f"Expected 60 month labels, got {len(labels)}")
    return labels


def require_int(stage: dict[str, Any], key: str, row_number: int) -> int:
    if key not in stage:
        raise ValueError(f"Stage {row_number} is missing required field '{key}'.")
    value = stage[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Stage {row_number} field '{key}' must be an integer.")
    return value


def parse_task(stage: Any, row_number: int) -> Task:
    if not isinstance(stage, dict):
        raise ValueError(f"Stage {row_number} must be a JSON object.")
    name = stage.get("name", stage.get("activity", f"Stage {row_number}"))
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Stage {row_number} field 'name' must be a non-empty string.")

    task = Task(
        name=name.strip(),
        plan_start=require_int(stage, "plan_start", row_number),
        plan_duration=require_int(stage, "plan_duration", row_number),
        actual_start=require_int(stage, "actual_start", row_number),
        actual_duration=require_int(stage, "actual_duration", row_number),
    )
    for key, value in (
        ("plan_start", task.plan_start),
        ("actual_start", task.actual_start),
    ):
        if value < 1:
            raise ValueError(f"Stage {row_number} field '{key}' must be 1 or greater.")
    for key, value in (
        ("plan_duration", task.plan_duration),
        ("actual_duration", task.actual_duration),
    ):
        if value < 0:
            raise ValueError(f"Stage {row_number} field '{key}' must be 0 or greater.")
    return task


def validate_chart_data(chart_data: ChartData) -> None:
    if not chart_data.tasks:
        raise ValueError("The data file must contain at least one stage.")
    if not chart_data.periods:
        raise ValueError("The data file must contain at least one period label.")
    if chart_data.current_period < 1 or chart_data.current_period > len(chart_data.periods):
        raise ValueError(
            f"current_period must be between 1 and {len(chart_data.periods)}, "
            f"got {chart_data.current_period}."
        )
    for index, task in enumerate(chart_data.tasks, start=1):
        for label, start in (("plan", task.plan_start), ("actual", task.actual_start)):
            if start > len(chart_data.periods):
                raise ValueError(
                    f"Stage {index} ({task.name}) {label} bar starts at period {start}, "
                    f"but only {len(chart_data.periods)} periods are defined."
                )
        for label, end in (("plan", task.plan_end), ("actual", task.actual_end)):
            if end - 1 > len(chart_data.periods):
                raise ValueError(
                    f"Stage {index} ({task.name}) {label} bar ends at period {end - 1}, "
                    f"but only {len(chart_data.periods)} periods are defined."
                )


def load_chart_data(path: Path) -> ChartData:
    with path.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    if isinstance(raw_data, list):
        stages = raw_data
        periods = sample_month_labels()
        current_period = 20
    elif isinstance(raw_data, dict):
        stages = raw_data.get("stages")
        if not isinstance(stages, list):
            raise ValueError("The data file must contain a 'stages' list.")

        raw_periods = raw_data.get("periods", sample_month_labels())
        if not isinstance(raw_periods, list) or not raw_periods:
            raise ValueError("'periods' must be a non-empty list of labels.")
        periods = []
        for index, period in enumerate(raw_periods, start=1):
            if not isinstance(period, str) or not period.strip():
                raise ValueError(f"Period {index} must be a non-empty string.")
            periods.append(period.strip())

        current_period = raw_data.get("current_period", 20)
        if isinstance(current_period, bool) or not isinstance(current_period, int):
            raise ValueError("'current_period' must be an integer.")
    else:
        raise ValueError("The data file must be either an object or a list of stages.")

    chart_data = ChartData(
        current_period=current_period,
        periods=tuple(periods),
        tasks=tuple(parse_task(stage, index) for index, stage in enumerate(stages, start=1)),
    )
    validate_chart_data(chart_data)
    return chart_data


def period_width(layout: Layout, period_count: int) -> float:
    return (layout.plot_right - layout.plot_left) / period_count


def period_left(layout: Layout, period_number: int, period_count: int) -> int:
    return round(layout.plot_left + (period_number - 1) * period_width(layout, period_count))


def period_right(layout: Layout, period_number: int, period_count: int) -> int:
    return round(layout.plot_left + period_number * period_width(layout, period_count))


def period_center(layout: Layout, period_number: int, period_count: int) -> float:
    return layout.plot_left + (period_number - 0.5) * period_width(layout, period_count)


def text_size(text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1]


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int] = TEXT,
) -> None:
    draw.text(xy, text, font=font, fill=fill, anchor="mm")


def draw_rotated_label(
    image: Image.Image,
    x_center: float,
    bottom_y: int,
    text: str,
    font: ImageFont.ImageFont,
) -> None:
    width, height = text_size(text, font)
    label = Image.new("RGBA", (width + 4, height + 4), (255, 255, 255, 0))
    label_draw = ImageDraw.Draw(label)
    label_draw.text((2, 2), text, font=font, fill=HEADER_TEXT)
    rotated = label.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    x = round(x_center - rotated.width / 2)
    y = bottom_y - rotated.height
    image.alpha_composite(rotated, (x, y))


def draw_hatched_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    spacing: int,
    line_width: int = 1,
) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=WHITE)
    for diagonal in range(x0 + y0, x1 + y1 + spacing, spacing):
        points: list[tuple[int, int]] = []
        for x in (x0, x1):
            y = diagonal - x
            if y0 <= y <= y1:
                points.append((x, y))
        for y in (y0, y1):
            x = diagonal - y
            if x0 <= x <= x1:
                points.append((x, y))
        if len(points) >= 2:
            first, second = points[0], points[-1]
            draw.line((first, second), fill=HATCH, width=line_width)


def draw_period_grid(draw: ImageDraw.ImageDraw, layout: Layout, period_count: int) -> None:
    for period in range(1, period_count + 1, 2):
        x0 = period_left(layout, period, period_count)
        x1 = period_right(layout, period, period_count) - 1
        draw.rectangle((x0, layout.grid_top, x1, layout.grid_bottom), fill=GRID)


def draw_frame(draw: ImageDraw.ImageDraw, layout: Layout) -> None:
    draw.line((0, layout.header_line_y, layout.plot_right, layout.header_line_y), fill=PURPLE, width=1)
    draw.line((0, layout.bottom_line_y, layout.plot_right, layout.bottom_line_y), fill=PURPLE, width=1)
    draw.rectangle(
        (layout.plot_right - 2, layout.right_line_top_y, layout.plot_right, layout.bottom_line_y),
        fill=RED,
    )


def draw_headers(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    layout: Layout,
    *,
    periods: Sequence[str],
    start_header: str,
    duration_header: str,
) -> None:
    header_font = load_font(layout.header_font_size, bold=True)
    month_font = load_font(layout.month_font_size, bold=True)
    number_font = load_font(layout.number_font_size, bold=True)

    draw.text((layout.activity_x, layout.header_y), "ACTIVITY", font=header_font, fill=HEADER_TEXT, anchor="lm")

    if "\n" in start_header:
        line1, line2 = start_header.split("\n", maxsplit=1)
        draw_centered_text(draw, (layout.start_x, layout.header_y - 14), line1, header_font, HEADER_TEXT)
        draw_centered_text(draw, (layout.start_x, layout.header_y + 9), line2, header_font, HEADER_TEXT)
    else:
        draw_centered_text(draw, (layout.start_x, layout.header_y), start_header, header_font, HEADER_TEXT)

    if "\n" in duration_header:
        line1, line2 = duration_header.split("\n", maxsplit=1)
        draw_centered_text(draw, (layout.duration_x, layout.header_y - 24), line1, header_font, HEADER_TEXT)
        draw_centered_text(draw, (layout.duration_x, layout.header_y + 9), line2, header_font, HEADER_TEXT)
    else:
        draw_centered_text(draw, (layout.duration_x, layout.header_y), duration_header, header_font, HEADER_TEXT)

    period_count = len(periods)
    for index, label in enumerate(periods, start=1):
        draw_rotated_label(image, period_center(layout, index, period_count), layout.month_label_bottom_y, label, month_font)
        draw_centered_text(
            draw,
            (period_center(layout, index, period_count), layout.month_number_y),
            str(index),
            number_font,
            HEADER_TEXT,
        )


def draw_table_values(
    draw: ImageDraw.ImageDraw,
    layout: Layout,
    rows: Sequence[tuple[str, int, int]],
) -> None:
    row_font = load_font(layout.row_font_size, bold=True)
    value_font = load_font(layout.value_font_size)
    for index, (name, start, duration) in enumerate(rows):
        top = layout.row_tops[index]
        draw.text(
            (layout.row_label_x, top + layout.row_text_offset_y),
            name,
            font=row_font,
            fill=TEXT,
            anchor="lm",
        )
        draw_centered_text(
            draw,
            (layout.start_x, top + layout.value_text_offset_y),
            str(start),
            value_font,
            TEXT,
        )
        draw_centered_text(
            draw,
            (layout.duration_x, top + layout.value_text_offset_y),
            str(duration),
            value_font,
            TEXT,
        )


def draw_bar(
    draw: ImageDraw.ImageDraw,
    layout: Layout,
    period_count: int,
    row_index: int,
    start: int,
    duration: int,
    color: tuple[int, int, int, int],
) -> None:
    if duration <= 0:
        return
    x0 = period_left(layout, start, period_count)
    x1 = period_right(layout, start + duration - 1, period_count) - 1
    y0 = layout.row_tops[row_index]
    y1 = y0 + layout.bar_height
    draw.rectangle((x0, y0, x1, y1), fill=color)


def render_plan(tasks: Sequence[Task], periods: Sequence[str]) -> Image.Image:
    layout = layout_for_task_count(PLAN_LAYOUT, len(tasks))
    image = Image.new("RGBA", (layout.width, layout.height), WHITE)
    draw = ImageDraw.Draw(image)
    period_count = len(periods)

    draw_period_grid(draw, layout, period_count)
    for index, task in enumerate(tasks):
        draw_bar(draw, layout, period_count, index, task.plan_start, task.plan_duration, PURPLE)

    draw_headers(
        image,
        draw,
        layout,
        periods=periods,
        start_header="PLAN START",
        duration_header="PLAN\nDURATION",
    )
    draw_table_values(
        draw,
        layout,
        [(task.name, task.plan_start, task.plan_duration) for task in tasks],
    )
    draw_frame(draw, layout)
    return image


def draw_current_marker(
    draw: ImageDraw.ImageDraw,
    layout: Layout,
    current_period: int,
    period_count: int,
) -> None:
    if layout.current_top_y is None:
        return
    x0 = period_left(layout, current_period, period_count)
    x1 = period_right(layout, current_period, period_count) - 1
    draw.rectangle((x0, layout.current_top_y, x1, layout.bottom_line_y - 1), fill=CURRENT_FILL)
    draw.line((x0, layout.current_top_y, x0, layout.bottom_line_y - 1), fill=CURRENT_EDGE, width=1)
    draw.line((x1, layout.current_top_y, x1, layout.bottom_line_y - 1), fill=CURRENT_EDGE, width=1)


def render_actual(tasks: Sequence[Task], periods: Sequence[str], *, current_period: int) -> Image.Image:
    layout = layout_for_task_count(ACTUAL_LAYOUT, len(tasks))
    image = Image.new("RGBA", (layout.width, layout.height), WHITE)
    draw = ImageDraw.Draw(image)
    period_count = len(periods)

    draw_period_grid(draw, layout, period_count)

    for index, task in enumerate(tasks):
        top = layout.row_tops[index]
        bottom = top + layout.bar_height

        if task.actual_start > task.plan_start:
            x0 = period_left(layout, task.plan_start, period_count)
            x1 = period_left(layout, task.actual_start, period_count) - 1
            draw_hatched_rect(draw, (x0, top, x1, bottom), spacing=4)

        draw_bar(draw, layout, period_count, index, task.actual_start, task.actual_duration, PURPLE)

        overrun_start = max(task.actual_start, task.plan_end)
        overrun_duration = task.actual_end - overrun_start
        if overrun_duration > 0:
            draw_bar(draw, layout, period_count, index, overrun_start, overrun_duration, OVERDUE)

    draw_current_marker(draw, layout, current_period, period_count)

    draw_headers(
        image,
        draw,
        layout,
        periods=periods,
        start_header="ACTUAL/PLAN\nSTART",
        duration_header="ACTUAL/PLAN\nDURATION",
    )
    draw_table_values(
        draw,
        layout,
        [(task.name, task.actual_start, task.actual_duration) for task in tasks],
    )
    draw_frame(draw, layout)
    return image


def save_image(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def compare_images(generated: Path, sample: Path) -> tuple[float, float, tuple[int, int, int, int] | None]:
    with Image.open(generated).convert("RGB") as generated_image:
        with Image.open(sample).convert("RGB") as sample_image:
            if generated_image.size != sample_image.size:
                raise ValueError(
                    f"{generated.name} is {generated_image.size}, sample is {sample_image.size}"
                )
            diff = ImageChops.difference(generated_image, sample_image)
            histogram = diff.histogram()
            square_sum = sum(value * ((index % 256) ** 2) for index, value in enumerate(histogram))
            channel_count = len(generated_image.getbands())
            pixel_count = generated_image.size[0] * generated_image.size[1]
            rms = math.sqrt(square_sum / (pixel_count * channel_count))
            changed_pixels = sum(diff.convert("L").histogram()[1:])
            changed_percent = changed_pixels * 100 / pixel_count
            return rms, changed_percent, diff.getbbox()


def render_all(output_dir: Path, chart_data: ChartData, *, current_period: int) -> dict[str, Path]:
    outputs = {
        "original": output_dir / "original.png",
        "actual": output_dir / "actual.png",
    }
    save_image(render_plan(chart_data.tasks, chart_data.periods), outputs["original"])
    save_image(
        render_actual(chart_data.tasks, chart_data.periods, current_period=current_period),
        outputs["actual"],
    )
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate sample-style Gantt PNG diagrams.")
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help=f"JSON data file. Default: {DEFAULT_DATA_FILE}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for generated PNG files. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--current-period",
        "--current-month",
        dest="current_period",
        type=int,
        default=None,
        help="Override the period highlighted in the actual/plan diagram.",
    )
    parser.add_argument(
        "--compare-samples",
        action="store_true",
        help="Compare generated images with samples/original.png and samples/actual.png.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    chart_data = load_chart_data(args.data)
    current_period = args.current_period if args.current_period is not None else chart_data.current_period
    chart_data = replace(chart_data, current_period=current_period)
    validate_chart_data(chart_data)
    outputs = render_all(args.output_dir, chart_data, current_period=current_period)

    for name, path in outputs.items():
        print(f"wrote {name}: {path}")

    if args.compare_samples:
        for name, generated in outputs.items():
            sample = SAMPLES_DIR / f"{name}.png"
            if not sample.exists():
                print(f"missing sample for {name}: {sample}")
                continue
            rms, changed_percent, bbox = compare_images(generated, sample)
            print(
                f"{name} vs sample: rms={rms:.2f}, "
                f"changed_pixels={changed_percent:.2f}%, diff_bbox={bbox}"
            )


if __name__ == "__main__":
    main()
