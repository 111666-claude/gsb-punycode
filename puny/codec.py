"""punycode：基本码点 + 扩展部分。只用标准库。"""

BASE = 36
TMIN = 1
TMAX = 26
SKEW = 38
DAMP = 700
INITIAL_BIAS = 72
INITIAL_N = 128


class PunyError(Exception):
    """punycode 不合法。缺陷：不带位置。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def digit_to_char(value):
    if value < 26:
        return chr(ord("a") + value)
    return chr(ord("0") + value - 26)


def char_to_digit(char):
    if "a" <= char <= "z":
        return ord(char) - ord("a")
    if "0" <= char <= "9":
        return ord(char) - ord("0") + 26
    raise PunyError("不是 punycode 数字：%r" % char)


def adapt(delta, points, first):
    """自适应偏置。缺陷：固定用初始偏置，不按 delta 衰减。"""
    _ = (delta, points, first)
    return INITIAL_BIAS


def encode_label(text):
    """编码一个标签。缺陷：基本码点后没有加 '-' 分隔符。"""
    base_points = [ord(char) for char in text if ord(char) < INITIAL_N]
    out = "".join(chr(point) for point in base_points)
    handled = len(base_points)
    n = INITIAL_N
    delta = 0
    bias = INITIAL_BIAS
    while handled < len(text):
        smallest = min(ord(char) for char in text if ord(char) >= n)
        delta += (smallest - n) * (handled + 1)
        n = smallest
        for char in text:
            point = ord(char)
            if point < n:
                delta += 1
            elif point == n:
                q = delta
                for k in range(BASE, 1 << 20, BASE):
                    threshold = TMIN if k <= bias else (TMAX if k >= bias + TMAX else k - bias)
                    if q < threshold:
                        break
                    out += digit_to_char(threshold + (q - threshold) % (BASE - threshold))
                    q = (q - threshold) // (BASE - threshold)
                out += digit_to_char(q)
                bias = adapt(delta, handled + 1, handled == len(base_points))
                delta = 0
                handled += 1
        delta += 1
        n += 1
    return out


def decode_label(label):
    """解码一个标签。缺陷：不校验尾随 '-'，也不校验非法数字。"""
    if "-" in label:
        basic, encoded = label.rsplit("-", 1)
    else:
        basic, encoded = "", label
    out = list(basic)
    n = INITIAL_N
    i = 0
    bias = INITIAL_BIAS
    at = 0
    while at < len(encoded):
        old = i
        w = 1
        k = BASE
        while True:
            if at >= len(encoded):
                raise PunyError("扩展部分不完整")
            digit = char_to_digit(encoded[at])
            at += 1
            i += digit * w
            threshold = TMIN if k <= bias else (TMAX if k >= bias + TMAX else k - bias)
            if digit < threshold:
                break
            w *= BASE - threshold
            k += BASE
        bias = adapt(i - old, len(out) + 1, old == 0)
        n += i // (len(out) + 1)
        i %= len(out) + 1
        out.insert(i, chr(n))
        i += 1
    return "".join(out)
