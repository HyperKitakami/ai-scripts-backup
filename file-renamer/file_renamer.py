"""
文件后缀批量修改工具
Python 3.12 / tkinter（内置，无需额外安装）
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import os
from pathlib import Path


# ── 配色 ──────────────────────────────────────────────────────────────────────
BG       = "#F7F6F3"
PANEL    = "#FFFFFF"
BORDER   = "#E0DED7"
TEXT     = "#1A1A18"
MUTED    = "#6B6A66"
ACCENT   = "#1A1A18"
SUCCESS  = "#3B6D11"
SUCCESS_BG = "#EAF3DE"
ERR      = "#A32D2D"
ERR_BG   = "#FCEBEB"
INFO_BG  = "#F1EFE8"
BTN_H    = "#ECEAE3"


# ── 规则行 ────────────────────────────────────────────────────────────────────
class RuleRow(tk.Frame):
    def __init__(self, parent, on_delete, **kwargs):
        super().__init__(parent, bg=PANEL, **kwargs)

        self.src_var    = tk.StringVar()
        self.dst_var    = tk.StringVar()
        self.folder_var = tk.StringVar()

        entry_cfg = dict(
            bg=BG, fg=TEXT, relief="flat",
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT, insertbackground=TEXT,
            font=("Segoe UI", 10), bd=0
        )

        self.src_entry = tk.Entry(self, textvariable=self.src_var,
                                  width=10, **entry_cfg)
        self.src_entry.insert(0, ".zip")
        self.src_entry.bind("<FocusIn>",  lambda e: self._clear_placeholder(self.src_entry,  ".zip"))
        self.src_entry.bind("<FocusOut>", lambda e: self._set_placeholder  (self.src_entry,  ".zip"))

        self.dst_entry = tk.Entry(self, textvariable=self.dst_var,
                                  width=10, **entry_cfg)
        self.dst_entry.insert(0, ".czb")
        self.dst_entry.bind("<FocusIn>",  lambda e: self._clear_placeholder(self.dst_entry,  ".czb"))
        self.dst_entry.bind("<FocusOut>", lambda e: self._set_placeholder  (self.dst_entry,  ".czb"))

        self.folder_entry = tk.Entry(self, textvariable=self.folder_var,
                                     width=28, **entry_cfg)
        ph = "留空则原地修改"
        self.folder_entry.insert(0, ph)
        self.folder_entry.config(fg=MUTED)
        self.folder_entry.bind("<FocusIn>",  lambda e: self._clear_placeholder(self.folder_entry, ph, True))
        self.folder_entry.bind("<FocusOut>", lambda e: self._set_placeholder  (self.folder_entry, ph, True))

        browse_btn = tk.Button(self, text="…", width=2,
                               bg=BG, fg=TEXT, relief="flat",
                               activebackground=BTN_H,
                               font=("Segoe UI", 10), cursor="hand2",
                               command=self._browse_folder)

        del_btn = tk.Button(self, text="✕", width=2,
                            bg=PANEL, fg=MUTED, relief="flat",
                            activebackground=ERR_BG, activeforeground=ERR,
                            font=("Segoe UI", 10), cursor="hand2",
                            command=on_delete)

        self.src_entry.pack(side="left", ipady=4, padx=(0, 6))
        tk.Label(self, text="→", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 6))
        self.dst_entry.pack(side="left", ipady=4, padx=(0, 6))
        self.folder_entry.pack(side="left", ipady=4, padx=(0, 4), expand=True, fill="x")
        browse_btn.pack(side="left", padx=(0, 6))
        del_btn.pack(side="left")

    # 占位文字处理
    def _clear_placeholder(self, widget, placeholder, grey=False):
        if widget.get() == placeholder:
            widget.delete(0, "end")
            widget.config(fg=TEXT)

    def _set_placeholder(self, widget, placeholder, grey=False):
        if widget.get().strip() == "":
            widget.insert(0, placeholder)
            widget.config(fg=MUTED if grey else TEXT)

    def _browse_folder(self):
        path = filedialog.askdirectory(title="选择目标文件夹")
        if path:
            self.folder_var.set(path)
            self.folder_entry.config(fg=TEXT)

    def get_rule(self):
        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()
        folder = self.folder_var.get().strip()
        placeholder = "留空则原地修改"
        if folder == placeholder:
            folder = ""
        # 自动补点
        if src and not src.startswith("."):
            src = "." + src
        if dst and not dst.startswith("."):
            dst = "." + dst
        return src.lower(), dst, folder


# ── 主窗口 ────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("文件后缀批量修改")
        self.geometry("780x640")
        self.minsize(640, 480)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._rule_rows: list[RuleRow] = []
        self._build_ui()
        self._add_rule()       # 默认一条规则

    # ── 界面构建 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # 顶部标题
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(18, 0))
        tk.Label(hdr, text="文件后缀批量修改工具", bg=BG, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(hdr, text="支持自定义规则、原地修改或移动到指定目录（含 SMB 映射盘符）",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

        # 规则区
        self._build_rules_panel()

        # 文件选择区
        self._build_files_panel()

        # 执行 & 日志
        self._build_action_panel()

    def _section(self, title):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="x", padx=20, pady=(14, 0))
        panel = tk.Frame(outer, bg=PANEL,
                         highlightthickness=1, highlightbackground=BORDER)
        panel.pack(fill="x")
        tk.Label(panel, text=title, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(10, 0))
        inner = tk.Frame(panel, bg=PANEL)
        inner.pack(fill="x", padx=14, pady=(6, 12))
        return inner

    def _build_rules_panel(self):
        inner = self._section("转换规则")

        # 列标题
        hdr = tk.Frame(inner, bg=PANEL)
        hdr.pack(fill="x", pady=(0, 4))
        for text, w in [("源后缀", 10), ("", 2), ("目标后缀", 10), ("目标文件夹（留空=原地修改）", 28)]:
            tk.Label(hdr, text=text, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9), width=w, anchor="w").pack(side="left", padx=(0, 6))

        self._rules_frame = tk.Frame(inner, bg=PANEL)
        self._rules_frame.pack(fill="x")

        add_btn = tk.Button(inner, text="+ 添加规则",
                            bg=BG, fg=MUTED, relief="flat",
                            activebackground=BTN_H, activeforeground=TEXT,
                            font=("Segoe UI", 10), cursor="hand2",
                            command=self._add_rule)
        add_btn.pack(anchor="w", pady=(8, 0))

    def _build_files_panel(self):
        inner = self._section("选择文件")

        row = tk.Frame(inner, bg=PANEL)
        row.pack(fill="x")

        self._src_var = tk.StringVar()
        entry = tk.Entry(row, textvariable=self._src_var, state="readonly",
                         bg=BG, fg=TEXT, relief="flat",
                         highlightthickness=1, highlightbackground=BORDER,
                         font=("Segoe UI", 10), readonlybackground=BG)
        entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))

        tk.Button(row, text="选择文件", bg=BG, fg=TEXT, relief="flat",
                  activebackground=BTN_H, font=("Segoe UI", 10), cursor="hand2",
                  command=self._pick_files).pack(side="left", padx=(0, 6))

        tk.Button(row, text="选择文件夹", bg=BG, fg=TEXT, relief="flat",
                  activebackground=BTN_H, font=("Segoe UI", 10), cursor="hand2",
                  command=self._pick_folder).pack(side="left")

        # 递归选项
        opt_row = tk.Frame(inner, bg=PANEL)
        opt_row.pack(fill="x", pady=(8, 0))
        self._recursive_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_row, text="包含子文件夹（递归）",
                       variable=self._recursive_var,
                       bg=PANEL, fg=TEXT, font=("Segoe UI", 10),
                       activebackground=PANEL, selectcolor=PANEL).pack(side="left")

        # 文件预览列表
        self._preview_frame = tk.Frame(inner, bg=PANEL)
        self._preview_frame.pack(fill="x", pady=(10, 0))
        self._preview_label = tk.Label(self._preview_frame,
                                       text="尚未选择文件", bg=PANEL, fg=MUTED,
                                       font=("Segoe UI", 10))
        self._preview_label.pack(anchor="w")

        self._selected_paths: list[Path] = []

    def _build_action_panel(self):
        inner = self._section("执行")

        btn_row = tk.Frame(inner, bg=PANEL)
        btn_row.pack(fill="x")

        self._run_btn = tk.Button(btn_row, text="执行重命名",
                                  bg=ACCENT, fg="#FFFFFF", relief="flat",
                                  activebackground="#333330", activeforeground="#FFFFFF",
                                  font=("Segoe UI", 10, "bold"), cursor="hand2",
                                  padx=16, pady=6, command=self._run)
        self._run_btn.pack(side="left", padx=(0, 8))

        tk.Button(btn_row, text="清空日志", bg=BG, fg=MUTED, relief="flat",
                  activebackground=BTN_H, font=("Segoe UI", 10), cursor="hand2",
                  padx=12, pady=6,
                  command=self._clear_log).pack(side="left")

        # 日志框
        log_outer = tk.Frame(inner, bg=PANEL)
        log_outer.pack(fill="both", expand=True, pady=(10, 0))

        self._log_text = tk.Text(log_outer, height=10, state="disabled",
                                 bg=INFO_BG, fg=TEXT, relief="flat",
                                 font=("Consolas", 9), wrap="word",
                                 highlightthickness=0, bd=0)
        self._log_text.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(log_outer, command=self._log_text.yview)
        sb.pack(side="right", fill="y")
        self._log_text.config(yscrollcommand=sb.set)

        self._log_text.tag_config("ok",   foreground=SUCCESS, background=SUCCESS_BG)
        self._log_text.tag_config("err",  foreground=ERR,     background=ERR_BG)
        self._log_text.tag_config("info", foreground=MUTED)
        self._log_text.tag_config("head", foreground=TEXT, font=("Consolas", 9, "bold"))

    # ── 规则管理 ──────────────────────────────────────────────────────────────
    def _add_rule(self):
        row = RuleRow(self._rules_frame,
                      on_delete=lambda r=None: self._delete_rule(row))
        row.pack(fill="x", pady=(0, 4))
        self._rule_rows.append(row)

    def _delete_rule(self, row):
        row.destroy()
        self._rule_rows.remove(row)

    # ── 文件选择 ──────────────────────────────────────────────────────────────
    def _pick_files(self):
        paths = filedialog.askopenfilenames(title="选择文件")
        if paths:
            self._selected_paths = [Path(p) for p in paths]
            self._update_preview()

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="选择文件夹")
        if folder:
            recursive = self._recursive_var.get()
            pattern = "**/*" if recursive else "*"
            self._selected_paths = [
                p for p in Path(folder).glob(pattern) if p.is_file()
            ]
            self._update_preview()

    def _update_preview(self):
        n = len(self._selected_paths)
        if n == 0:
            self._preview_label.config(text="未找到文件")
            self._src_var.set("")
            return
        self._src_var.set(str(self._selected_paths[0].parent) +
                          f"  （共 {n} 个文件）")
        self._preview_label.config(
            text="\n".join(p.name for p in self._selected_paths[:8]) +
                 (f"\n… 还有 {n - 8} 个文件" if n > 8 else ""),
            fg=TEXT
        )

    # ── 执行 ──────────────────────────────────────────────────────────────────
    def _run(self):
        rules = []
        for row in self._rule_rows:
            src, dst, folder = row.get_rule()
            if src and dst:
                rules.append((src, dst, folder))

        if not rules:
            messagebox.showwarning("提示", "请至少配置一条有效规则（源后缀和目标后缀均不能为空）")
            return
        if not self._selected_paths:
            messagebox.showwarning("提示", "请先选择要处理的文件")
            return

        self._log("─" * 60, "head")
        self._log(f"开始处理，共 {len(self._selected_paths)} 个文件，{len(rules)} 条规则", "info")

        ok = skip = err = 0

        for path in self._selected_paths:
            ext = path.suffix.lower()
            matched = next((r for r in rules if r[0] == ext), None)
            if not matched:
                self._log(f"  跳过  {path.name}  （无匹配规则）", "info")
                skip += 1
                continue

            _, dst_ext, dst_folder = matched
            new_name = path.stem + dst_ext

            if dst_folder:
                dst_dir = Path(dst_folder)
                dst_dir.mkdir(parents=True, exist_ok=True)
                dst_path = dst_dir / new_name
            else:
                dst_path = path.parent / new_name

            try:
                if dst_path.exists():
                    dst_path = self._resolve_conflict(dst_path)
                if dst_folder:
                    shutil.move(str(path), str(dst_path))
                    action = f"移动+重命名 → {dst_path}"
                else:
                    path.rename(dst_path)
                    action = f"重命名 → {dst_path.name}"
                self._log(f"  ✓  {path.name}  →  {action}", "ok")
                ok += 1
            except Exception as e:
                self._log(f"  ✗  {path.name}  错误: {e}", "err")
                err += 1

        self._log(f"完成：成功 {ok}  跳过 {skip}  失败 {err}", "head")
        self._log("─" * 60, "head")
        self._selected_paths = []
        self._update_preview()

    def _resolve_conflict(self, path: Path) -> Path:
        i = 1
        while True:
            candidate = path.parent / f"{path.stem}_{i}{path.suffix}"
            if not candidate.exists():
                return candidate
            i += 1

    # ── 日志 ──────────────────────────────────────────────────────────────────
    def _log(self, msg, tag="info"):
        self._log_text.config(state="normal")
        self._log_text.insert("end", msg + "\n", tag)
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _clear_log(self):
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
