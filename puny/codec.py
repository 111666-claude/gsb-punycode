"""punycode：基本码点 + 扩展部分。只用标准库。"""

BASE = 36
TMIN = 1
TMAX = 26
SKEW = 38
DAMP = 700
INITIAL_BIAS = 72
INITIAL_N = 128


class PunyError(Exception):
    """punycode 不合法；position 是出错字符的偏移（0 起），可为 None。"""

    def __init__(self, message, position=None):
        super().__init__(message)
        self.message = message
        self.position = position


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


def _threshold(k, bias):
    if k <= bias:
        return TMIN
    if k >= bias + TMAX:
        return TMAX
    return k - bias


class _Fenwick:
    """树状数组：前缀和与按次序取槽位，O(log n)。"""

    def __init__(self, size, fill=0):
        self.size = size
        self.tree = [0] * (size + 1)
        if fill:
            for pos in range(1, size + 1):
                self.tree[pos] = (pos & -pos) * fill

    def add(self, index, delta):
        index += 1
        tree = self.tree
        size = self.size
        while index <= size:
            tree[index] += delta
            index += index & -index

    def sum_to(self, index):
        """[0, index) 的前缀和。"""
        total = 0
        tree = self.tree
        while index > 0:
            total += tree[index]
            index -= index & -index
        return total

    def total(self):
        return self.sum_to(self.size)

    def kth(self, k):
        """第 k 个（1 起）未占用槽位的 0 起偏移。"""
        index = 0
        bit = 1 << (self.size.bit_length() - 1)
        tree = self.tree
        while bit:
            nxt = index + bit
            if nxt <= self.size and tree[nxt] < k:
                index = nxt
                k -= tree[nxt]
            bit >>= 1
        return index


def encode_label(text):
    """编码一个标签：基本码点后跟 '-' 再写扩展部分；单遍统计，内存 O(标签长度)。"""
    if not text:
        return ""
    ords = [ord(char) for char in text]
    out = [chr(point) for point in ords if point < INITIAL_N]
    basic_count = len(out)
    if basic_count == len(ords):
        out.append("-")
        return "".join(out)
    if basic_count:
        out.append("-")

    # 每个位置之前有多少更小的码点（树状数组单遍统计）
    distinct = sorted(set(ords))
    rank = {point: index for index, point in enumerate(distinct)}
    counter = _Fenwick(len(distinct))
    smaller_before = [0] * len(ords)
    positions = {}
    for at, point in enumerate(ords):
        smaller_before[at] = counter.sum_to(rank[point])
        counter.add(rank[point], 1)
        if point >= INITIAL_N:
            positions.setdefault(point, []).append(at)

    handled = basic_count
    less_total = basic_count  # 码点严格小于当前 n 的位置总数
    n = INITIAL_N
    delta = 0
    bias = INITIAL_BIAS
    for point in distinct:
        if point < INITIAL_N:
            continue
        delta += (point - n) * (less_total + 1)
        n = point
        previous = 0
        for at in positions[point]:
            delta += smaller_before[at] - previous
            previous = smaller_before[at]
            q = delta
            k = BASE
            while True:
                threshold = _threshold(k, bias)
                if q < threshold:
                    break
                out.append(digit_to_char(threshold + (q - threshold) % (BASE - threshold)))
                q = (q - threshold) // (BASE - threshold)
                k += BASE
            out.append(digit_to_char(q))
            bias = adapt(delta, handled + 1, handled == basic_count)
            delta = 0
            handled += 1
        delta += less_total - previous
        less_total += len(positions[point])
        delta += 1
        n += 1
    return "".join(out)


def decode_label(label):
    """解码一个标签；校验 '-' 位置、扩展部分数字与截断，错误带字符偏移。"""
    if not label:
        return ""
    dash = label.rfind("-")
    if dash != -1:
        if dash == 0:
            raise PunyError("'-' 位置非法：第 1 个字符前没有基本码点", 0)
        basic = label[:dash]
        encoded = label[dash + 1:]
        offset = dash + 1
    else:
        basic = ""
        encoded = label
        offset = 0

    inserts = []
    out_len = len(basic)
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
                raise PunyError("扩展部分截断：第 %d 个字符处还需要更多数字" % (offset + at + 1), offset + at)
            char = encoded[at]
            try:
                digit = char_to_digit(char)
            except PunyError:
                raise PunyError("非法数字 %r：第 %d 个字符" % (char, offset + at + 1), offset + at) from None
            at += 1
            i += digit * w
            threshold = _threshold(k, bias)
            if digit < threshold:
                break
            w *= BASE - threshold
            k += BASE
        bias = adapt(i - old, out_len + 1, old == 0)
        n += i // (out_len + 1)
        i %= out_len + 1
        inserts.append((i, chr(n)))
        i += 1
        out_len += 1

    if not inserts:
        return basic

    # 逆序把插入字符放到最终槽位，避免逐个 list.insert 的 O(n^2) 搬移
    total = len(basic) + len(inserts)
    free = _Fenwick(total, fill=1)
    slots = [None] * total
    for index, char in reversed(inserts):
        slot = free.kth(index + 1)
        slots[slot] = char
        free.add(slot, -1)
    rest = iter(basic)
    for slot in range(total):
        if slots[slot] is None:
            slots[slot] = next(rest)
    return "".join(slots)
