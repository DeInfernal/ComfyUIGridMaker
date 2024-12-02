import argparse

from comfyui_api import ComfyUIAPI
from lib.linefile import LineFile
from lib.renderer import LineFileRenderer


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--comfyui_ip", type=str, help="IP of ComfyUI interface", default="127.0.0.1")
    parser.add_argument("--comfyui_port", type=str, help="Port of ComfyUI interface", default="8188")
    parser.add_argument("--skip_compilation", action="store_true", help="Set the flag to skip the step with compilation of WEBM file (only make images)")
    parser.add_argument("--do_reverse", action="store_true", help="If set, do a reverse set in the video as well")
    parser.add_argument("--output_type", choices=["apng", "webp", "mp4"], default="webp", help="Set the output file type")
    parser.add_argument("--fps", type=int, default=24, help="Amount of frames per second, integer")
    parser.add_argument("--ignore_non_replacements", action="store_true", help="Set the flag to True if you are fine that on Sliders variable replacement step there can be no replacements to workflow")
    parser.add_argument("--yes", action="store_true", help="Do not wait for enter key in the end")
    parser.add_argument("--resize_ratio", type=float, help="Set to number lower than 1 to scale down the XY plot (useful if you have thousands of HD images)")
    parser.add_argument("linefile", type=str, help="Path to PLOTFILE")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    linefile = LineFile(args.linefile)
    api = ComfyUIAPI(args.comfyui_ip, args.comfyui_port)
    renderer = LineFileRenderer(api)
    kwargs = dict()
    kwargs.setdefault("skip_compilation", args.skip_compilation)
    kwargs.setdefault("output_type", args.output_type)
    kwargs.setdefault("fps", args.fps)
    kwargs.setdefault("do_reverse", args.do_reverse)
    kwargs.setdefault("ignore_non_replacements", args.ignore_non_replacements)
    kwargs.setdefault("yes", args.yes)
    if args.resize_ratio is not None:
        kwargs.setdefault("resize_ratio", args.resize_ratio)
    renderer.render(linefile, **kwargs)
