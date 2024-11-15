import argparse

from comfyui_api import ComfyUIAPI
from lib.plotfile import PlotFile
from lib.renderer import PlotFileRenderer


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--comfyui_ip", type=str, help="IP of ComfyUI interface", default="127.0.0.1")
    parser.add_argument("--comfyui_port", type=str, help="Port of ComfyUI interface", default="8188")
    parser.add_argument("--skip_mass_generation", action="store_true", help="Set the flag to skip the step with generation of XY plot (only make images)")
    parser.add_argument("--ignore_non_replacements", action="store_true", help="Set the flag to True if you are fine that on Axis variable replacement step there can be no replacements to workflow")
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
    if args.resize_ratio is not None:
        kwargs.setdefault("resize_ratio", args.resize_ratio)
    if args.autoreduce is not None:
        kwargs.setdefault("autoreduce", args.autoreduce)
    renderer.render(plotfile, **kwargs)
