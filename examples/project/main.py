import argparse
import sys

import haven
from mylib.config import Config


def parse_args(argv):
    parser = argparse.ArgumentParser("my_program")
    parser.add_argument("--cfg", required=True, help="Path to config file to load.")
    parser.add_argument("overrides", nargs=argparse.REMAINDER)
    return parser.parse_args(argv)


def main(arg_list):
    args = parse_args(arg_list)

    # Load yaml config file and cli overrides
    with open(args.cfg, "r") as f:
        cfg = haven.load(Config, f, dotlist_overrides=args.overrides)

    # Print yaml
    print(haven.dump(cfg))

    cfg.task(cfg)


if __name__ == "__main__":
    main(sys.argv[1:])
