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
        self._pause_evt= threading.Event()
        self._reconnect_evt = threading.Event()  # ← добавить
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

        if cfg.get("reconnect_enabled") and cfg.get("reconnect_time"):
            threading.Thread(target=self._scheduler, args=(cfg,), daemon=True).start()


    def _scheduler(self, cfg):
        """Следит за временем независимо от основного цикла"""
        target = cfg["reconnect_time"]
        while not self._stop_evt.is_set():
            msk_str = datetime.now(timezone(timedelta(hours=3))).strftime("%H:%M")
            if msk_str == target:
                self.log(f"[SCH] Время {target} МСК — запускаю переподключение\n", "accent")
                self._reconnect_evt.set()
                time.sleep(61)  # ждём минуту чтоб не срабатывало повторно
            time.sleep(30)

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

    @staticmethod
    def _scale(x, y, w, h):
        sx = w / 1920
        sy = h / 1080
        return int(x * sx), int(y * sy)

    def _wait(self, seconds):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if self._stop_evt.is_set():
                return False
            if self._reconnect_evt.is_set():
                return False
            if self._pause_evt.is_set():
                deadline += 0.1
                time.sleep(0.1)
                continue
            time.sleep(min(1.0, deadline - time.time()))  # ← не выходим за deadline
        return True

    def _reconnect(self):
        self.log("[>>] Переподключение к серверу...\n", "accent")
        keyboard.release("w")
        keyboard.release("s")
        pyautogui.press("f1")
        self._wait(0.2)

        screen_w, screen_h = pyautogui.size()
        pyautogui.FAILSAFE = False
        pyautogui.click(screen_w - 230, 20)
        pyautogui.FAILSAFE = True
        self._wait(2)
        pyautogui.click(screen_w - 730, 550)
        self._wait(3)
        
    def _loop(self, cfg):
        pyautogui.FAILSAFE = True
        w = cfg["screen"]["width"]
        h = cfg["screen"]["height"]

        self.log("[>>] Бот запущен\n", "accent")

        while not self._stop_evt.is_set():

            if self._reconnect_evt.is_set():
                self._reconnect_evt.clear()
                keyboard.release("w")
                keyboard.release("s")
                self._reconnect()
                continue
            

            # ---- wait while paused ----
            while self._pause_evt.is_set():
                if self._stop_evt.is_set():
                    break
                time.sleep(0.5)
            if self._stop_evt.is_set():
                break

            # ---- reconnect by schedule ---- (начало каждого цикла)
            if cfg.get("reconnect_enabled") and cfg.get("reconnect_time"):
                msk = datetime.now(timezone(timedelta(hours=3)))
                msk_str = msk.strftime("%H:%M")
                self.log(f"[DBG] МСК: {msk_str} | цель: {cfg['reconnect_time']}\n", "muted")
                # if True:
                if msk_str == cfg["reconnect_time"]:
                    self._reconnect()
                    if not self._wait(60):
                        break
                    continue

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
                    if self._reconnect_evt.is_set():   # ← прервал планировщик
                        self._reconnect_evt.clear()
                        self._reconnect()
                        continue                        # ← продолжаем цикл, не останавливаемся
                    break                              # ← прервал stop()
                keyboard.release("w")
                keyboard.release("s")

                self.cycles += 1
                self.on_cycle(self.cycles)
                self.log(f"[>>] Цикл #{self.cycles} завершён\n", "accent")
                if not self._wait(1):
                    break
                continue

            break  # inner for-else broke early

        keyboard.release("w")
        keyboard.release("s")
        self.log("[--] Бот остановлен\n", "muted")
        self.on_end()


if __name__ == "__main__":
    def log(text, tag=None):
        print(text, end="")

    bot = AFKBot(
        log_fn      = log,
        on_end_fn   = lambda: print("[END]"),
        on_cycle_fn = lambda n: print(f"[CYCLE] {n}"),
    )

    cfg = {
        "screen": {"width": 1920, "height": 1080},
        "reconnect_enabled": True,
        "reconnect_time": "18:05",  # ← сюда вставь текущее МСК время для теста
    }

    bot.start(cfg)

    import time
    time.sleep(90)  # ждём 30 сек и смотрим лог
    bot.stop()