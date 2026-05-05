import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
import json
import os
import sys
import pyautogui
import keyboard
from main import AFKBot

# ── Config ────────────────────────────────────────────────────────────────────
def get_config_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'config.json')
    return os.path.join(os.path.dirname(__file__), 'config.json')

CONFIG_PATH = get_config_path()

DEFAULT_CONFIG = {
    "screen":            {"width": 1920, "height": 1080},
    "hotkey_start_key":  "F5",
    "hotkey_start_scan": 63,
    "hotkey_pause_key":  "F4",
    "hotkey_pause_scan": 62,
    "hotkey_stop_key":   "F8",
    "hotkey_stop_scan":  66,
    "reconnect_enabled": False,
    "reconnect_time":    "07:00",
}

def _load_config():
    if not os.path.exists(CONFIG_PATH):
        _save_config(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ── Launcher GUI ──────────────────────────────────────────────────────────────
class GTA5Launcher(tk.Tk):
    DARK   = "#0f0f0f"
    PANEL  = "#1a1a1a"
    BORDER = "#2a2a2a"
    ACCENT = "#e5c07b"
    GREEN  = "#98c379"
    TEXT   = "#e0e0e0"
    MUTED  = "#666666"
    RED    = "#ff4d4d"

    def __init__(self):
        super().__init__()
        self.title("GTA5RP AFK BOT")
        self.resizable(False, False)
        self.configure(bg=self.DARK)

        self._bot = AFKBot(
            log_fn      = self._log,
            on_end_fn   = lambda: self.after(0, self._on_ended),
            on_cycle_fn = lambda n: self.after(0, self._update_cycles, n),
        )

        self._timer_job = None
        self._build_ui()
        self._load_config_to_ui()
        self._bind_hotkeys()

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        D, P, B, A, G = self.DARK, self.PANEL, self.BORDER, self.ACCENT, self.GREEN
        T, M, R       = self.TEXT, self.MUTED, self.RED

        lf = ("Segoe UI", 9)
        mo = ("Consolas", 10)

        # header
        hdr = tk.Frame(self, bg=D, pady=12)
        hdr.pack(fill="x", padx=16)
        tk.Label(hdr, text="GTA5RP AFK BOT",
                 font=("Segoe UI", 13, "bold"), fg=A, bg=D).pack(side="left")
        self.lbl_status = tk.Label(hdr, text="● остановлен",
                                   font=("Segoe UI", 9), fg=M, bg=D)
        self.lbl_status.pack(side="right", padx=(0, 4))
        tk.Frame(self, bg=B, height=1).pack(fill="x", padx=16)

        # resolution
        res = tk.Frame(self, bg=D, pady=10)
        res.pack(fill="x", padx=16)
        tk.Label(res, text="Разрешение:", font=lf, fg=M, bg=D).pack(side="left")
        self._ent_w = self._entry(res, 6, mo)
        self._ent_w.pack(side="left", padx=(6, 4))
        tk.Label(res, text="×", font=("Segoe UI", 10), fg=M, bg=D).pack(side="left")
        self._ent_h = self._entry(res, 6, mo)
        self._ent_h.pack(side="left", padx=(4, 10))
        self._btn(res, "Сохранить", self._save_resolution).pack(side="left")
        tk.Frame(self, bg=B, height=1).pack(fill="x", padx=16)

        # hotkeys
        for label, attr in [("F5 — Старт", "_lbl_f5"),
                             ("F4 — Пауза", "_lbl_f4"),
                             ("F8 — Стоп",  "_lbl_f8")]:
            self._hotkey_row(label, attr, lf, mo)
        tk.Frame(self, bg=B, height=1).pack(fill="x", padx=16)

        # ── Reconnect schedule ────────────────────────────────────────────────
        rc = tk.Frame(self, bg=D, pady=8)
        rc.pack(fill="x", padx=16)

        self._var_rc = tk.BooleanVar()
        tk.Checkbutton(rc, text="Переподключение в:", variable=self._var_rc,
                       font=lf, fg=M, bg=D, selectcolor=D,
                       activebackground=D, activeforeground=T,
                       command=self._toggle_rc).pack(side="left")

        self._ent_rc = self._entry(rc, 6, mo)
        self._ent_rc.config(bg="#1a1a1a", fg="#e0e0e0")
        self._ent_rc.pack(side="left", padx=(6, 4))
        self._ent_rc.insert(0, "07:00")

        tk.Label(rc, text="по МСК", font=lf, fg=M, bg=D).pack(side="left", padx=(2, 8))
        self._btn(rc, "Сохранить", self._save_rc).pack(side="left")
        tk.Frame(self, bg=B, height=1).pack(fill="x", padx=16)

        # ── Festival ──────────────────────────────────────────────────────────
        fe = tk.Frame(self, bg=D, pady=8)
        fe.pack(fill="x", padx=16)

        self._var_fe = tk.BooleanVar()
        tk.Checkbutton(fe, text="Собирать Событие", variable=self._var_fe,
                       font=lf, fg=M, bg=D, selectcolor=D,
                       activebackground=D, activeforeground=T,
                       command=self._save_fe).pack(side="left")
        tk.Frame(self, bg=B, height=1).pack(fill="x", padx=16)

        # stats
        stats = tk.Frame(self, bg=D, pady=8)

        # stats
        stats = tk.Frame(self, bg=D, pady=8)
        stats.pack(fill="x", padx=16)
        self.lbl_timer  = tk.Label(stats, text="AFK Time: 00:00:00",
                                   font=lf, fg=T, bg=D)
        self.lbl_timer.pack(side="left", padx=(0, 20))
        self.lbl_cycles = tk.Label(stats, text="Cycles: 0",
                                   font=lf, fg=G, bg=D)
        self.lbl_cycles.pack(side="left")
        tk.Frame(self, bg=B, height=1).pack(fill="x", padx=16)

        # start / pause / stop
        ctrl = tk.Frame(self, bg=D, pady=12)
        ctrl.pack(fill="x", padx=16)
        self.btn_start = self._btn(ctrl, "  ▶  Запустить", self._start,
                                   bg=A, fg="#000", active_bg="#d4aa60")
        self.btn_start.pack(side="left", padx=(0, 6))
        self.btn_pause = self._btn(ctrl, "  ⏸  Пауза", self._pause,
                                   bg=B, fg=T, active_bg="#3a3a3a", state="disabled")
        self.btn_pause.pack(side="left", padx=(0, 6))
        self.btn_stop  = self._btn(ctrl, "  ■  Стоп", self._stop,
                                   bg=B, fg=R, active_bg="#3a3a3a", state="disabled")
        self.btn_stop.pack(side="left")

        # log
        lframe = tk.LabelFrame(self, text=" Лог ", font=lf,
                               fg=M, bg=P, bd=1, relief="flat",
                               highlightbackground=B, highlightthickness=1)
        lframe.pack(fill="both", expand=True, padx=16, pady=(4, 4))
        self.log_box = scrolledtext.ScrolledText(
            lframe, width=54, height=10,
            bg="#0a0a0a", fg="#b0b0b0",
            insertbackground=A,
            font=mo, relief="flat", bd=8, state="disabled")
        self.log_box.pack(fill="both", expand=True)
        self.log_box.tag_config("accent", foreground=A)
        self.log_box.tag_config("green",  foreground=G)
        self.log_box.tag_config("error",  foreground=R)
        self.log_box.tag_config("muted",  foreground=M)

        tk.Button(self, text="Очистить лог", font=("Segoe UI", 8),
                  bg=D, fg=M, activebackground=D, activeforeground=T,
                  relief="flat", bd=0, cursor="hand2",
                  command=self._clear_log).pack(pady=(0, 8))

    def _hotkey_row(self, label, attr, lf, mo):
        D, M = self.DARK, self.MUTED
        f = tk.Frame(self, bg=D, pady=4)
        f.pack(fill="x", padx=16)
        tk.Label(f, text=label, font=lf, fg=M, bg=D, width=12,
                 anchor="w").pack(side="left")
        lbl = tk.Label(f, text="", font=mo, fg=self.TEXT, bg=D)
        lbl.pack(side="left", padx=(4, 0))
        setattr(self, attr, lbl)

    def _entry(self, parent, width, font):
        return tk.Entry(parent, width=width, bg="#1a1a1a", fg=self.TEXT,
                        insertbackground=self.ACCENT, relief="flat", bd=4,
                        font=font, justify="center")

    def _btn(self, parent, text, cmd,
             bg=None, fg=None, active_bg=None, state="normal"):
        bg        = bg        or self.ACCENT
        fg        = fg        or "#000"
        active_bg = active_bg or "#d4aa60"
        return tk.Button(parent, text=text,
                         font=("Segoe UI", 9, "bold"),
                         bg=bg, fg=fg,
                         activebackground=active_bg, activeforeground=fg,
                         relief="flat", bd=0, padx=12, pady=7,
                         cursor="hand2", state=state, command=cmd)

    # ── Reconnect ─────────────────────────────────────────────────────────────
    def _toggle_rc(self):
        state = "normal" if self._var_rc.get() else "disabled"

    def _save_rc(self):
        import re
        time_str = self._ent_rc.get().strip()
        if not re.match(r"^\d{2}:\d{2}$", time_str):
            messagebox.showerror("Ошибка", "Формат времени: ЧЧ:ММ (например 07:00)")
            return
        try:
            cfg = _load_config()
            cfg["reconnect_enabled"] = self._var_rc.get()
            cfg["reconnect_time"]    = time_str
            _save_config(cfg)
            self._log(f"[CFG] Переподключение: {time_str} МСК\n", "accent")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


 
    


    def _save_fe(self):
        try:
            cfg = _load_config()
            cfg["festival_enabled"] = self._var_fe.get()
            _save_config(cfg)
            state = "включено" if self._var_fe.get() else "выключено"
            self._log(f"[CFG] Собирать Событие: {state}\n", "accent")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


    # ── Config ────────────────────────────────────────────────────────────────
    def _load_config_to_ui(self):
        try:
            cfg = _load_config()                          # ← сначала загружаем
            w   = cfg["screen"]["width"]
            h   = cfg["screen"]["height"]
            f5  = cfg.get("hotkey_start_key", "F5")
            f4  = cfg.get("hotkey_pause_key",  "F4")
            f8  = cfg.get("hotkey_stop_key",   "F8")
            rc_on   = cfg.get("reconnect_enabled", False)
            rc_time = cfg.get("reconnect_time", "07:00")
            fe_on = cfg.get("festival_enabled", False)
        except Exception:
            w, h, f5, f4, f8 = 1920, 1080, "F5", "F4", "F8"
            rc_on, rc_time = False, "07:00"
            fe_on = False

        self._var_fe.set(fe_on)
        self._ent_w.delete(0, "end"); self._ent_w.insert(0, str(w))
        self._ent_h.delete(0, "end"); self._ent_h.insert(0, str(h))
        self._lbl_f5.config(text=f5)
        self._lbl_f4.config(text=f4)
        self._lbl_f8.config(text=f8)

        self._var_rc.set(rc_on)
        self._ent_rc.delete(0, "end")
        self._ent_rc.insert(0, rc_time)
        self._toggle_rc()

    def _save_resolution(self):
        try:
            w = int(self._ent_w.get())
            h = int(self._ent_h.get())
            if w <= 0 or h <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные значения.")
            return
        try:
            cfg = _load_config()
            cfg["screen"]["width"]  = w
            cfg["screen"]["height"] = h
            _save_config(cfg)
            self._log(f"[CFG] Разрешение сохранено: {w}×{h}\n", "accent")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # ── Hotkeys ───────────────────────────────────────────────────────────────
    def _bind_hotkeys(self):
        try:
            cfg = _load_config()
            self._scan_start = cfg.get("hotkey_start_scan", 63)
            self._scan_pause = cfg.get("hotkey_pause_scan", 62)
            self._scan_stop  = cfg.get("hotkey_stop_scan",  66)
            keyboard.hook(self._on_key)
        except Exception as e:
            self._log(f"[ERR] hotkeys: {e}\n", "error")

    def _on_key(self, event):
        if event.event_type != "down":
            return
        sc = event.scan_code
        if sc == self._scan_start:
            self.after(0, self._start)
        elif sc == self._scan_pause:
            self.after(0, self._pause)
        elif sc == self._scan_stop:
            self.after(0, self._stop)

    # ── Bot controls ──────────────────────────────────────────────────────────
    def _start(self):
        if self._bot.running:
            return
        try:
            cfg = _load_config()
        except Exception as e:
            self._log(f"[ERR] Конфиг: {e}\n", "error")
            return
        self.lbl_cycles.config(text="Cycles: 0")
        self.lbl_timer.config(text="AFK Time: 00:00:00")
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal")
        self.btn_stop.config(state="normal")
        self.lbl_status.config(text="● работает", fg=self.GREEN)
        self._start_timer()
        self._bot.start(cfg)

    def _pause(self):
        if not self._bot.running:
            return
        is_paused = self._bot.toggle_pause()
        if is_paused:
            self.btn_pause.config(text="  ▶  Продолжить")
            self.lbl_status.config(text="● пауза", fg=self.ACCENT)
            self._log("[||] Пауза\n", "muted")
        else:
            self.btn_pause.config(text="  ⏸  Пауза")
            self.lbl_status.config(text="● работает", fg=self.GREEN)
            self._log("[>>] Продолжено\n", "accent")

    def _stop(self):
        self._bot.stop()
        self._log("[--] Остановка...\n", "muted")

    def _on_ended(self):
        self._stop_timer()
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled", text="  ⏸  Пауза")
        self.btn_stop.config(state="disabled")
        self.lbl_status.config(text="● остановлен", fg=self.MUTED)

    def _update_cycles(self, n):
        self.lbl_cycles.config(text=f"Cycles: {n}")

    # ── Timer ─────────────────────────────────────────────────────────────────
    def _start_timer(self):
        self._tick_timer()

    def _tick_timer(self):
        if self._bot.start_time and self._bot.running and not self._bot.paused:
            el = int(time.time() - self._bot.start_time)
            h, m, s = el // 3600, (el % 3600) // 60, el % 60
            self.lbl_timer.config(text=f"AFK Time: {h:02}:{m:02}:{s:02}")
        self._timer_job = self.after(1000, self._tick_timer)

    def _stop_timer(self):
        if self._timer_job:
            self.after_cancel(self._timer_job)
            self._timer_job = None

    # ── Log ───────────────────────────────────────────────────────────────────
    def _log(self, text, tag=None):
        self.log_box.config(state="normal")
        self.log_box.insert("end", text, tag or "")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def on_close(self):
        self._bot.stop()
        self.after(200, self.destroy)


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = GTA5Launcher()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()