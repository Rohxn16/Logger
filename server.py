import socket
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class LogWriter:
    root: Path = Path("logs")
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _current_day: str | None = field(default=None, init=False)
    _current_hour: int | None = field(default=None, init=False)

    def _day_dir(self, day: str) -> Path:
        return self.root / day

    def _open_for_now(self) -> tuple[datetime, Path]:
        now = datetime.now()
        day = now.strftime("%Y-%m-%d")
        hour = now.hour

        day_dir = self._day_dir(day)
        day_dir.mkdir(parents=True, exist_ok=True)
        log_path = day_dir / "server.log"

        new_day = day != self._current_day
        new_hour = hour != self._current_hour or new_day

        if new_hour:
            with log_path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(f"------------{hour:02d}:00------------------\n")
                f.flush()

        self._current_day = day
        self._current_hour = hour
        return now, log_path

    def write_event(self, text: str, addr: tuple[str, int]) -> None:
        with self._lock:
            now, log_path = self._open_for_now()
            line = f"[{now.strftime('%H:%M:%S')}] [{addr[0]}:{addr[1]}] {text}\n"
            with log_path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(line)
                f.flush()

    def write_msg(self, msg: str, addr: tuple[str, int]) -> None:
        with self._lock:
            _, log_path = self._open_for_now()
            line = f"[{addr[0]}:{addr[1]}] {msg}\n"
            with log_path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(line)
                f.flush()


_logger = LogWriter()


def _handle_client(conn: socket.socket, addr: tuple[str, int]) -> None:
    started_at = datetime.now()
    _logger.write_event(f"TRANSMISSION START ({started_at.isoformat(timespec='seconds')})", addr)
    try:
        with conn:
            buffer = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    msg = line.decode("utf-8", errors="replace").strip()
                    if msg:
                        _logger.write_msg(msg, addr)
    except Exception as e:
        _logger.write_event(f"TRANSMISSION ERROR ({type(e).__name__}: {e})", addr)
    finally:
        ended_at = datetime.now()
        _logger.write_event(f"TRANSMISSION OFF ({ended_at.isoformat(timespec='seconds')})", addr)


def serve(host: str = "127.0.0.1", port: int = 5000) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        print(f"Server listening on {host}:{port}")

        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=_handle_client, args=(conn, addr), daemon=True)
            t.start()


if __name__ == "__main__":
    serve()
