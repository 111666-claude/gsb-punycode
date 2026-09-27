"""punycode：基本码点 + 扩展部分（RFC 3492）。只用标准库。"""

BASE = 36
TMIN = 1
TMAX = 26
SKEW = 38
DAMP = 700
INITIAL_BIAS = 72
INITIAL_N = 128


class PunyError(Exception):
    """punycode 不合法；pos 是出错字符在标签里的偏移（从 0 计）。"""

    def __init__(self, message, pos=None):
        super().__init__(message)
        self.message = message
        self.pos = pos


def digit_to_char(value):
    if value < 26:
        return chr(ord("a") + value)
    return chr(ord("0") + value - 26)


def char_to_digit(char):
    if "a" <= char <= "z":
        return ord(char) - ord("a")
    if "A" <= char <= "Z":
        return ord(char) - ord("A")
    if "0" <= char <= "9":
        return ord(char) - ord("0") + 26
    raise PunyError("不是 punycode 数字：%r" % char)


def adapt(delta, points, first):
    """RFC 3492 的偏置自适应：随 delta 衰减。"""
    delta = delta // DAMP if first else delta // 2
    delta += delta // points
    k = 0
    while delta > ((BASE - TMIN) * TMAX) // 2:
        delta //= BASE - TMIN
        k += BASE
    return k + (BASE - TMIN + 1) * delta // (delta + SKEW)


def encode_label(text):
    """编码一个标签；有基本码点时后面跟 '-' 再写扩展部分。"""
    if not text:
        return ""
    out = [char for char in text if ord(char) < INITIAL_N]
    handled = len(out)
    if handled:
        out.append("-")
    basic_count = handled
    n = INITIAL_N
    delta = 0
    bias = INITIAL_BIAS
    length = len(text)
    while handled < length:
        smallest = min(ord(char) for char in text if ord(char) >= n)
        delta += (smallest - n) * (handled + 1)
        n = smallest
        for char in text:
            point = ord(char)
            if point < n:
                delta += 1
            elif point == n:
                q = delta
                k = BASE
                while True:
                    if k <= bias:
                        threshold = TMIN
                    elif k >= bias + TMAX:
                        threshold = TMAX
                    else:
                        threshold = k - bias
                    if q < threshold:
                        break
                    out.append(digit_to_char(threshold + (q - threshold) % (BASE - threshold)))
                    q = (q - threshold) // (BASE - threshold)
                    k += BASE
                out.append(digit_to_char(q))
                bias = adapt(delta, handled + 1, handled == basic_count)
                delta = 0
                handled += 1
        delta += 1
        n += 1
    return "".join(out)


def decode_label(label):
    """解码一个标签；校验 '-' 位置、扩展部分数字与截断，错误带偏移。"""
    if not label:
        return ""
    dash = label.find("-")
    if dash != -1:
        again = label.find("-", dash + 1)
        if again != -1:
            raise PunyError("'-' 只能出现一次（第 %d 个字符）" % (again + 1), again)
        if dash == 0:
            raise PunyError("'-' 必须跟在基本码点之后（第 1 个字符）", 0)
        basic, encoded = label[:dash], label[dash + 1:]
        offset = dash + 1
    else:
        basic, encoded = "", label
        offset = 0
    for index, char in enumerate(basic):
        if ord(char) >= INITIAL_N:
            raise PunyError(
                "基本码点必须是 ASCII（第 %d 个字符：%r）" % (index + 1, char), index
            )
    out = list(basic)
    n = INITIAL_N
    i = 0
    bias = INITIAL_BIAS
    at = 0
    end = len(encoded)
    while at < end:
        old = i
        w = 1
        k = BASE
        while True:
            if at >= end:
                raise PunyError(
                    "扩展部分被截断（第 %d 个字符处结束）" % (offset + at + 1),
                    offset + at,
                )
            char = encoded[at]
            try:
                digit = char_to_digit(char)
            except PunyError:
                raise PunyError(
                    "扩展部分含非法数字（第 %d 个字符：%r）" % (offset + at + 1, char),
                    offset + at,
                ) from None
            at += 1
            i += digit * w
            if k <= bias:
                threshold = TMIN
            elif k >= bias + TMAX:
                threshold = TMAX
            else:
                threshold = k - bias
            if digit < threshold:
                break
            w *= BASE - threshold
            k += BASE
        points = len(out) + 1
        bias = adapt(i - old, points, old == 0)
        n += i // points
        i %= points
        out.insert(i, chr(n))
        i += 1
    return "".join(out)
