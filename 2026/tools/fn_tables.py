"""在每個 Python 程式區塊上方產生「函式名稱／說明／官方文件連結」表格。

    python3 tools/fn_tables.py docs     # （需連網）從官方 objects.inv 找出每個條目的文件網址，逐一實測後寫入 tools/fn_docs.json
    python3 tools/fn_tables.py check    # 列出每個區塊會產生的表格與未登錄的函式，不改檔
    python3 tools/fn_tables.py apply    # 改寫 01–18 講義：移除舊表格、重新插入

怎麼決定一個區塊要列哪些函式：
1. 把每節的完整 Demo 加上探針實際執行，記下每一個屬性存取、呼叫、索引、比較與運算的「接收者型別」。
   `df.sum()` 與 `s.sum()` 因此能分辨，不靠猜。
2. 節錄（`<!-- 節錄 -->`）依它在 Demo 中的位置對應行號；其他片段逐行比對 Demo，對不上的行用全課觀察到的型別推定。
3. 依 tools/fn_catalog.py 的 MERGE 合併同義條目、略過 FAMILIAR（前置課程學過的）。
4. 全課依 01→18、區塊由上而下的順序：第一次出現的函式各一列；之前介紹過的併成最後一列「前面介紹過」。
   第 01 節是預覽（講義寫「語法從第 02 節開始」）：表格完整列出，但不算第一次介紹，02 節起重新計。

講義是唯一原稿；表格由本程式產生，測試會重新產生並比對，所以改了 Demo 就要重跑 `apply`。
"""
import ast
import builtins
import io
import json
import operator
import re
import sys
import types as _types
import warnings
import zlib
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import fn_catalog as C  # noqa: E402

DOCS_FILE = HERE / "fn_docs.json"
MARK = "<!-- fn-table -->"
HEADER = "| 函式名稱 | 說明 | 官方文件連結 |"
FENCE = re.compile(r"^( *)```python\n(.*?)^\1```[ \t]*$", re.S | re.M)
DEMO = re.compile(r"<!-- demo: ([\w.]+) -->\n```python\n(.*?)\n```", re.S)
TABLE = re.compile(r"^( *)" + re.escape(MARK) + r"\n(?:\1\|[^\n]*\n)+\n", re.M)

TYPEMAP = {
    "pandas.Series": ["pandas.Series"], "pandas.DataFrame": ["pandas.DataFrame"],
    "pandas.core.strings.accessor.StringMethods": ["pandas.Series.str"],
    "pandas.core.indexes.accessors.DatetimeProperties": ["pandas.Series.dt"],
    "pandas.core.indexes.accessors.CombinedDatetimelikeProperties": ["pandas.Series.dt"],
    "pandas.core.indexes.accessors.TimedeltaProperties": ["pandas.Series.dt"],
    "pandas.api.typing.DataFrameGroupBy": ["pandas.api.typing.DataFrameGroupBy"],
    "pandas.api.typing.SeriesGroupBy": ["pandas.api.typing.SeriesGroupBy"],
    "pandas.api.typing.DatetimeIndexResampler": ["pandas.api.typing.Resampler"],
    "pandas.api.typing.Resampler": ["pandas.api.typing.Resampler"],
    "pandas.core.resample.DatetimeIndexResampler": ["pandas.api.typing.Resampler"],
    "pandas.Index": ["pandas.Index"], "pandas.RangeIndex": ["pandas.RangeIndex", "pandas.Index"],
    "pandas.DatetimeIndex": ["pandas.DatetimeIndex", "pandas.Index"],
    "pandas.MultiIndex": ["pandas.MultiIndex", "pandas.Index"], "pandas.PeriodIndex": ["pandas.PeriodIndex", "pandas.Index"],
    "pandas.Timestamp": ["pandas.Timestamp"], "pandas.Timedelta": ["pandas.Timedelta"],
    "pandas.arrays.StringArray": ["pandas.arrays.StringArray", "pandas.api.extensions.ExtensionArray"],
    "pandas.arrays.ArrowStringArray": ["pandas.api.extensions.ExtensionArray"],
    "builtins.str": ["str"], "builtins.bytes": ["bytes"], "builtins.dict": ["dict"], "builtins.list": ["list"],
    "builtins.set": ["set"], "pathlib.PosixPath": ["pathlib.Path", "pathlib.PurePath"],
    "_hashlib.HASH": ["hashlib.hash"], "collections.deque": ["collections.deque"],
    "collections.defaultdict": ["collections.defaultdict", "dict"], "sqlite3.Connection": ["sqlite3.Connection"],
    "datetime.timedelta": ["datetime.timedelta"], "datetime.datetime": ["datetime.datetime"], "datetime.date": ["datetime.date"],
    "numpy.ndarray": ["numpy.ndarray"], "_io.StringIO": ["io.StringIO"], "re.Pattern": ["re.Pattern"],
    "builtins.UnicodeDecodeError": ["UnicodeError"],
}
# 這些型別上的屬性不列表（itertuples 的列欄位、警告物件、例外）
IGNORE_TYPES = {"pandas.core.frame.Pandas", "warnings.WarningMessage", "pandas.errors.DatabaseError",
                "sqlite3.IntegrityError", "builtins.ValueError"}
FAMILIAR_MODULES = {"mariadb", "os", "sys", "time", "csv"}
# 沒執行到的行，若全課觀察到不只一種對應，就用這裡的預設
PREFER = {"agg": "pandas.api.typing.DataFrameGroupBy.agg", "describe": "pandas.DataFrame.describe",
          "size": "pandas.api.typing.DataFrameGroupBy.size", "first": "pandas.api.typing.SeriesGroupBy.first",
          "mean": "pandas.Series.mean", "max": "pandas.Series.max", "min": "pandas.Series.min",
          "nunique": "pandas.Series.nunique", "values": "pandas.DataFrame.values", "count": "pandas.Series.str.count",
          "replace": "pandas.Series.replace", "split": "pandas.Series.str.split", "get": "pandas.Series.get",
          "strftime": "pandas.Series.dt.strftime", "dayofweek": "pandas.Series.dt.dayofweek",
          "total_seconds": "pandas.Series.dt.total_seconds", "isascii": "str.isascii", "isdigit": "str.isdigit",
          "fromisoformat": "datetime.datetime.fromisoformat", "contains": "pandas.Series.str.contains",
          "startswith": "pandas.Series.str.startswith", "endswith": "pandas.Series.str.endswith",
          "join": "str.join", "items": "pandas.Series.items", "len": "pandas.Series.str.len",
          "match": "pandas.Series.str.match", "copy": "pandas.DataFrame.copy", "round": "pandas.DataFrame.round",
          "sum": "pandas.Series.sum", "read": None, "category": None, "to_period": "pandas.Series.dt.to_period"}
PANDASY = {"pandas.Series", "pandas.DataFrame"}


def locate_excerpt(code, snippet):
    """同 test_lessons.locate_excerpt：節錄可以是主程式去掉 4 格縮排後的樣子。"""
    for indent in ("", "    ", "        "):
        shifted = "\n".join(indent + line if line.strip() else line for line in snippet.split("\n"))
        i = code.find(shifted)
        if i >= 0 and (i == 0 or code[i - 1] == "\n"):
            return code[:i].count("\n"), indent
    return None


def canon(key):
    return C.CANON.get(key, key)


def known(key):
    k = canon(key)
    return k in C.ENTRIES or k in C.FAMILIAR or k in C.SKIP or key in C.FAMILIAR


def blocks(text):
    """回傳每個 python 區塊：(縮排, 程式碼, 區塊開頭位置, 種類, 節錄插入點)。"""
    out = []
    for m in FENCE.finditer(text):
        ind = m.group(1)
        code = "\n".join(line[len(ind):] if line.startswith(ind) else line for line in m.group(2).rstrip("\n").split("\n"))
        before = text[:m.start()]
        prev = before.rstrip("\n").split("\n")[-1].strip()
        kind = "demo" if prev.startswith("<!-- demo:") else "excerpt" if prev.startswith("<!-- 節錄") else "snippet"
        start = m.start()
        if kind != "snippet":
            start = before.rstrip("\n").rfind("\n") + 1
        out.append(dict(indent=ind, code=code, start=start, kind=kind))
    return out


# ---------------------------------------------------------------- 執行探針

_PUBLIC = None


def _public_names():
    """pandas 2 與 3 的類別 __module__ 不同（pandas.core.frame.DataFrame vs pandas.DataFrame）。
    依類別物件本身對應到公開名稱，兩個版本產生相同的表格。"""
    global _PUBLIC
    if _PUBLIC is None:
        import pandas as pd
        from pandas.api import typing as pt
        _PUBLIC = {}
        for name in ("Series", "DataFrame", "Index", "RangeIndex", "DatetimeIndex", "MultiIndex", "PeriodIndex",
                     "Timestamp", "Timedelta"):
            _PUBLIC[getattr(pd, name)] = f"pandas.{name}"
        for name in ("DataFrameGroupBy", "SeriesGroupBy", "DatetimeIndexResampler", "Resampler"):
            if hasattr(pt, name):
                _PUBLIC[getattr(pt, name)] = f"pandas.api.typing.{name}"
        for cls in (type(pd.Series(["a"]).str), type(pd.Series(pd.to_datetime(["2026-01-01"])).dt),
                    type(pd.Series(pd.to_timedelta([1], unit="s")).dt)):
            _PUBLIC[cls] = {"StringMethods": "pandas.core.strings.accessor.StringMethods"}.get(
                cls.__name__, "pandas.core.indexes.accessors.DatetimeProperties")
        for cls in (type(pd.array(["a"], dtype="string")), type(pd.Series(["a"], dtype="str").array)):
            _PUBLIC[cls] = "pandas.arrays.StringArray"
    return _PUBLIC


def tname(x):
    if isinstance(x, _types.ModuleType):
        return "module:" + x.__name__
    if isinstance(x, type):
        return "class:" + _public_names().get(x, f"{x.__module__}.{x.__qualname__}")
    t = type(x)
    pub = _public_names()
    for c in t.__mro__:
        if c in pub:
            return pub[c]
    return f"{t.__module__}.{t.__qualname__}"


class _Probe(ast.NodeTransformer):
    def visit_Attribute(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load):
            return ast.copy_location(ast.Call(ast.Name("__pa", ast.Load()),
                                              [node.value, ast.Constant(node.attr), ast.Constant(node.lineno)], []), node)
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name):
            node.func = ast.copy_location(ast.Call(ast.Name("__pn", ast.Load()),
                                                   [node.func, ast.Constant(node.func.id), ast.Constant(node.lineno)], []), node.func)
        return node

    def visit_Subscript(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load):
            return ast.copy_location(ast.Call(ast.Name("__sl", ast.Load()),
                                              [node.value, self._key(node.slice), ast.Constant(node.lineno)], []), node)
        node.value = ast.copy_location(ast.Call(ast.Name("__ps", ast.Load()),
                                                [node.value, ast.Constant(node.lineno)], []), node.value)
        return node

    def _key(self, s):
        if isinstance(s, ast.Slice):
            return ast.Call(ast.Name("slice", ast.Load()), [s.lower or ast.Constant(None), s.upper or ast.Constant(None),
                                                            s.step or ast.Constant(None)], [])
        if isinstance(s, ast.Tuple):
            return ast.Tuple([self._key(e) for e in s.elts], ast.Load())
        return s

    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1 and not isinstance(node.ops[0], (ast.In, ast.NotIn, ast.Is, ast.IsNot)):
            return ast.copy_location(ast.Call(ast.Name("__pc", ast.Load()),
                                              [node.left, node.comparators[0], ast.Constant(type(node.ops[0]).__name__),
                                               ast.Constant(node.lineno)], []), node)
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        name = type(node.op).__name__
        if name in _ARI or name in ("BitAnd", "BitOr"):
            return ast.copy_location(ast.Call(ast.Name("__pr", ast.Load()),
                                              [node.left, node.right, ast.Constant(name), ast.Constant(node.lineno)], []), node)
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Invert):
            return ast.copy_location(ast.Call(ast.Name("__pu", ast.Load()), [node.operand, ast.Constant(node.lineno)], []), node)
        return node


_CMP = {"Eq": operator.eq, "NotEq": operator.ne, "Lt": operator.lt, "LtE": operator.le, "Gt": operator.gt, "GtE": operator.ge}
_ARI = {"Add": operator.add, "Sub": operator.sub, "Mult": operator.mul, "Div": operator.truediv, "Mod": operator.mod,
        "FloorDiv": operator.floordiv, "BitAnd": operator.and_, "BitOr": operator.or_}


def run_demo(lesson_path):
    """執行 Demo，回傳 {行號: [(類別, 接收者型別, 名稱)]}；行號是 Demo 程式碼內的行號。"""
    import pandas as pd
    text = lesson_path.read_text(encoding="utf-8")
    name, src = DEMO.findall(text)[0]
    obs = {}

    def add(line, item):
        obs.setdefault(line, set()).add(item)

    def keykind(k):
        if isinstance(k, (pd.Series, pd.Index)) and k.dtype == bool:
            return "mask"
        if callable(k):
            return "mask"
        if isinstance(k, str):
            return "label"
        if isinstance(k, (list, pd.Index)):
            return "labels"
        if isinstance(k, slice):
            return "slice"
        if isinstance(k, int):
            return "int"
        return "other"

    def pa(v, attr, line):
        r = getattr(v, attr)
        add(line, ("attr", tname(v), attr, isinstance(r, _types.ModuleType)))
        return r

    def pn(f, ident, line):
        if isinstance(f, type) and f in _public_names():
            add(line, ("name", _public_names()[f], ident, False))
            return f
        mod = getattr(f, "__module__", None) or ""
        qn = getattr(f, "__qualname__", None) or getattr(f, "__name__", ident)
        add(line, ("name", f"{mod}.{qn}", ident, False))
        return f

    def sl(v, k, line):
        add(line, ("sub", tname(v), keykind(k), False))
        return v[k]

    def ps(v, line):
        add(line, ("store", tname(v), "", False))
        return v

    def pc(a, b, op, line):
        add(line, ("cmp", tname(a), tname(b), False))
        return _CMP[op](a, b)

    def pr(a, b, op, line):
        add(line, ("bool" if op in ("BitAnd", "BitOr") else "ari", tname(a), tname(b), False))
        return _ARI[op](a, b)

    def pu(a, line):
        add(line, ("bool", tname(a), "", False))
        return ~a

    tree = _Probe().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    g = {"__name__": "__main__", "__file__": str(lesson_path.parent / name), "__pa": pa, "__pn": pn, "__sl": sl,
         "__ps": ps, "__pc": pc, "__pr": pr, "__pu": pu}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with redirect_stdout(io.StringIO()):
            exec(compile(tree, name, "exec"), g)
    return src, obs


# ---------------------------------------------------------------- 對應到條目

def attr_key(typ, attr, is_module):
    """回傳 (key 或 None, 錯誤訊息或 None)。"""
    if attr.startswith("__") or is_module:
        return None, None
    if typ.startswith("module:"):
        owners = [typ[7:]]
        if typ[7:].split(".")[0] in FAMILIAR_MODULES:
            return None, None
    elif typ.startswith("class:"):
        owners = [typ[6:]]
    elif typ in IGNORE_TYPES:
        return None, None
    else:
        owners = TYPEMAP.get(typ)
        if owners is None:
            return None, f"未知型別 {typ}.{attr}"
    for o in owners:
        if known(f"{o}.{attr}"):
            return f"{o}.{attr}", None
    return None, f"未登錄 {owners[0]}.{attr}"


def name_key(qual, ident):
    if qual.startswith("__main__.") or qual.startswith("my_"):
        return None, None
    if qual.startswith("builtins."):
        k = qual
        return (k if known(k) else None), None
    if known(qual):
        return qual, None
    if qual.split(".")[0] in FAMILIAR_MODULES:
        return None, None
    return None, f"未登錄呼叫 {qual}（{ident}）"


def obs_key(item):
    """一個觀察結果 → (key 或 None, 錯誤或 None)。"""
    kind, typ, x, flag = item
    if kind == "attr":
        return attr_key(typ, x, flag)
    if kind == "name":
        return name_key(typ, x)
    if kind == "sub":
        if typ == "pandas.DataFrame":
            return ("syntax:mask" if x == "mask" else "syntax:col"), None
        if typ == "pandas.Series":
            return ("syntax:mask" if x == "mask" else "syntax:label"), None
        if typ == "pandas.core.strings.accessor.StringMethods":
            return "syntax:strslice", None
    if kind == "store" and typ == "pandas.DataFrame":
        return "syntax:col", None
    if kind == "cmp" and (typ in PANDASY or x in PANDASY):
        return "syntax:mask", None
    if kind == "bool" and typ in PANDASY | {"numpy.ndarray"}:
        return "syntax:boolops", None
    if kind == "ari" and (typ in PANDASY or x in PANDASY):
        return "syntax:vector", None
    return None, None


def obs_keys(items):
    return [obs_key(it) for it in items]


class Course:
    def __init__(self, root=ROOT):
        self.root = root
        self.lessons = sorted(p for p in root.glob("[0-1][0-9]-*.md"))
        self.runs = {p.name: run_demo(p) for p in self.lessons}
        # 全課：屬性名 → 觀察到的 key；呼叫名 → key；被觀察為 DataFrame/Series 的變數名
        self.by_attr, self.by_name = {}, {}
        for src, obs in self.runs.values():
            for items in obs.values():
                for it in items:
                    k, _ = obs_key(it)
                    if k and it[0] == "attr":
                        self.by_attr.setdefault(it[2], set()).add(canon(k))
                    if k and it[0] == "name":
                        self.by_name.setdefault(it[2], set()).add(canon(k))
        self.frames = self._frame_names()

    def _frame_names(self):
        names = set()
        for src, obs in self.runs.values():
            tree = ast.parse(src)
            lines = {}
            for n in ast.walk(tree):
                if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):
                    lines.setdefault(n.lineno, set()).add(n.value.id)
            for ln, items in obs.items():
                if any(k == "sub" and t in PANDASY for k, t, _, _ in items):
                    names |= lines.get(ln, set())
        return names

    # ---- 靜態推定（沒執行到的行）
    def static_keys(self, code_line_nodes, defined, modules, lesson="", line=""):
        out = []
        for n in code_line_nodes:
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load) and not n.attr.startswith("__"):
                hit = [k for (les, attr, sub), k in C.STATIC_OVERRIDE.items() if les == lesson and attr == n.attr and sub in line]
                if hit:
                    out.append((hit[0], None))
                    continue
                if isinstance(n.value, ast.Name) and n.value.id in modules:
                    mod = modules[n.value.id]
                    if mod.split(".")[0] in FAMILIAR_MODULES:
                        continue
                    k = f"{mod}.{n.attr}"
                    out.append((k, None) if known(k) else (None, f"未登錄 {k}"))
                    continue
                if n.attr in ("str", "dt"):
                    continue
                recv = n.value
                while isinstance(recv, ast.Subscript):
                    recv = recv.value
                if (isinstance(recv, ast.Constant) and isinstance(recv.value, str)) or isinstance(recv, ast.JoinedStr) or (
                        isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id in ("str", "repr")):
                    k = f"str.{n.attr}"     # 接收者明顯是 Python 字串，例如 str(exc).split(...)
                    out.append((k if known(k) else None, None))
                    continue
                cands = self.by_attr.get(n.attr, set())
                if n.attr in PREFER:
                    if PREFER[n.attr]:
                        out.append((PREFER[n.attr], None))
                elif len(cands) == 1:
                    out.append((next(iter(cands)), None))
                elif not cands:
                    out.append((None, f"沒執行到、也無法推定的屬性 .{n.attr}"))
                else:
                    out.append((None, f"無法唯一推定 .{n.attr}：{sorted(cands)}"))
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                ident = n.func.id
                if ident in defined or ident in self.locals_:
                    continue
                if hasattr(builtins, ident):
                    k = f"builtins.{ident}"
                    out.append((k if known(k) else None, None))
                elif ident in self.by_name:
                    out.append((next(iter(self.by_name[ident])), None))
                elif ident in modules:
                    k = modules[ident]
                    if k.split(".")[0] in FAMILIAR_MODULES:
                        continue
                    out.append((k, None) if known(k) else (None, f"未登錄 {k}"))
                else:
                    out.append((None, f"無法推定的呼叫 {ident}()"))
            elif isinstance(n, ast.Subscript):
                root = n.value
                while isinstance(root, (ast.Subscript, ast.Attribute, ast.Call)):
                    root = root.value if not isinstance(root, ast.Call) else root.func
                if isinstance(n.value, ast.Attribute) and n.value.attr == "str":
                    out.append(("syntax:strslice", None))
                elif isinstance(n.value, ast.Attribute) and n.value.attr in ("loc", "iloc"):
                    continue
                elif isinstance(root, ast.Name) and root.id in self.frames:
                    sl = n.slice
                    mask = isinstance(sl, (ast.Compare, ast.BinOp, ast.UnaryOp, ast.Call)) or (
                        isinstance(sl, ast.Name) and sl.id in ("mask", "bad", "dup", "keep", "ok", "late"))
                    out.append(("syntax:mask" if mask else "syntax:col", None))
            elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.BitAnd, ast.BitOr)) or (
                    isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Invert)):
                out.append(("syntax:boolops", None))
        return out

    def block_keys(self, lesson, block):
        """回傳 [(key, 第幾行)]（依出現順序、去重）與錯誤清單。"""
        src, obs = self.runs[lesson]
        demo_lines = src.split("\n")
        code = block["code"]
        tree = ast.parse(code)
        self.locals_ = set()
        for t in (ast.parse(src), tree):
            for n in ast.walk(t):
                if isinstance(n, ast.arg):
                    self.locals_.add(n.arg)
                elif isinstance(n, (ast.For, ast.comprehension)) and isinstance(n.target, ast.Name):
                    self.locals_.add(n.target.id)
        defined = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        defined |= {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        modules = {"pd": "pandas", "np": "numpy"}
        for t in (ast.parse(src), tree):
            for n in ast.walk(t):
                if isinstance(n, ast.Import):
                    for a in n.names:
                        modules[a.asname or a.name] = a.name
                elif isinstance(n, ast.ImportFrom) and n.module:
                    for a in n.names:
                        if n.module.startswith("my_"):
                            defined.add(a.asname or a.name)
                        else:
                            modules[a.asname or a.name] = f"{n.module}.{a.name}"
        if block["kind"] == "demo":
            offset = 0
        elif block["kind"] == "excerpt":
            loc = locate_excerpt(src, code)
            if loc is None:
                return [], [f"{lesson}：節錄與 Demo 不一致"]
            offset = loc[0]
        else:
            offset = None
        nodes_by_line = {}
        for n in ast.walk(tree):
            if hasattr(n, "lineno"):
                nodes_by_line.setdefault(n.lineno, []).append(n)
        found, errors = [], []
        for ln, line in enumerate(code.split("\n"), 1):
            dl = None
            if offset is not None:
                dl = ln + offset
            elif line.strip():
                hits = [i + 1 for i, d in enumerate(demo_lines) if d.strip() == line.strip()]
                dl = hits[0] if hits else None
            line_nodes = nodes_by_line.get(ln, [])
            if dl in obs:
                got = obs_keys(sorted(obs[dl]))
                # 執行到的行：只替「執行時完全沒碰到的屬性名」補靜態推定（例如 raise 訊息裡的屬性）
                seen_attrs = {it[2] for it in obs[dl] if it[0] == "attr"}
                rest = [n for n in line_nodes if isinstance(n, ast.Attribute) and n.attr not in seen_attrs]
                got = got + [(k, e) for k, e in self.static_keys(rest, defined, modules, lesson, line) if k]
            else:
                got = self.static_keys(line_nodes, defined, modules, lesson, line)
            for k, err in got:
                if err:
                    errors.append(f"{lesson} 第 {ln} 行：{err}")
                elif k:
                    found.append((canon(k), ln))
        for (les, needle), extra in C.EXTRA.items():
            if les == lesson and needle in code:
                found += [(k, 0) for k in extra]
        keys = []
        for k, ln in found:
            if k in C.SKIP or k in C.FAMILIAR or k not in C.ENTRIES:
                if k not in C.ENTRIES and k not in C.SKIP and k not in C.FAMILIAR and not k.startswith("builtins."):
                    errors.append(f"{lesson}：條目缺少說明 {k}")
                continue
            if k not in [x for x, _ in keys]:
                keys.append((k, ln))
        return keys, errors


# ---------------------------------------------------------------- 產生表格

def short(key):
    disp = C.ENTRIES[key][0]
    if key in C.SHORT:
        return C.SHORT[key]
    first = disp.split("／")[0].strip("`")
    for cut in ("(", "["):
        if cut in first:
            first = first[:first.index(cut)] + ("()" if cut == "(" else "[]")
            break
    return first


def cell(s):
    return s.replace("|", "\\|")


def render(rows, back, docs, indent):
    lines = [MARK, HEADER, "|---|---|---|"]
    if rows is None:
        lines.append("| （同上） | 這支程式用到的函式，都已在上面各段的表格介紹過 | — |")
        return "".join(indent + ln + "\n" for ln in lines) + "\n"
    for k in rows:
        disp, desc = C.ENTRIES[k]
        lines.append(f"| {cell(disp)} | {cell(desc)} | [文件]({docs[k]}) |")
    if back:
        links = "、".join(f"[`{cell(short(k))}`]({docs[k]})（{n}）" for k, n in back)
        lines.append(f"| 前面介紹過 | 用法同前，括號內是在哪裡第一次介紹 | {links} |")
    if not rows and not back:
        lines.append("| （無） | 本段只用到 Python 基礎與前幾門課學過的寫法，沒有新的函式 | — |")
    return "".join(indent + ln + "\n" for ln in lines) + "\n"


def plan(course=None):
    course = course or Course()
    docs = json.loads(DOCS_FILE.read_text(encoding="utf-8")) if DOCS_FILE.exists() else {}
    first, out, errors = {}, {}, []
    for p in course.lessons:
        text = TABLE.sub("", p.read_text(encoding="utf-8"))
        nn = p.name[:2]
        tables = []
        all_blocks = blocks(text)
        stepwise = any(b["kind"] == "excerpt" for b in all_blocks) and C.STEPWISE(p.name)
        for b in all_blocks:
            if stepwise and b["kind"] == "demo":
                tables.append((b, None, None))      # 逐段教過了：附錄完整程式只放一句話
                continue
            keys, errs = course.block_keys(p.name, b)
            errors += errs
            new = [k for k, _ in keys if k not in first and k not in C.PRIOR]
            if nn not in C.PREVIEW_LESSONS:     # 第 01 節只是預覽：照列，但不算「第一次介紹」
                for k in new:
                    first[k] = nn
            back = [(k, C.PRIOR.get(k) or f"第 {first[k]} 節") for k, _ in keys if k not in new]
            # 依「在哪裡介紹」再依短名排序：不受同一行內觀察順序影響（pandas 2／3 結果相同）
            back.sort(key=lambda kv: (not kv[1].startswith("第"), kv[1], short(kv[0])))
            missing = [k for k in new + [k for k, _ in back] if k not in docs]
            errors += [f"{p.name}：沒有已驗證的文件網址 {k}" for k in missing]
            tables.append((b, new, back))
        out[p.name] = (text, tables)
    return out, docs, errors


def build(text, tables, docs):
    parts, last = [], 0
    for b, new, back in tables:
        parts.append(text[last:b["start"]])
        if not parts[-1].endswith("\n\n"):
            parts.append("\n")
        parts.append(render(new, back, docs, b["indent"]))
        last = b["start"]
    parts.append(text[last:])
    return "".join(parts)


# ---------------------------------------------------------------- 官方文件網址

INVENTORIES = [("https://pandas.pydata.org/docs/", "objects.inv"), ("https://docs.python.org/3.12/", "objects.inv"),
               ("https://numpy.org/doc/stable/", "objects.inv")]


def read_inventory(raw, base):
    lines = raw.split(b"\n", 4)
    body = zlib.decompress(lines[4]).decode("utf-8")
    out = {}
    for line in body.splitlines():
        m = re.match(r"(.+?)\s+py:(\S+)\s+(-?\d+)\s+(\S*)\s+(.*)$", line)
        if m:
            name, uri = m.group(1), m.group(4)
            if uri.endswith("$"):
                uri = uri[:-1] + name
            out.setdefault(name, base + uri)
    return out


def fetch(url):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "4-learn course link check"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read(), r.geturl()


def verify(urls):
    """每個網址：HTTP 200、最終網址與原網址同頁（沒有被轉走）、錨點 id 存在於頁面。"""
    pages, bad = {}, []
    for url in sorted(set(urls)):
        page, _, anchor = url.partition("#")
        if page not in pages:
            try:
                status, body, final = fetch(page)
                pages[page] = (status, body.decode("utf-8", "replace"), final)
            except Exception as exc:  # noqa: BLE001
                pages[page] = (str(exc), "", "")
        status, body, final = pages[page]
        if status != 200 or final.split("#")[0] != page:
            bad.append(f"{url}：{status} {final}")
        elif anchor and f'id="{anchor}"' not in body:
            bad.append(f"{url}：頁面沒有錨點 {anchor}")
    return bad


def cmd_docs():
    inv = {}
    for base, f in INVENTORIES:
        _, raw, _ = fetch(base + f)
        for k, v in read_inventory(raw, base).items():
            inv.setdefault(k, v)
    docs, missing = {}, []
    for k in C.ENTRIES:
        if k in C.MANUAL_DOCS:
            docs[k] = C.MANUAL_DOCS[k]
        elif k in inv:
            docs[k] = inv[k]
        else:
            missing.append(k)
    if missing:
        raise SystemExit(f"官方 inventory 找不到：{missing}（請在 fn_catalog.MANUAL_DOCS 補）")
    bad = verify(docs.values())
    if bad:
        raise SystemExit("網址驗證失敗：\n" + "\n".join(bad))
    DOCS_FILE.write_text(json.dumps(docs, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(docs)} 個網址全部驗證通過 → {DOCS_FILE.name}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "docs":
        return cmd_docs()
    out, docs, errors = plan()
    if errors:
        print("\n".join(sorted(set(errors))))
        if cmd == "apply":
            raise SystemExit("有錯誤，未改檔")
    for name, (text, tables) in out.items():
        new = build(text, tables, docs) if not errors or cmd == "check" and docs else None
        if cmd == "check":
            for b, nw, back in tables:
                if nw is None:
                    print(f"{name[:2]} {b['kind']:8} （同上）")
                    continue
                print(f"{name[:2]} {b['kind']:8} 新 {len(nw):2} 前面 {len(back):2}  {[short(k) for k in nw]}")
        elif cmd == "apply":
            (ROOT / name).write_text(new, encoding="utf-8")
    if cmd == "apply":
        print("已更新", len(out), "篇")


if __name__ == "__main__":
    main()
