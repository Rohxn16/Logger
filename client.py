import random
import socket
import time
from pathlib import Path
import queue
from datetime import datetime
from pynput import keyboard


def run(host: str = "127.0.0.1", port: int = 5000) -> None:
    buffer_path = Path(f".client_buffer_{host}_{port}.txt".replace(":", "_"))

    def _append_to_buffer(n: int) -> None:
        buffer_path.parent.mkdir(parents=True, exist_ok=True)
        with buffer_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(f"{n}\n")
            f.flush()

    def _flush_buffer(sock: socket.socket) -> None:
        if not buffer_path.exists():
            return

        lines = buffer_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not lines:
            buffer_path.unlink(missing_ok=True)
            return

        sent_upto = 0
        try:
            for i, line in enumerate(lines):
                msg = line.strip()
                if not msg:
                    sent_upto = i + 1
                    continue
                sock.sendall(f"{msg}\n".encode("utf-8"))
                sent_upto = i + 1
        except (ConnectionError, OSError):
            remaining = [ln for ln in lines[sent_upto:] if ln.strip()]
            if remaining:
                buffer_path.write_text("\n".join(remaining) + "\n", encoding="utf-8", newline="\n")
            else:
                buffer_path.unlink(missing_ok=True)
            raise

        buffer_path.unlink(missing_ok=True)

    while True:
        try:
            with socket.create_connection((host, port), timeout=10) as s:
                print(f"Connected to {host}:{port}")
                _flush_buffer(s)
                while True:
                    n = random.randint(0, 1_000_000)
                    try:
                        payload = f"{n}\n".encode("utf-8")
                        s.sendall(payload)
                        print(f"Sent: {n}")
                    except (ConnectionError, OSError) as e:
                        _append_to_buffer(n)
                        print(f"Send failed ({e}); buffered {n} and reconnecting...")
                        time.sleep(2)
                        break

                    time.sleep(10)
        except (ConnectionError, OSError) as e:
            n = random.randint(0, 1_000_000)
            _append_to_buffer(n)
            print(f"Connection failed ({e}); buffered {n}; retrying in 10s...")
            time.sleep(10)


if __name__ == "__main__":
    run()
