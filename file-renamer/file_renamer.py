"""
文件名管理工具 v2.0.0
Tab1: 通用重命名  Tab2: 后缀批量修改  Tab3: 字幕配对
依赖: pip install tkinterdnd2
Python 3.12 / tkinter 内置
"""

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil, re
from pathlib import Path

# ─────────────────────────────────────────────
#  配色
# ─────────────────────────────────────────────
BG         = "#F7F6F3"
PANEL      = "#FFFFFF"
BORDER     = "#E0DED7"
TEXT       = "#1A1A18"
MUTED      = "#6B6A66"
ACCENT     = "#1A1A18"
SUCCESS    = "#3B6D11"
SUCCESS_BG = "#EAF3DE"
ERR        = "#A32D2D"
ERR_BG     = "#FCEBEB"
WARN_BG    = "#FAEEDA"
WARN       = "#854F0B"
INFO_BG    = "#F1EFE8"
BTN_H      = "#ECEAE3"
DROP_HL    = "#D0E8FF"
SEL_BG     = "#E6F1FB"

ENTRY_CFG = dict(
    bg=BG, fg=TEXT, relief="flat",
    highlightthickness=1, highlightbackground=BORDER,
    highlightcolor=ACCENT, insertbackground=TEXT,
    font=("Segoe UI", 10), bd=0
)

# ─────────────────────────────────────────────
#  集数提取正则（通用）
# ─────────────────────────────────────────────
EP_PATTERNS = [
    re.compile(r'\[(\d{1,4})\]'),                      # [01]
    re.compile(r'[Ee](\d{1,4})'),                       # E01 e01
    re.compile(r'[Ss]\d{1,2}[Ee](\d{1,4})'),           # S01E01
    re.compile(r'第(\d{1,4})[话集話]'),                  # 第01话
    re.compile(r'[ _\-](\d{1,4})[ _\-\.]'),            # _01_ -01-
    re.compile(r'(\d{1,4})$'),                          # 末尾纯数字
]

def extract_episode(name: str) -> int | None:
    stem = Path(name).stem
    for pat in EP_PATTERNS:
        m = pat.search(stem)
        if m:
            return int(m.group(1))
    return None

# ─────────────────────────────────────────────
#  公共小部件
# ─────────────────────────────────────────────
def make_entry(parent, width=20, placeholder="", **kw) -> tk.Entry:
    e = tk.Entry(parent, width=width, **ENTRY_CFG, **kw)
    if placeholder:
        e.insert(0, placeholder)
        e.config(fg=MUTED)
        def _fi(ev, ph=placeholder):
            if e.get() == ph:
                e.delete(0, "end"); e.config(fg=TEXT)
        def _fo(ev, ph=placeholder):
            if not e.get().strip():
                e.insert(0, ph); e.config(fg=MUTED)
        e.bind("<FocusIn>",  _fi)
        e.bind("<FocusOut>", _fo)
    return e

def accent_btn(parent, text, cmd, **kw):
    return tk.Button(parent, text=text, command=cmd,
                     bg=ACCENT, fg="#FFF", relief="flat",
                     activebackground="#333330", activeforeground="#FFF",
                     font=("Segoe UI", 10, "bold"), cursor="hand2",
                     padx=14, pady=5, **kw)

def plain_btn(parent, text, cmd, **kw):
    return tk.Button(parent, text=text, command=cmd,
                     bg=BG, fg=MUTED, relief="flat",
                     activebackground=BTN_H, activeforeground=TEXT,
                     font=("Segoe UI", 10), cursor="hand2",
                     padx=10, pady=5, **kw)

def section_frame(parent, title):
    outer = tk.Frame(parent, bg=BG)
    outer.pack(fill="x", padx=16, pady=(10, 0))
    panel = tk.Frame(outer, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
    panel.pack(fill="x")
    tk.Label(panel, text=title, bg=PANEL, fg=MUTED,
             font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(8, 0))
    inner = tk.Frame(panel, bg=PANEL)
    inner.pack(fill="x", padx=12, pady=(4, 10))
    return inner

def expand_section(parent, title):
    """可纵向扩展的 section（用于日志区）"""
    outer = tk.Frame(parent, bg=BG)
    outer.pack(fill="both", expand=True, padx=16, pady=(10, 10))
    panel = tk.Frame(outer, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
    panel.pack(fill="both", expand=True)
    tk.Label(panel, text=title, bg=PANEL, fg=MUTED,
             font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(8, 0))
    inner = tk.Frame(panel, bg=PANEL)
    inner.pack(fill="both", expand=True, padx=12, pady=(4, 10))
    return inner

# ─────────────────────────────────────────────
#  拖拽区
# ─────────────────────────────────────────────
class DropZone(tk.Frame):
    def __init__(self, parent, on_drop, label="将文件或文件夹拖拽到此处", **kw):
        super().__init__(parent, bg=PANEL,
                         highlightthickness=1, highlightbackground=BORDER, **kw)
        self._on_drop = on_drop
        self._lbl = tk.Label(self,
            text=label if DND_AVAILABLE else "拖拽不可用 — pip install tkinterdnd2",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 10), pady=10)
        self._lbl.pack(fill="x")
        if DND_AVAILABLE:
            for w in (self, self._lbl):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>",      self._drop)
                w.dnd_bind("<<DragEnter>>", self._enter)
                w.dnd_bind("<<DragLeave>>", self._leave)

    def _enter(self, e):
        self.config(bg=DROP_HL, highlightbackground="#5AABF0")
        self._lbl.config(bg=DROP_HL, fg="#185FA5")

    def _leave(self, e):
        self.config(bg=PANEL, highlightbackground=BORDER)
        self._lbl.config(bg=PANEL, fg=MUTED)

    def _drop(self, e):
        self._leave(e)
        result = []
        for p in self._parse(e.data):
            pp = Path(p)
            if pp.is_file():   result.append(pp)
            elif pp.is_dir():  result.extend(f for f in pp.rglob("*") if f.is_file())
        if result: self._on_drop(result)

    @staticmethod
    def _parse(data):
        paths, data = [], data.strip()
        while data:
            if data.startswith("{"):
                end = data.index("}")
                paths.append(data[1:end]); data = data[end+1:].strip()
            else:
                p = data.split(" ", 1)
                paths.append(p[0]); data = p[1].strip() if len(p) > 1 else ""
        return paths

# ─────────────────────────────────────────────
#  日志 Mixin
# ─────────────────────────────────────────────
class LogMixin:
    def _init_log(self, parent):
        inner = expand_section(parent, "日志")
        btn_row = tk.Frame(inner, bg=PANEL)
        btn_row.pack(fill="x", pady=(0, 6))
        self._exec_btn = accent_btn(btn_row, "执行", self._execute)
        self._exec_btn.pack(side="left", padx=(0, 8))
        plain_btn(btn_row, "清空日志", self._clear_log).pack(side="left")

        log_wrap = tk.Frame(inner, bg=PANEL)
        log_wrap.pack(fill="both", expand=True)
        self._log_w = tk.Text(log_wrap, height=8, state="disabled",
                              bg=INFO_BG, fg=TEXT, relief="flat",
                              font=("Consolas", 9), wrap="word",
                              highlightthickness=0, bd=0)
        self._log_w.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(log_wrap, command=self._log_w.yview)
        sb.pack(side="right", fill="y")
        self._log_w.config(yscrollcommand=sb.set)
        self._log_w.tag_config("ok",   foreground=SUCCESS, background=SUCCESS_BG)
        self._log_w.tag_config("err",  foreground=ERR,     background=ERR_BG)
        self._log_w.tag_config("warn", foreground=WARN,    background=WARN_BG)
        self._log_w.tag_config("info", foreground=MUTED)
        self._log_w.tag_config("head", foreground=TEXT, font=("Consolas", 9, "bold"))

    def log(self, msg, tag="info"):
        self._log_w.config(state="normal")
        self._log_w.insert("end", msg + "\n", tag)
        self._log_w.see("end")
        self._log_w.config(state="disabled")

    def _clear_log(self):
        self._log_w.config(state="normal")
        self._log_w.delete("1.0", "end")
        self._log_w.config(state="disabled")

    def _execute(self): pass  # 子类实现

# ═════════════════════════════════════════════
#  TAB 1 — 通用重命名
# ═════════════════════════════════════════════
class OpRow(tk.Frame):
    """单条操作行，支持拖拽排序（通过上下按钮模拟）"""
    TYPES = ["增加前缀", "删除前缀", "增加后缀", "删除后缀", "查找替换", "序号规范化", "自定义正则"]

    def __init__(self, parent, on_delete, on_move, refresh_preview, **kw):
        super().__init__(parent, bg=PANEL,
                         highlightthickness=1, highlightbackground=BORDER, **kw)
        self._on_delete = on_delete
        self._on_move   = on_move          # on_move(self, delta)
        self._refresh   = refresh_preview

        # 拖拽手柄 + 上下按钮
        grip = tk.Frame(self, bg=PANEL, width=28)
        grip.pack(side="left", fill="y", padx=(4, 0))
        grip.pack_propagate(False)
        tk.Button(grip, text="▲", bg=PANEL, fg=MUTED, relief="flat", bd=0,
                  font=("Segoe UI", 8), cursor="hand2",
                  command=lambda: self._on_move(self, -1)).pack(fill="x")
        tk.Button(grip, text="▼", bg=PANEL, fg=MUTED, relief="flat", bd=0,
                  font=("Segoe UI", 8), cursor="hand2",
                  command=lambda: self._on_move(self, +1)).pack(fill="x")

        # 类型下拉
        self.type_var = tk.StringVar(value=self.TYPES[0])
        self._type_cb = ttk.Combobox(self, textvariable=self.type_var,
                                     values=self.TYPES, state="readonly",
                                     width=14, font=("Segoe UI", 10))
        self._type_cb.pack(side="left", padx=6, ipady=3)
        self.type_var.trace_add("write", lambda *_: self._rebuild_params())

        # 参数区（动态）
        self._param_frame = tk.Frame(self, bg=PANEL)
        self._param_frame.pack(side="left", fill="x", expand=True, padx=(0, 4))

        # 删除按钮
        tk.Button(self, text="✕", bg=PANEL, fg=MUTED, relief="flat",
                  activebackground=ERR_BG, activeforeground=ERR,
                  font=("Segoe UI", 10), cursor="hand2",
                  command=self._on_delete).pack(side="right", padx=4)

        self._widgets: dict = {}
        self._rebuild_params()

    def _rebuild_params(self):
        for w in self._param_frame.winfo_children():
            w.destroy()
        self._widgets.clear()
        t = self.type_var.get()

        def ent(ph, w=22):
            e = make_entry(self._param_frame, width=w, placeholder=ph)
            e.pack(side="left", ipady=3, padx=(0, 6))
            e.bind("<KeyRelease>", lambda _: self._refresh())
            return e

        if t in ("增加前缀", "删除前缀"):
            self._widgets["text"] = ent("文本，如 [VCB-Studio]")
        elif t in ("增加后缀", "删除后缀"):
            self._widgets["text"] = ent("文本，如 [1080p]")
        elif t == "查找替换":
            self._widgets["find"]    = ent("查找")
            self._widgets["replace"] = ent("替换为（留空=删除）", 18)
            self._widgets["regex"]   = self._check("正则")
        elif t == "序号规范化":
            tk.Label(self._param_frame, text="格式", bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9)).pack(side="left")
            self._widgets["fmt"]    = ent("如 S01E{n:02d}", 16)
            tk.Label(self._param_frame, text="偏移", bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9)).pack(side="left")
            self._widgets["offset"] = ent("0", 5)
        elif t == "自定义正则":
            self._widgets["pattern"] = ent("正则表达式")
            self._widgets["replace"] = ent("替换（支持 \\1）", 18)

    def _check(self, label):
        var = tk.BooleanVar(value=False)
        tk.Checkbutton(self._param_frame, text=label, variable=var,
                       bg=PANEL, fg=TEXT, font=("Segoe UI", 10),
                       activebackground=PANEL, selectcolor=PANEL,
                       command=self._refresh).pack(side="left", padx=(0, 6))
        return var

    def apply(self, stem: str) -> str:
        """对文件主名（不含扩展名）应用本操作，返回新主名。"""
        t = self.type_var.get()
        w = self._widgets
        PH = {e.cget("fg") == MUTED for e in [v for v in w.values() if isinstance(v, tk.Entry)]}

        def val(key):
            v = w[key]
            if isinstance(v, tk.BooleanVar): return v.get()
            s = v.get().strip()
            return "" if v.cget("fg") == MUTED else s  # 占位文字视为空

        if t == "增加前缀":
            txt = val("text"); return txt + stem if txt else stem
        if t == "删除前缀":
            txt = val("text"); return stem[len(txt):] if txt and stem.startswith(txt) else stem
        if t == "增加后缀":
            txt = val("text"); return stem + txt if txt else stem
        if t == "删除后缀":
            txt = val("text"); return stem[:-len(txt)] if txt and stem.endswith(txt) else stem
        if t == "查找替换":
            find = val("find"); repl = val("replace"); use_re = val("regex")
            if not find: return stem
            try:
                return re.sub(find, repl, stem) if use_re else stem.replace(find, repl)
            except re.error: return stem
        if t == "序号规范化":
            fmt = val("fmt"); off_s = val("offset")
            ep = extract_episode(stem)
            if ep is None: return stem
            try:
                offset = int(off_s) if off_s else 0
                ep += offset
                return fmt.format(n=ep) if fmt else stem
            except Exception: return stem
        if t == "自定义正则":
            pat = val("pattern"); repl = val("replace")
            if not pat: return stem
            try: return re.sub(pat, repl, stem)
            except re.error: return stem
        return stem


class RenameTab(tk.Frame, LogMixin):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._files: list[Path] = []
        self._op_rows: list[OpRow] = []
        self._build()

    def _build(self):
        # ── 文件选择
        fs = section_frame(self, "文件列表")
        br = tk.Frame(fs, bg=PANEL); br.pack(fill="x")
        self._path_var = tk.StringVar()
        tk.Entry(br, textvariable=self._path_var, state="readonly",
                 readonlybackground=BG, **{k:v for k,v in ENTRY_CFG.items()
                 if k not in ("bg",)}
                 ).pack(side="left", fill="x", expand=True, ipady=4, padx=(0,8))
        plain_btn(br, "选择文件",   self._pick_files).pack(side="left", padx=(0,4))
        plain_btn(br, "选择文件夹", self._pick_folder).pack(side="left", padx=(0,4))
        plain_btn(br, "清空",       self._clear_files).pack(side="left")
        DropZone(fs, self._drop).pack(fill="x", pady=(8,0))
        self._file_preview = tk.Label(fs, text="尚未选择文件", bg=PANEL, fg=MUTED,
                                      font=("Segoe UI", 10), justify="left", anchor="w")
        self._file_preview.pack(fill="x", pady=(6,0))

        # ── 操作列表
        ops = section_frame(self, "操作（可拖拽排序）")
        self._ops_frame = tk.Frame(ops, bg=PANEL); self._ops_frame.pack(fill="x")
        plain_btn(ops, "+ 添加操作", self._add_op).pack(anchor="w", pady=(6,0))

        # ── 预览
        pv = section_frame(self, "预览")
        cols = ("原文件名", "新文件名")
        self._preview_tree = ttk.Treeview(pv, columns=cols, show="headings", height=6)
        for c in cols:
            self._preview_tree.heading(c, text=c)
            self._preview_tree.column(c, width=300, anchor="w")
        self._preview_tree.pack(fill="x")
        plain_btn(pv, "刷新预览", self._refresh_preview).pack(anchor="w", pady=(6,0))

        # ── 日志 + 执行
        self._init_log(self)

    # ── 文件管理
    def _pick_files(self):
        ps = filedialog.askopenfilenames(title="选择文件")
        if ps: self._add_paths([Path(p) for p in ps])

    def _pick_folder(self):
        d = filedialog.askdirectory(title="选择文件夹")
        if d: self._add_paths([p for p in Path(d).glob("*") if p.is_file()])

    def _drop(self, paths): self._add_paths(paths)

    def _add_paths(self, new):
        ex = {p.resolve() for p in self._files}
        for p in new:
            if p.resolve() not in ex:
                self._files.append(p); ex.add(p.resolve())
        self._update_file_preview()
        self._refresh_preview()

    def _clear_files(self):
        self._files.clear()
        self._update_file_preview()
        self._refresh_preview()

    def _update_file_preview(self):
        n = len(self._files)
        if n == 0:
            self._path_var.set(""); self._file_preview.config(text="尚未选择文件", fg=MUTED); return
        dirs = {str(p.parent) for p in self._files}
        self._path_var.set((next(iter(dirs)) if len(dirs)==1 else f"{len(dirs)} 个目录") + f"  （共 {n} 个）")
        lines = "\n".join(p.name for p in self._files[:6])
        if n > 6: lines += f"\n… 还有 {n-6} 个"
        self._file_preview.config(text=lines, fg=TEXT)

    # ── 操作管理
    def _add_op(self):
        row = OpRow(self._ops_frame,
                    on_delete=lambda r=None: self._del_op(row),
                    on_move=self._move_op,
                    refresh_preview=self._refresh_preview)
        row.pack(fill="x", pady=(0,4))
        self._op_rows.append(row)
        self._refresh_preview()

    def _del_op(self, row):
        row.destroy(); self._op_rows.remove(row); self._refresh_preview()

    def _move_op(self, row, delta):
        idx = self._op_rows.index(row)
        new = idx + delta
        if not (0 <= new < len(self._op_rows)): return
        self._op_rows[idx], self._op_rows[new] = self._op_rows[new], self._op_rows[idx]
        for r in self._op_rows: r.pack_forget()
        for r in self._op_rows: r.pack(fill="x", pady=(0,4))
        self._refresh_preview()

    # ── 预览
    def _compute_new_name(self, path: Path) -> str:
        stem = path.stem
        for row in self._op_rows:
            try: stem = row.apply(stem)
            except Exception: pass
        return stem + path.suffix

    def _refresh_preview(self):
        for row in self._preview_tree.get_children():
            self._preview_tree.delete(row)
        for p in self._files[:50]:
            new = self._compute_new_name(p)
            tag = "same" if new == p.name else "changed"
            self._preview_tree.insert("", "end", values=(p.name, new), tags=(tag,))
        self._preview_tree.tag_configure("changed", foreground=SUCCESS)
        self._preview_tree.tag_configure("same",    foreground=MUTED)

    # ── 执行
    def _execute(self):
        if not self._files:
            messagebox.showwarning("提示", "请先选择文件"); return
        if not self._op_rows:
            messagebox.showwarning("提示", "请至少添加一个操作"); return
        ok = skip = err = 0
        self.log("─"*60, "head")
        for path in self._files:
            new_name = self._compute_new_name(path)
            if new_name == path.name:
                self.log(f"  ·  {path.name}  （无变化，跳过）", "info"); skip += 1; continue
            dst = path.parent / new_name
            try:
                if dst.exists(): dst = self._resolve_conflict(dst)
                path.rename(dst)
                self.log(f"  ✓  {path.name}  →  {new_name}", "ok"); ok += 1
            except Exception as e:
                self.log(f"  ✗  {path.name}  错误: {e}", "err"); err += 1
        self.log(f"完成：成功 {ok}  跳过 {skip}  失败 {err}", "head")
        self.log("─"*60, "head")
        self._files.clear(); self._update_file_preview(); self._refresh_preview()

    @staticmethod
    def _resolve_conflict(path: Path) -> Path:
        i = 1
        while True:
            c = path.parent / f"{path.stem}_{i}{path.suffix}"
            if not c.exists(): return c
            i += 1


# ═════════════════════════════════════════════
#  TAB 2 — 后缀批量修改
# ═════════════════════════════════════════════
class ExtRow(tk.Frame):
    def __init__(self, parent, on_delete, **kw):
        super().__init__(parent, bg=PANEL, **kw)
        self.src_var = tk.StringVar(); self.dst_var = tk.StringVar(); self.dir_var = tk.StringVar()
        src = make_entry(self, width=10, placeholder=".zip"); src.pack(side="left", ipady=3, padx=(0,4))
        tk.Label(self, text="→", bg=PANEL, fg=MUTED, font=("Segoe UI",10)).pack(side="left", padx=(0,4))
        dst = make_entry(self, width=10, placeholder=".cbz"); dst.pack(side="left", ipady=3, padx=(0,6))
        self._dir_e = make_entry(self, width=26, placeholder="留空则原地修改")
        self._dir_e.pack(side="left", ipady=3, padx=(0,4), expand=True, fill="x")
        plain_btn(self, "…", self._browse).pack(side="left", padx=(0,4))
        tk.Button(self, text="✕", bg=PANEL, fg=MUTED, relief="flat",
                  activebackground=ERR_BG, activeforeground=ERR,
                  font=("Segoe UI",10), cursor="hand2",
                  command=on_delete).pack(side="right")
        self._src_e = src; self._dst_e = dst

    def _browse(self):
        p = filedialog.askdirectory(title="选择目标文件夹")
        if p:
            self._dir_e.delete(0,"end"); self._dir_e.insert(0,p); self._dir_e.config(fg=TEXT)

    def _val(self, e, ph=""):
        s = e.get().strip()
        return "" if (e.cget("fg") == MUTED or s == ph) else s

    def get(self):
        src = self._val(self._src_e, ".zip")
        dst = self._val(self._dst_e, ".cbz")
        folder = self._val(self._dir_e, "留空则原地修改")
        if src and not src.startswith("."): src = "." + src
        if dst and not dst.startswith("."): dst = "." + dst
        return src.lower(), dst, folder


class ExtTab(tk.Frame, LogMixin):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._files: list[Path] = []
        self._ext_rows: list[ExtRow] = []
        self._build()

    def _build(self):
        # 规则
        rs = section_frame(self, "转换规则")
        hdr = tk.Frame(rs, bg=PANEL); hdr.pack(fill="x", pady=(0,4))
        for t,w in [("源后缀",10),("",2),("目标后缀",10),("目标文件夹（留空=原地修改）",26)]:
            tk.Label(hdr, text=t, bg=PANEL, fg=MUTED, font=("Segoe UI",9),
                     width=w, anchor="w").pack(side="left", padx=(0,6))
        self._rules_frame = tk.Frame(rs, bg=PANEL); self._rules_frame.pack(fill="x")
        plain_btn(rs, "+ 添加规则", self._add_rule).pack(anchor="w", pady=(6,0))
        self._add_rule()   # 默认一条

        # 文件选择
        fs = section_frame(self, "选择文件")
        br = tk.Frame(fs, bg=PANEL); br.pack(fill="x")
        self._path_var = tk.StringVar()
        tk.Entry(br, textvariable=self._path_var, state="readonly",
                 readonlybackground=BG, **{k:v for k,v in ENTRY_CFG.items() if k!="bg"}
                 ).pack(side="left", fill="x", expand=True, ipady=4, padx=(0,8))
        plain_btn(br, "选择文件",   self._pick_files).pack(side="left", padx=(0,4))
        plain_btn(br, "选择文件夹", self._pick_folder).pack(side="left", padx=(0,4))
        plain_btn(br, "清空",       self._clear_files).pack(side="left")

        opt = tk.Frame(fs, bg=PANEL); opt.pack(fill="x", pady=(8,0))
        self._recursive_var = tk.BooleanVar(value=False)
        self._keep_var      = tk.BooleanVar(value=False)
        tk.Checkbutton(opt, text="包含子文件夹（递归）", variable=self._recursive_var,
                       bg=PANEL, fg=TEXT, font=("Segoe UI",10),
                       activebackground=PANEL, selectcolor=PANEL).pack(side="left", padx=(0,16))
        tk.Checkbutton(opt, text="保留源文件（复制）", variable=self._keep_var,
                       bg=PANEL, fg=TEXT, font=("Segoe UI",10),
                       activebackground=PANEL, selectcolor=PANEL).pack(side="left")

        DropZone(fs, self._drop).pack(fill="x", pady=(8,0))
        self._file_preview = tk.Label(fs, text="尚未选择文件", bg=PANEL, fg=MUTED,
                                      font=("Segoe UI",10), justify="left", anchor="w")
        self._file_preview.pack(fill="x", pady=(6,0))

        self._init_log(self)

    def _add_rule(self):
        row = ExtRow(self._rules_frame, on_delete=lambda r=None: self._del_rule(row))
        row.pack(fill="x", pady=(0,4)); self._ext_rows.append(row)

    def _del_rule(self, row):
        row.destroy(); self._ext_rows.remove(row)

    def _pick_files(self):
        ps = filedialog.askopenfilenames(title="选择文件")
        if ps: self._add_paths([Path(p) for p in ps])

    def _pick_folder(self):
        d = filedialog.askdirectory(title="选择文件夹")
        if d:
            pat = "**/*" if self._recursive_var.get() else "*"
            self._add_paths([p for p in Path(d).glob(pat) if p.is_file()])

    def _drop(self, paths): self._add_paths(paths)

    def _add_paths(self, new):
        ex = {p.resolve() for p in self._files}
        for p in new:
            if p.resolve() not in ex:
                self._files.append(p); ex.add(p.resolve())
        self._update_preview()

    def _clear_files(self):
        self._files.clear(); self._update_preview()

    def _update_preview(self):
        n = len(self._files)
        if n == 0:
            self._path_var.set(""); self._file_preview.config(text="尚未选择文件", fg=MUTED); return
        dirs = {str(p.parent) for p in self._files}
        self._path_var.set((next(iter(dirs)) if len(dirs)==1 else f"{len(dirs)} 个目录") + f"  （共 {n} 个）")
        lines = "\n".join(p.name for p in self._files[:6])
        if n > 6: lines += f"\n… 还有 {n-6} 个"
        self._file_preview.config(text=lines, fg=TEXT)

    def _execute(self):
        rules = [(s,d,f) for row in self._ext_rows for s,d,f in [row.get()] if s and d]
        if not rules:   messagebox.showwarning("提示","请配置至少一条有效规则"); return
        if not self._files: messagebox.showwarning("提示","请先选择文件"); return
        keep = self._keep_var.get()
        ok = skip = err = 0
        self.log("─"*60, "head")
        for path in self._files:
            ext = path.suffix.lower()
            m = next((r for r in rules if r[0]==ext), None)
            if not m:
                self.log(f"  ·  {path.name}  （无匹配规则，跳过）","info"); skip+=1; continue
            _, dst_ext, dst_folder = m
            dst_dir = Path(dst_folder) if dst_folder else path.parent
            dst_path = dst_dir / (path.stem + dst_ext)
            try:
                dst_dir.mkdir(parents=True, exist_ok=True)
                if dst_path.exists(): dst_path = self._resolve(dst_path)
                if keep:          shutil.copy2(str(path), str(dst_path)); act = f"复制 → {dst_path}"
                elif dst_folder:  shutil.move(str(path), str(dst_path));  act = f"移动 → {dst_path}"
                else:             path.rename(dst_path);                   act = f"重命名 → {dst_path.name}"
                self.log(f"  ✓  {path.name}  →  {act}", "ok"); ok+=1
            except Exception as e:
                self.log(f"  ✗  {path.name}  错误: {e}", "err"); err+=1
        self.log(f"完成：成功 {ok}  跳过 {skip}  失败 {err}", "head")
        self.log("─"*60, "head")
        if not keep: self._files.clear(); self._update_preview()

    @staticmethod
    def _resolve(path: Path) -> Path:
        i = 1
        while True:
            c = path.parent / f"{path.stem}_{i}{path.suffix}"
            if not c.exists(): return c
            i += 1


# ═════════════════════════════════════════════
#  TAB 3 — 字幕配对
# ═════════════════════════════════════════════
class SubTab(tk.Frame, LogMixin):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._videos:  list[Path] = []
        self._subs:    list[Path] = []
        self._pairs:   list[tuple[Path|None, Path]] = []   # (video, sub)
        self._build()

    def _build(self):
        # ── 视频 & 字幕选择（左右两列）
        pick_outer = tk.Frame(self, bg=BG)
        pick_outer.pack(fill="x", padx=16, pady=(10,0))

        for title, attr, drop_cb, pick_cb in [
            ("视频文件", "_videos", self._drop_video, self._pick_video),
            ("字幕文件", "_subs",   self._drop_sub,   self._pick_sub),
        ]:
            col = tk.Frame(pick_outer, bg=PANEL,
                           highlightthickness=1, highlightbackground=BORDER)
            col.pack(side="left", fill="both", expand=True, padx=(0,8) if attr=="_videos" else 0)
            tk.Label(col, text=title, bg=PANEL, fg=MUTED,
                     font=("Segoe UI",9)).pack(anchor="w", padx=10, pady=(8,0))
            inner = tk.Frame(col, bg=PANEL); inner.pack(fill="x", padx=10, pady=(4,8))
            br = tk.Frame(inner, bg=PANEL); br.pack(fill="x")
            plain_btn(br, "选择文件",   pick_cb).pack(side="left", padx=(0,4))
            plain_btn(br, "选择文件夹", lambda a=attr: self._pick_folder(a)).pack(side="left", padx=(0,4))
            plain_btn(br, "清空",       lambda a=attr: self._clear_list(a)).pack(side="left")
            DropZone(inner, drop_cb, label="拖拽到此处").pack(fill="x", pady=(6,0))
            lbl = tk.Label(inner, text="尚未选择", bg=PANEL, fg=MUTED,
                           font=("Segoe UI",10), justify="left", anchor="w")
            lbl.pack(fill="x", pady=(4,0))
            setattr(self, f"_{attr.strip('_')}_lbl", lbl)

        # ── 配对选项
        opt_s = section_frame(self, "配对选项")
        opt_r = tk.Frame(opt_s, bg=PANEL); opt_r.pack(fill="x")
        tk.Label(opt_r, text="集数偏移", bg=PANEL, fg=TEXT,
                 font=("Segoe UI",10)).pack(side="left", padx=(0,6))
        self._offset_e = make_entry(opt_r, width=6, placeholder="0")
        self._offset_e.pack(side="left", ipady=3, padx=(0,16))
        self._keep_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_r, text="保留源字幕文件", variable=self._keep_var,
                       bg=PANEL, fg=TEXT, font=("Segoe UI",10),
                       activebackground=PANEL, selectcolor=PANEL).pack(side="left", padx=(0,16))
        plain_btn(opt_r, "自动配对", self._auto_pair).pack(side="left")

        # ── 配对预览表
        pv = section_frame(self, "配对预览（可点击字幕列手动调整）")
        cols = ("视频文件", "字幕文件（原）", "字幕文件（目标）")
        self._pair_tree = ttk.Treeview(pv, columns=cols, show="headings", height=8)
        widths = [260, 220, 220]
        for c, w in zip(cols, widths):
            self._pair_tree.heading(c, text=c)
            self._pair_tree.column(c, width=w, anchor="w")
        self._pair_tree.pack(fill="x")
        self._pair_tree.tag_configure("ok",      foreground=SUCCESS)
        self._pair_tree.tag_configure("unpaired", foreground=WARN)
        self._pair_tree.tag_configure("conflict", foreground=ERR)

        self._init_log(self)

    # ── 文件管理
    def _pick_video(self):
        ps = filedialog.askopenfilenames(title="选择视频文件",
            filetypes=[("视频文件","*.mkv *.mp4 *.avi *.mov *.ts"),("所有文件","*.*")])
        if ps: self._add_paths("_videos", [Path(p) for p in ps])

    def _pick_sub(self):
        ps = filedialog.askopenfilenames(title="选择字幕文件",
            filetypes=[("字幕文件","*.ass *.srt *.ssa *.sub"),("所有文件","*.*")])
        if ps: self._add_paths("_subs", [Path(p) for p in ps])

    def _pick_folder(self, attr):
        d = filedialog.askdirectory()
        if d: self._add_paths(attr, [p for p in Path(d).glob("*") if p.is_file()])

    def _drop_video(self, paths): self._add_paths("_videos", paths)
    def _drop_sub(self,   paths): self._add_paths("_subs",   paths)

    def _clear_list(self, attr):
        getattr(self, attr).clear()
        self._update_list_label(attr)
        self._pairs.clear(); self._refresh_pair_tree()

    def _add_paths(self, attr, new):
        lst = getattr(self, attr)
        ex = {p.resolve() for p in lst}
        for p in new:
            if p.resolve() not in ex:
                lst.append(p); ex.add(p.resolve())
        self._update_list_label(attr)

    def _update_list_label(self, attr):
        lst = getattr(self, attr)
        lbl_attr = f"_{attr.strip('_')}_lbl"
        lbl = getattr(self, lbl_attr, None)
        if lbl is None: return
        n = len(lst)
        if n == 0: lbl.config(text="尚未选择", fg=MUTED); return
        lines = "\n".join(p.name for p in lst[:5])
        if n > 5: lines += f"\n… 还有 {n-5} 个"
        lbl.config(text=lines, fg=TEXT)

    # ── 自动配对
    def _auto_pair(self):
        if not self._videos: messagebox.showwarning("提示","请先选择视频文件"); return
        if not self._subs:   messagebox.showwarning("提示","请先选择字幕文件"); return
        off_s = self._offset_e.get().strip()
        if self._offset_e.cget("fg") == MUTED: off_s = "0"
        try:    offset = int(off_s)
        except: offset = 0

        # 建立字幕集数索引
        sub_map: dict[int, Path] = {}
        for s in self._subs:
            ep = extract_episode(s.name)
            if ep is not None: sub_map[ep] = s

        self._pairs.clear()
        for v in self._videos:
            ep = extract_episode(v.name)
            if ep is None:
                self._pairs.append((v, None))
                continue
            matched = sub_map.get(ep + offset)
            self._pairs.append((v, matched))

        # 未配对的字幕（无对应视频）也列出
        paired_subs = {p for _, p in self._pairs if p}
        for s in self._subs:
            if s not in paired_subs:
                self._pairs.append((None, s))

        self._refresh_pair_tree()

    def _target_sub_name(self, video: Path, sub: Path) -> str:
        """字幕目标文件名 = 视频主名 + 字幕扩展名"""
        return video.stem + sub.suffix

    def _refresh_pair_tree(self):
        for row in self._pair_tree.get_children():
            self._pair_tree.delete(row)
        for video, sub in self._pairs:
            v_name  = video.name if video else "（无对应视频）"
            s_name  = sub.name   if sub   else "（未配对）"
            if video and sub:
                target = self._target_sub_name(video, sub)
                tag = "ok" if target != sub.name else "ok"
            elif sub and not video:
                target = "（跳过）"; tag = "unpaired"
            else:
                target = "（未找到字幕）"; tag = "unpaired"
            self._pair_tree.insert("", "end",
                values=(v_name, s_name, target), tags=(tag,))

    # ── 执行
    def _execute(self):
        if not self._pairs:
            messagebox.showwarning("提示","请先点击「自动配对」"); return
        keep = self._keep_var.get()
        ok = skip = err = 0
        self.log("─"*60, "head")
        for video, sub in self._pairs:
            if sub is None:
                self.log(f"  ·  {video.name if video else '?'}  （未找到字幕，跳过）","info")
                skip += 1; continue
            if video is None:
                self.log(f"  ·  {sub.name}  （无对应视频，跳过）","info")
                skip += 1; continue
            target_name = self._target_sub_name(video, sub)
            if target_name == sub.name:
                self.log(f"  ·  {sub.name}  （名称已匹配，跳过）","info"); skip+=1; continue
            dst = sub.parent / target_name
            try:
                if dst.exists(): dst = self._resolve(dst)
                if keep: shutil.copy2(str(sub), str(dst)); act = f"复制 → {dst.name}"
                else:    sub.rename(dst);                   act = f"重命名 → {dst.name}"
                self.log(f"  ✓  {sub.name}  →  {act}", "ok"); ok += 1
            except Exception as e:
                self.log(f"  ✗  {sub.name}  错误: {e}", "err"); err += 1
        self.log(f"完成：成功 {ok}  跳过 {skip}  失败 {err}", "head")
        self.log("─"*60, "head")
        if not keep:
            self._subs.clear(); self._pairs.clear()
            self._update_list_label("_subs"); self._refresh_pair_tree()

    @staticmethod
    def _resolve(path: Path) -> Path:
        i = 1
        while True:
            c = path.parent / f"{path.stem}_{i}{path.suffix}"
            if not c.exists(): return c
            i += 1


# ═════════════════════════════════════════════
#  主窗口
# ═════════════════════════════════════════════
_Base = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk


class App(_Base):
    def __init__(self):
        super().__init__()
        self.title("文件名管理工具")
        self.geometry("900x760")
        self.minsize(720, 580)
        self.configure(bg=BG)
        self.resizable(True, True)
        self._build()

    def _build(self):
        # 标题
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(16, 0))
        tk.Label(hdr, text="文件名管理工具", bg=BG, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(hdr, text="通用重命名 · 后缀批量修改 · 字幕配对",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

        # Notebook 样式
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook",        background=BG, borderwidth=0)
        style.configure("TNotebook.Tab",    background=BG, foreground=MUTED,
                                            font=("Segoe UI", 10), padding=(14, 6))
        style.map("TNotebook.Tab",
                  background=[("selected", PANEL)],
                  foreground=[("selected", TEXT)])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=4, pady=(10, 4))

        t1 = RenameTab(nb); nb.add(t1, text="  通用重命名  ")
        t2 = ExtTab(nb);    nb.add(t2, text="  后缀批量修改  ")
        t3 = SubTab(nb);    nb.add(t3, text="  字幕配对  ")


if __name__ == "__main__":
    app = App()
    app.mainloop()
