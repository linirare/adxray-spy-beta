"""ADXRay Game Spy - 公开 Beta 图形界面。"""
import json
import queue
import re
import sys
import threading
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

sys.path.insert(0, str(Path(__file__).parent))
from adxray_spy_core import (  # noqa: E402
    APP_VERSION,
    ADXRaySpy,
    ExtractionCancelled,
    create_diagnostic_bundle,
    ensure_playwright_browsers,
)

RELEASE_API = "https://api.github.com/repos/linirare/adxray-spy-beta/releases?per_page=1"


def version_key(value):
    """将公开版本标签转换为可比较元组，稳定版高于同号 Beta。"""
    value = str(value).lower().lstrip("v")
    main, separator, prerelease = value.partition("-")
    numbers = [int(item) for item in re.findall(r"\d+", main)[:3]]
    numbers.extend([0] * (3 - len(numbers)))
    stable_rank = 1 if not separator else 0
    prerelease_number = int(re.findall(r"\d+", prerelease)[-1]) if re.findall(r"\d+", prerelease) else 0
    return (*numbers, stable_rank, prerelease_number)


class RedirectText:
    """将 print 输出送入线程安全日志队列。"""

    def __init__(self, emit):
        self.emit = emit
        self.buffer = ""
        self.lock = threading.Lock()

    def write(self, text):
        if not text:
            return
        with self.lock:
            self.buffer += text
            while "\n" in self.buffer:
                line, self.buffer = self.buffer.split("\n", 1)
                self.emit(line, timestamp=False)

    def flush(self):
        with self.lock:
            if self.buffer:
                self.emit(self.buffer, timestamp=False)
                self.buffer = ""


class ADXRaySpyGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title(f"ADXRay Game Spy {APP_VERSION}")
        self.window.geometry("760x720")
        self.window.minsize(720, 650)

        self.ui_queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker = None
        self.spy = None
        self.logs = []
        self.last_data = None
        self.last_diagnostics = []
        self.output_dir = str(Path.cwd() / "output")
        self.session_name = "adx"

        self._build_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.after(50, self._drain_ui_queue)
        self.window.after(1500, self._check_updates_async)
        self._log("Ready. 发布版内置 Chromium；所有登录数据仅保存在本机。")

    def _build_ui(self):
        header = ttk.Frame(self.window, padding=(20, 15, 20, 5))
        header.pack(fill="x")
        ttk.Label(header, text="ADXRay Game Spy", font=("Microsoft YaHei", 17, "bold")).pack(side="left")
        ttk.Label(header, text=APP_VERSION, foreground="#777").pack(side="right")
        ttk.Label(
            self.window,
            text="输入游戏名，自动提取 ADXRay 可见投放数据、素材链接，并生成文本报告与 Excel",
            foreground="#555",
        ).pack(anchor="w", padx=22, pady=(0, 12))

        form = ttk.Frame(self.window, padding=(20, 5))
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="游戏名称").grid(row=0, column=0, sticky="w", pady=5)
        self.game_entry = ttk.Entry(form, font=("Microsoft YaHei", 10))
        self.game_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=5)
        self.game_entry.focus()

        ttk.Label(form, text="输出目录").grid(row=1, column=0, sticky="w", pady=5)
        self.dir_var = tk.StringVar(value=self.output_dir)
        ttk.Entry(form, textvariable=self.dir_var).grid(row=1, column=1, sticky="ew", padx=(10, 5), pady=5)
        self.browse_btn = ttk.Button(form, text="浏览", command=self._browse_dir, width=8)
        self.browse_btn.grid(row=1, column=2, pady=5)

        account = ttk.LabelFrame(self.window, text="ADXRay 登录", padding=8)
        account.pack(fill="x", padx=20, pady=10)
        self.status_label = ttk.Label(account, text="尚未检查", foreground="#666")
        self.status_label.pack(side="left", padx=5)
        self.clear_login_btn = ttk.Button(account, text="清除登录", command=self._clear_login)
        self.clear_login_btn.pack(side="right", padx=4)
        self.relogin_btn = ttk.Button(account, text="重新登录", command=self._re_login)
        self.relogin_btn.pack(side="right", padx=4)
        self.check_login_btn = ttk.Button(account, text="检查登录", command=self._check_login)
        self.check_login_btn.pack(side="right", padx=4)

        actions = ttk.Frame(self.window, padding=(20, 0))
        actions.pack(fill="x")
        self.run_btn = ttk.Button(actions, text="开始提取", command=self._start_extract)
        self.run_btn.pack(side="left")
        self.cancel_btn = ttk.Button(actions, text="取消", command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=8)
        self.diagnostic_btn = ttk.Button(actions, text="导出诊断包", command=self._export_diagnostics, state="disabled")
        self.diagnostic_btn.pack(side="right")

        progress_frame = ttk.Frame(self.window, padding=(20, 10, 20, 0))
        progress_frame.pack(fill="x")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x")
        self.progress_label = ttk.Label(progress_frame, text="等待任务", foreground="#666")
        self.progress_label.pack(anchor="w", pady=(3, 0))

        ttk.Label(self.window, text="运行日志", foreground="#666").pack(anchor="w", padx=22, pady=(10, 2))
        self.log_text = scrolledtext.ScrolledText(
            self.window,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            height=20,
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        sys.stdout = RedirectText(self._log)

        self.conflict_buttons = [
            self.run_btn,
            self.browse_btn,
            self.check_login_btn,
            self.relogin_btn,
            self.clear_login_btn,
        ]

    def _post_ui(self, callback, *args, **kwargs):
        self.ui_queue.put((callback, args, kwargs))

    def _drain_ui_queue(self):
        try:
            while True:
                callback, args, kwargs = self.ui_queue.get_nowait()
                callback(*args, **kwargs)
        except queue.Empty:
            pass
        if self.window.winfo_exists():
            self.window.after(50, self._drain_ui_queue)

    def _append_log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _log(self, text, timestamp=True):
        if not text:
            return
        rendered = str(text)
        if timestamp and not rendered.startswith("\n"):
            rendered = f"[{datetime.now():%H:%M:%S}] {rendered}"
        if not rendered.endswith("\n"):
            rendered += "\n"
        self.logs.extend(line for line in rendered.splitlines() if line)
        self._post_ui(self._append_log, rendered)

    def _set_busy(self, busy, label="等待任务"):
        state = "disabled" if busy else "normal"
        for button in self.conflict_buttons:
            button.config(state=state)
        self.cancel_btn.config(state="normal" if busy else "disabled")
        self.progress_label.config(text=label)
        if not busy:
            self.progress_var.set(0)

    def _set_login_status(self, logged_in, message=""):
        if logged_in:
            self.status_label.config(text=f"已登录 {message}".strip(), foreground="#268a3a")
        else:
            self.status_label.config(text=f"未登录 {message}".strip(), foreground="#c43b3b")

    def _set_progress(self, current, total, message):
        self.progress_var.set((current / max(total, 1)) * 100)
        self.progress_label.config(text=message)

    def _start_worker(self, label, target):
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("任务进行中", "请等待当前任务结束，或先点击取消。")
            return
        self.cancel_event.clear()
        self._set_busy(True, label)

        def wrapper():
            try:
                target()
            except ExtractionCancelled as exc:
                self._log(str(exc))
                self._post_ui(messagebox.showinfo, "已取消", str(exc))
            except Exception as exc:
                self._log(f"任务失败: {exc}")
                self._post_ui(messagebox.showerror, "任务失败", str(exc))
            finally:
                if self.spy:
                    self.last_diagnostics = list(self.spy.diagnostics)
                    if self.last_diagnostics and self.last_data is None:
                        self.last_data = {"游戏名": "", "抓取状态": {"总体状态": "失败", "模块": []}}
                    if self.last_diagnostics:
                        self._post_ui(self.diagnostic_btn.config, state="normal")
                self._close_spy()
                self._post_ui(self._set_busy, False, "等待任务")

        self.worker = threading.Thread(target=wrapper, daemon=True)
        self.worker.start()

    def _close_spy(self):
        spy = self.spy
        self.spy = None
        if spy:
            try:
                spy.close()
            except Exception as exc:
                self._log(f"关闭浏览器时出现问题: {exc}")

    def _new_spy(self, progress_callback=None):
        self._close_spy()
        self.spy = ADXRaySpy(
            self.session_name,
            cancel_event=self.cancel_event,
            progress_callback=progress_callback,
        )
        return self.spy

    def _browse_dir(self):
        selected = filedialog.askdirectory(initialdir=self.dir_var.get() or self.output_dir)
        if selected:
            self.output_dir = selected
            self.dir_var.set(selected)

    def _check_login(self):
        def task():
            self._log("正在检查登录状态...")
            ensure_playwright_browsers()
            spy = self._new_spy()
            spy.launch(headless=True)
            ok = spy.is_logged_in()
            self._post_ui(self._set_login_status, ok, "（会话有效）" if ok else "")
            self._log("登录状态检查完成")

        self._start_worker("正在检查登录状态", task)

    def _re_login(self):
        def task():
            self._log("正在打开浏览器，请在浏览器中完成 ADXRay 登录。")
            ensure_playwright_browsers()
            ADXRaySpy.clear_login_state(self.session_name)
            spy = self._new_spy()
            spy.launch(headless=False)
            ok = spy.wait_for_login()
            self._post_ui(self._set_login_status, ok, "（登录成功）" if ok else "")
            if not ok:
                raise RuntimeError("登录超时，请重试")

        self._start_worker("等待登录", task)

    def _clear_login(self):
        try:
            self._close_spy()
            ADXRaySpy.clear_login_state(self.session_name)
            self._set_login_status(False, "（本地登录状态已清除）")
            self._log("已清除本机保存的 ADXRay 登录状态。")
        except Exception as exc:
            messagebox.showerror("清除失败", str(exc))

    def _choose_product_from_worker(self, products):
        event = threading.Event()
        result = {}

        def ask():
            choices = "\n".join(
                f"{index}. {item.get('name', '未知产品')} (ID={item.get('id', '?')})"
                for index, item in enumerate(products, 1)
            )
            selected = simpledialog.askinteger(
                "选择产品",
                f"找到多个匹配产品，请输入编号：\n\n{choices}",
                minvalue=1,
                maxvalue=len(products),
                parent=self.window,
            )
            if selected:
                result["product"] = products[selected - 1]
            event.set()

        self._post_ui(ask)
        while not event.wait(0.1):
            if self.cancel_event.is_set():
                raise ExtractionCancelled("用户已取消抓取")
        if "product" not in result:
            raise ExtractionCancelled("用户取消了产品选择")
        return result["product"]

    def _start_extract(self):
        raw = self.game_entry.get().strip()
        if not raw:
            messagebox.showwarning("提示", "请输入至少一个游戏名称。")
            return
        games = [item.strip() for item in raw.replace("，", ",").split(",") if item.strip()]
        output_root = self.dir_var.get().strip() or self.output_dir
        self.last_data = None
        self.last_diagnostics = []

        def task():
            ensure_playwright_browsers()
            total_steps = len(games) * 7
            game_step = {"offset": 0}

            def progress(current, _total, message):
                self._post_ui(self._set_progress, game_step["offset"] + current, total_steps, message)

            spy = self._new_spy(progress)
            spy.launch(headless=False)
            if not spy.is_logged_in():
                self._log("需要登录 ADXRay，请在浏览器窗口中完成登录。")
                if not spy.wait_for_login():
                    raise RuntimeError("登录超时，请重试")
            self._post_ui(self._set_login_status, True, "")

            results = []
            for game_index, game in enumerate(games):
                if self.cancel_event.is_set():
                    raise ExtractionCancelled("用户已取消抓取")
                game_step["offset"] = game_index * 7
                self._log(f"\n开始处理: {game}")
                try:
                    product = spy.get_product_from_search(game, chooser=self._choose_product_from_worker)
                    if not product:
                        results.append((game, "失败", "未找到产品"))
                        continue
                    data = spy.extract_all(product)
                    outputs = spy.export_bundle(data, output_root)
                    self.last_data = data
                    status = data.get("抓取状态", {}).get("总体状态", "未知")
                    results.append((game, status, outputs["directory"]))
                    self._log(f"{game}: {status}，输出目录: {outputs['directory']}")
                except ExtractionCancelled:
                    raise
                except Exception as exc:
                    results.append((game, "失败", str(exc)))
                    self._log(f"{game}: 失败 - {exc}")

            lines = [f"{game}: {status}\n{detail}" for game, status, detail in results]
            incomplete = [item for item in results if item[1] != "成功"]
            title = "提取完成" if not incomplete else "提取完成，但存在不完整结果"
            self._post_ui(self.diagnostic_btn.config, state="normal")
            self._post_ui(messagebox.showinfo, title, "\n\n".join(lines))

        self._start_worker("正在提取", task)

    def _cancel(self):
        self.cancel_event.set()
        self.progress_label.config(text="正在取消...")
        self._log("已请求取消，当前页面操作结束后将停止。")

    def _export_diagnostics(self):
        if not self.last_data:
            messagebox.showwarning("无诊断数据", "请先运行一次抓取任务。")
            return
        default = f"adxray-diagnostics-{datetime.now():%Y%m%d-%H%M%S}.zip"
        path = filedialog.asksaveasfilename(
            title="导出诊断包",
            defaultextension=".zip",
            initialfile=default,
            filetypes=[("ZIP archive", "*.zip")],
        )
        if not path:
            return
        extra_logs = list(self.logs)
        extra_logs.extend(json.dumps(item, ensure_ascii=False) for item in self.last_diagnostics)
        create_diagnostic_bundle(path, self.last_data, extra_logs)
        messagebox.showinfo("导出完成", f"诊断包已保存：\n{path}\n\n诊断包不包含 Cookie 或浏览器登录数据。")

    def _check_updates_async(self):
        def task():
            try:
                request = urllib.request.Request(RELEASE_API, headers={"User-Agent": f"ADXRay-Spy/{APP_VERSION}"})
                with urllib.request.urlopen(request, timeout=5) as response:
                    releases = json.load(response)
                release = releases[0] if isinstance(releases, list) and releases else {}
                latest = str(release.get("tag_name", "")).lstrip("v")
                if latest and version_key(latest) > version_key(APP_VERSION):
                    url = release.get("html_url", "https://github.com/linirare/adxray-spy-beta/releases")

                    def notify():
                        if messagebox.askyesno("发现新版本", f"当前版本：{APP_VERSION}\n最新版本：{latest}\n\n打开下载页面？"):
                            webbrowser.open(url)

                    self._post_ui(notify)
            except Exception:
                return

        threading.Thread(target=task, daemon=True).start()

    def _on_close(self):
        self.cancel_event.set()
        sys.stdout = sys.__stdout__
        self.window.destroy()

    def run(self):
        self.window.mainloop()


def main():
    if "--version" in sys.argv:
        print(APP_VERSION)
        return
    if "--smoke-test" in sys.argv:
        import openpyxl  # noqa: F401
        import playwright  # noqa: F401
        ensure_playwright_browsers()
        spy = ADXRaySpy("release-smoke-test")
        try:
            spy.launch(headless=True)
        finally:
            spy.close()
        return
    ADXRaySpyGUI().run()


if __name__ == "__main__":
    main()
