"""punycode 标签编解码。"""

from .codec import PunyError, decode_label, encode_label

__all__ = ["PunyError", "decode_label", "encode_label"]
