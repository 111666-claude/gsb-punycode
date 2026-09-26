# punycode

punycode 标签编解码（RFC 3492），只用 Python 标准库。

```
python3 -m puny.cli --encode bücher
python3 -m puny.cli --decode wgv71a119e
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **基本码点后面必须加 `-` 分隔符**（只有扩展部分时也要能区分）：`bücher` 按口径编成 `bcher-kva`
  （标准库 `'bücher'.encode('punycode')` 就是 `b'cher-kva'` 的形式，前面带基本码点），
  现在编出 `bcherkva`（少了那个 `-`）。
- **偏置 bias 必须按 delta 自适应**（`adapt` 里用 `DAMP`/`SKEW`/`TMIN`/`TMAX` 那套公式）：
  现在 `adapt` 直接返回初始偏置 72，所以短串碰巧对、长串全错。
  `--decode wgv71a119e` 按口径是 `日本語`，现在解出乱码；`--decode mnchen-3ya` 应是 `münchen`（这个现在对）。
- 解码要校验：`-` 的位置（只能有一个）、扩展部分只能出现 punycode 数字、末尾不能有多余字符。
- 不变量：`decode_label(encode_label(x)) == x`（任意 Unicode 文本）；纯 ASCII 标签编解码后原样；
  空串返回空串；同一输入重复编解码结果相同。
- 规模：1 MB 文本单遍编解码，内存 O(标签长度)。

## 现在的行为

- `encode_label` 拼完基本码点之后直接接扩展部分，**没有写 `-`**：`bücher` 给 `bcherkva`。
- `adapt` 忽略入参、固定返回 72：短的标签（如 `mnchen-3ya`）解码碰巧正确，
  但 `wgv71a119e`（`日本語`）解出来是乱码，编码长文本时扩展部分的数字也会算错。
- `decode_label` 不校验尾随 `-`、不校验扩展部分是否合法、也不检查多余的 `-`。

## 计划新增的能力

```
--encode 文本    编成 punycode 标签
--decode 标签    解码
```

## 输出

```
punycode 标签 / 原文
```

## 目录

```
puny/codec.py   编解码与偏置自适应
puny/cli.py     命令行入口
tests/          unittest 用例
```
