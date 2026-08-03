"""TCP relay: WSL-facing interface -> Edge's CDP on 127.0.0.1:9222.

Edge binds its remote-debugging port to loopback only, which WSL2 (NAT mode)
cannot reach. This relay listens on the vEthernet (WSL) address and pipes
bytes both ways, so Playwright inside WSL can drive the robot Edge.

Usage: python cdp_relay.py <listen_ip> [listen_port] [target_port]
"""
import socket
import sys
import threading


def say(*a):
    try:
        print(*a, flush=True)
    except Exception:
        pass  # detached console gone — keep serving


def pipe(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def serve(listen_ip, listen_port, target_port):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((listen_ip, listen_port))
    srv.listen(16)
    say(f"relay: {listen_ip}:{listen_port} -> 127.0.0.1:{target_port}")
    while True:
        cli, addr = srv.accept()
        try:
            up = socket.create_connection(("127.0.0.1", target_port), timeout=5)
        except OSError as e:
            say("upstream connect failed:", e)
            cli.close()
            continue
        threading.Thread(target=pipe, args=(cli, up), daemon=True).start()
        threading.Thread(target=pipe, args=(up, cli), daemon=True).start()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    lp = int(sys.argv[2]) if len(sys.argv) > 2 else 9223
    tp = int(sys.argv[3]) if len(sys.argv) > 3 else 9222
    serve(ip, lp, tp)
