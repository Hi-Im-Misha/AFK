# ── AFK Bot logic ─────────────────────────────────────────────────────────────
import time
import threading
import pyautogui
import keyboard
from datetime import datetime, timezone, timedelta

class AFKBot:
    def __init__(self, log_fn, on_end_fn, on_cycle_fn):
        self.log       = log_fn
        self.on_end    = on_end_fn
        self.on_cycle  = on_cycle_fn
        self._stop_evt = threading.Event()
        self._pause_evt= threading.Event()   # set = paused
        self._thread   = None
        self.cycles    = 0
        self.start_time: float | None = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def paused(self):
        return self._pause_evt.is_set()

    def start(self, cfg):
        if self.running:
            return
        self._stop_evt.clear()
        self._pause_evt.clear()
        self.cycles     = 0
        self.start_time = time.time()
        self._thread = threading.Thread(
            target=self._loop, args=(cfg,), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        self._pause_evt.clear()
        keyboard.release("w")
        keyboard.release("s")

    def toggle_pause(self):
        if self._pause_evt.is_set():
            self._pause_evt.clear()
        else:
            self._pause_evt.set()
        return self._pause_evt.is_set()

    # ── coordinates scaled to current resolution ──────────────────────────────
    @staticmethod
    def _scale(x, y, w, h):
        sx = w / 1920
        sy = h / 1080
        return int(x * sx), int(y * sy)

    def _wait(self, seconds):
        """Interruptible sleep that also respects pause."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            if self._stop_evt.is_set():
                return False
            if self._pause_evt.is_set():
                time.sleep(0.1)
                deadline += 0.1
                continue
            time.sleep(0.05)
        return True


    # внутри класса AFKBot добавить метод
    def _reconnect(self):
        """Переподключение к серверу (F5 → ждём → /reconnect)"""
        self.log("[>>] Переподключение к серверу...\n", "accent")
        keyboard.release("w")
        keyboard.release("s")

        

        pyautogui.press("f5")
        self._wait(3)



    def _loop(self, cfg):
        pyautogui.FAILSAFE = True
        w = cfg["screen"]["width"]
        h = cfg["screen"]["height"]

        self.log("[>>] Бот запущен\n", "accent")

        while not self._stop_evt.is_set():
            # ---- wait while paused ----
            while self._pause_evt.is_set():
                if self._stop_evt.is_set():
                    break
                time.sleep(0.5)
            if self._stop_evt.is_set():
                break

            # ---- roulette sequence ----
            pyautogui.press("f10")
            if not self._wait(0.5): break

            for raw_x, raw_y in [(1282, 272), (576, 335),
                                (760, 640), (960, 906)]:
                cx, cy = self._scale(raw_x, raw_y, w, h)
                pyautogui.click(cx, cy)
                if not self._wait(0.5): break
            else:
                if not self._wait(0.5): break
                pyautogui.press("escape")
                if not self._wait(0.5): break
                pyautogui.press("escape")
                if not self._wait(0.5): break

                # ---- hold W + S for 5 minutes ----
                self.log("[..] Удержание W+S (5 мин)\n", "muted")
                keyboard.press("w")
                keyboard.press("s")
                if not self._wait(300):
                    keyboard.release("w")
                    keyboard.release("s")
                    break
                keyboard.release("w")
                keyboard.release("s")

                self.cycles += 1
                self.on_cycle(self.cycles)
                self.log(f"[>>] Цикл #{self.cycles} завершён\n", "accent")
                if not self._wait(1):
                    break
                continue


            if cfg.get("reconnect_enabled") and cfg.get("reconnect_time"):
                msk = datetime.now(timezone(timedelta(hours=3)))
                if msk.strftime("%H:%M") == cfg["reconnect_time"]:
                    self._reconnect()
                    self._wait(60)
                    continue


            break

        keyboard.release("w")
        keyboard.release("s")
        self.log("[--] Бот остановлен\n", "muted")
        self.on_end()


