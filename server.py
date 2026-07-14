# -*- coding: utf-8 -*-
"""
대시보드 백엔드 (Python 표준 라이브러리 http.server, 무의존).

정적 파일(web/)과 JSON API 제공.
  GET  /                     -> web/index.html (SPA)
  GET  /api/home             -> 운용사 목록 + 큰 변화 ETF
  GET  /api/manager/<id>     -> 해당 운용사 ETF 카드 목록
  GET  /api/etf/<etf_id>     -> ETF 상세(최신/직전 구성 + 변화)
  POST /api/refresh          -> 최신 영업일 재수집(백그라운드)
  GET  /api/status           -> 재수집 상태
"""
from __future__ import annotations
import os
import json
import threading
import datetime as dt
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import store
import diff
from config import SERVER_HOST, SERVER_PORT

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")

_refresh = {"running": False, "started": None, "finished": None, "log": ""}


def _run_refresh(latest_only: bool = True):
    import ingest
    _refresh.update(running=True, started=dt.datetime.now().isoformat(timespec="seconds"), log="")
    try:
        ingest.ingest_all(latest_only=latest_only)
        _refresh["log"] = "ok"
    except Exception as e:
        _refresh["log"] = f"error: {e!r}"
    finally:
        _refresh.update(running=False, finished=dt.datetime.now().isoformat(timespec="seconds"))


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "ETFDash/1.0"

    def log_message(self, fmt, *args):
        pass  # 조용히

    # -- helpers --
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path):
        ext = os.path.splitext(path)[1].lower()
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            self._json({"error": "not found"}, 404); return
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- routing --
    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        try:
            if p == "/" or p == "/index.html":
                return self._file(os.path.join(WEB, "index.html"))
            if p.startswith("/api/"):
                return self._api_get(p, parse_qs(u.query))
            if p.startswith("/data/"):
                return self._data_get(p)
            # 정적 파일 (web/ 하위만 허용)
            safe = os.path.normpath(p).lstrip("\\/")
            full = os.path.join(WEB, safe)
            if os.path.commonpath([os.path.abspath(full), WEB]) == WEB and os.path.isfile(full):
                return self._file(full)
            self._json({"error": "not found"}, 404)
        except BrokenPipeError:
            pass
        except Exception as e:
            self._json({"error": repr(e)}, 500)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/refresh":
            if _refresh["running"]:
                return self._json({"started": False, "reason": "already running"})
            q = parse_qs(u.query)
            latest_only = q.get("full", ["0"])[0] != "1"
            threading.Thread(target=_run_refresh, args=(latest_only,), daemon=True).start()
            return self._json({"started": True})
        self._json({"error": "not found"}, 404)

    def _data_get(self, p):
        """정적 사이트와 동일한 경로(data/*.json)를 동적으로 제공."""
        if p == "/data/home.json":
            return self._json(diff.home_data())
        if p.startswith("/data/managers/"):
            mid = p.rsplit("/", 1)[-1].replace(".json", "").upper()
            return self._json(diff.manager_payload(mid))
        if p.startswith("/data/etfs/"):
            etf_id = p.rsplit("/", 1)[-1].replace(".json", "")
            return self._json(diff.compute_diff(etf_id))
        self._json({"error": "not found"}, 404)

    def _api_get(self, p, q):
        if p == "/api/home":
            return self._json(diff.home_data())
        if p == "/api/status":
            return self._json(_refresh)
        if p.startswith("/api/manager/"):
            return self._json(diff.manager_payload(p.rsplit("/", 1)[-1].upper()))
        if p.startswith("/api/etf/"):
            etf_id = p.rsplit("/", 1)[-1]
            return self._json(diff.compute_diff(etf_id))
        self._json({"error": "unknown api"}, 404)


def main():
    store.init_db()
    srv = ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), Handler)
    print(f"ETF 대시보드: http://{SERVER_HOST}:{SERVER_PORT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
