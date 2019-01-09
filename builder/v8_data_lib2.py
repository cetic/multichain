import logging
import os
import sys
from argparse import ArgumentParser
from itertools import chain
from subprocess import call

from pathlib2 import Path

logger = logging.getLogger(str(Path(__file__).stem))
asm = """
section .rodata

global {USC}binary_{NAME}_{EXT}_start;
global {USC}binary_{NAME}_{EXT}_end;

{USC}binary_{NAME}_{EXT}_start: incbin "{NAME}.{EXT}"
{USC}binary_{NAME}_{EXT}_end:
{USC}binary_{NAME}_{EXT}_size:  dd {USC}binary_{NAME}_{EXT}_end-{USC}binary_{NAME}_{EXT}_start
"""


def get_bin_type(platform):
    if platform == "darwin":
        bin_type = ("macho64", ".o", "lib{}.a")
    elif platform == "win32":
        bin_type = ("win64", ".obj", "{}.lib")
    else:
        bin_type = ("elf64", "{}.o", "lib{}.a")
    return bin_type


def process_bin_file(filepath, platform):
    logger.debug("process_bin_file(filepath={})".format(filepath))
    assert filepath.exists()
    arch, obj_suffix, _lib_pattern = get_bin_type(platform)
    obj_name = filepath.with_suffix(obj_suffix).name
    obj_path = Path("obj") / obj_name
    script = asm.format(USC=('__' if arch == "macho64" else '_'), NAME=filepath.stem, EXT=filepath.suffix[1:])
    script_file = filepath.with_suffix(".s").name
    with open(script_file, 'w') as f:
        f.write(script)
    cmd = ["nasm", "-f", arch, "-o", str(obj_path), script_file]
    logger.info(' '.join(cmd))
    call(cmd)
    return obj_name


def process_bin_files(platform):
    cwd = Path.cwd()
    obj_names = []
    for f in chain(cwd.glob("*.bin"), cwd.glob("*.dat")):
        obj_names.append(process_bin_file(f, platform))
    os.chdir("obj")
    arch, _obj_suffix, lib_pattern = get_bin_type(platform)
    ar = "x86_64-w64-mingw32-ar" if arch == "win64" else "ar"
    cmd = [ar, "rvs", lib_pattern.format("v8_data")]
    cmd += obj_names
    logger.info(' '.join(cmd))
    call(cmd)


def get_options():
    default_path = Path.cwd() / ".." / "v8build" / "v8" / "out.gn" / "x64.release"
    parser = ArgumentParser(description="Build v8_data.lib from .bin and .dat files")
    parser.add_argument("-v", "--verbose", action="store_true", help="print debug messages to log")
    parser.add_argument("-p", "--path", metavar="PATH", type=Path, default=default_path.resolve(),
                        help="path to the V8 build area (default: %(default)s)")
    parser.add_argument("-b", "--binutils", metavar="PATH", type=Path, help="path to binutils")
    parser.add_argument("-o", "--platform", default=sys.platform,
                        help="override platform definition (default: %(default)s)")

    options = parser.parse_args()

    if options.verbose:
        logger.setLevel(logging.DEBUG)

    logger.info("{} - {}".format(logger.name, parser.description))
    logger.info("  Path:     {}".format(options.path))
    logger.info("  Platform: {}".format(options.platform))
    if options.binutils:
        logger.info("  Binutils: {}".format(options.binutils))

    return options


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    options = get_options()
    if options.binutils:
        os.environ["PATH"] = os.pathsep.join(str(options.binutils / "bin"), os.environ["PATH"])
    os.chdir(str(options.path))
    process_bin_files(options.platform)
    return 0


if __name__ == '__main__':
    sys.exit(main())