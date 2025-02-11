import argparse

from comfyui_api import ComfyUIAPI
from lib.plotfile import PlotFile
from lib.plotfilerenderer import PlotFileRenderer


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--comfyui_ip", type=str, help="IP of ComfyUI interface", default="127.0.0.1")
    parser.add_argument("--comfyui_port", type=str, help="Port of ComfyUI interface", default="8188")
    parser.add_argument("--cleanup", action="store_true", help="Set the flag to delete images that is not the same name as the ones you want to generate.")
    parser.add_argument("--skip_mass_generation", action="store_true", help="Set the flag to skip the step with generation of XY plot (only make images)")
    parser.add_argument("--make_html_table", action="store_true", help="Set the flag to make HTML version of the table - The Original Infinitable.")
    parser.add_argument("--make_html_smallplot", action="store_true", help="Set the flag to make HTML version of the table - The SmallPlot, web-friendly.")
    parser.add_argument("--ignore_non_replacements", action="store_true", help="Set the flag to True if you are fine that on Axis variable replacement step there can be no replacements to workflow")
    parser.add_argument("--yes", action="store_true", help="Do not wait for enter key in the end")
    parser.add_argument("--hash_filenames", action="store_true", help="Use sha256 hex-hashed filenames instead of usual filenames")
    parser.add_argument("--flip_last_axis", action="store_true", help="If XY plot is an odd number (3, 5, 7, etc...), then make last axis VERTICAL instead of HORIZONTAL")
    parser.add_argument("--autoflip_last_axis", action="store_true", help="If XY plot is an odd number (3, 5, 7, etc...), then make last axis VERTICAL instead of HORIZONTAL, if it saves on Autoreduce function!")
    parser.add_argument("--resize_ratio", type=float, help="Set to number lower than 1 to scale down the XY plot (useful if you have thousands of HD images)")
    parser.add_argument("--autoreduce", type=int, help="Set the flag to automatically lower the XY grid size to a (your specified number) pixels if it was above such number.")
    parser.add_argument("plotfile", type=str, help="Path to PLOTFILE")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    plotfile = PlotFile(args.plotfile)
    api = ComfyUIAPI(args.comfyui_ip, args.comfyui_port)
    renderer = PlotFileRenderer(api)
    kwargs = dict()
    kwargs.setdefault("skip_mass_generation", args.skip_mass_generation)
    kwargs.setdefault("ignore_non_replacements", args.ignore_non_replacements)
    kwargs.setdefault("flip_last_axis", args.flip_last_axis)
    kwargs.setdefault("autoflip_last_axis", args.autoflip_last_axis)
    kwargs.setdefault("make_html_table", args.make_html_table)
    kwargs.setdefault("make_html_smallplot", args.make_html_smallplot)
    kwargs.setdefault("hash_filenames", args.hash_filenames)
    kwargs.setdefault("cleanup", args.cleanup)
    kwargs.setdefault("yes", args.yes)
    if args.resize_ratio is not None:
        kwargs.setdefault("resize_ratio", args.resize_ratio)
    if args.autoreduce is not None:
        kwargs.setdefault("autoreduce", args.autoreduce)
    renderer.render(plotfile, **kwargs)
