__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import sys

import click

click.disable_unicode_literals_warning = True

# ~~ "octoprint util" commands


def validate_result(result):
    dimensions = ("depth", "height", "width")
    printing_area = ("maxX", "maxY", "maxZ", "minX", "minY", "minZ")

    def validate_list(data):
        return not any(map(invalid_float, data))

    def validate_dict(data, keys):
        for k in keys:
            if k not in data or invalid_float(data[k]):
                return False
        return True

    def invalid_float(value):
        return value is None or value == float("inf") or value == float("-inf")

    if "dimensions" not in result or not validate_dict(result["dimensions"], dimensions):
        return False

    if "extrusion_length" not in result or not validate_list(result["extrusion_length"]):
        return False

    if "extrusion_volume" not in result or not validate_list(result["extrusion_volume"]):
        return False

    if "printing_area" not in result or not validate_dict(
        result["printing_area"], printing_area
    ):
        return False

    if "total_time" not in result or invalid_float(result["total_time"]):
        return False


@click.group()
def analysis_commands():
    pass


@analysis_commands.group(name="analysis")
def util():
    """Analysis tools."""
    pass


@util.command(name="gcode")
@click.option("--throttle", "throttle", type=float, default=None)
@click.option("--throttle-lines", "throttle_lines", type=int, default=None)
@click.option("--speed-x", "speedx", type=float, default=6000)
@click.option("--speed-y", "speedy", type=float, default=6000)
@click.option("--speed-z", "speedz", type=float, default=300)
@click.option("--offset", "offset", type=(float, float), multiple=True)
@click.option("--max-t", "maxt", type=int, default=10)
@click.option("--g90-extruder", "g90_extruder", is_flag=True)
@click.option("--progress", "progress", is_flag=True)
@click.argument("path", type=click.Path())
def gcode_command(
    path,
    speedx,
    speedy,
    speedz,
    offset,
    maxt,
    throttle,
    throttle_lines,
    g90_extruder,
    progress,
):
    """Runs a GCODE file analysis."""

    import time

    import yaml

    from octoprint.util.gcodeInterpreter import gcode

    throttle_callback = None
    if throttle:

        def throttle_callback(filePos, readBytes):
            if filePos % throttle_lines == 0:
                # only apply throttle every $throttle_lines lines
                time.sleep(throttle)

    offsets = offset
    if offsets is None:
        offsets = []
    elif isinstance(offset, tuple):
        offsets = list(offsets)
    offsets = [(0, 0)] + offsets
    if len(offsets) < maxt:
        offsets += [(0, 0)] * (maxt - len(offsets))

    start_time = time.monotonic()

    progress_callback = None
    if progress:

        def progress_callback(percentage):
            click.echo("PROGRESS:{}".format(percentage))

    interpreter = gcode(progress_callback=progress_callback)

    interpreter.load(
        path,
        speedx=speedx,
        speedy=speedy,
        offsets=offsets,
        throttle=throttle_callback,
        max_extruders=maxt,
        g90_extruder=g90_extruder,
    )

    click.echo("DONE:{}s".format(time.monotonic() - start_time))

    result = interpreter.get_result()
    if not validate_result(result):
        click.echo(
            "ERROR:Invalid analysis result, please create a bug report in OctoPrint's "
            "issue tracker and be sure to also include the GCODE file with which this "
            "happened"
        )
        sys.exit(-1)
    click.echo("RESULTS:")
    click.echo(
        yaml.safe_dump(
            interpreter.get_result(),
            default_flow_style=False,
            indent=4,
            allow_unicode=True,
        )
    )


if __name__ == "__main__":
    gcode_command()
