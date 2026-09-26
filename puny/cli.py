"""命令行入口：编解码 punycode 标签。"""

import argparse
import sys

from .codec import PunyError, decode_label, encode_label


def build_parser():
    parser = argparse.ArgumentParser(prog="punycode", description="punycode 标签")
    parser.add_argument("--encode", help="把这段文本编成 punycode 标签")
    parser.add_argument("--decode", help="把这段 punycode 标签解码")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.encode is not None:
            print(encode_label(args.encode))
            return 0
        if args.decode is not None:
            print(decode_label(args.decode))
            return 0
    except PunyError as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1
    print("错误：需要 --encode 或 --decode", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
