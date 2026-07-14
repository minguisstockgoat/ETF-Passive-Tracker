# -*- coding: utf-8 -*-
"""
정적 사이트 빌드 (GitHub Pages 배포용).

DB(data/etf.db)의 현재 상태를 읽어 서버 API와 동일한 JSON을 파일로 생성하고
프런트엔드(web/)를 docs/ 로 복사한다. -> docs/ 를 GitHub Pages로 서빙하면 끝.

  py build_static.py            # docs/ 생성
  py -m http.server 8860 --directory docs   # 로컬 미리보기
"""
from __future__ import annotations
import os
import json
import shutil

import store
import diff
from config import MANAGERS

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
OUT = os.path.join(HERE, "docs")


def _write(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def build() -> None:
    store.init_db()
    etfs = store.list_etfs()
    if not etfs:
        print("!! DB에 ETF가 없습니다. 먼저 `py ingest.py` 를 실행하세요.")
        return

    # 1) 프런트엔드 정적 자원 복사
    os.makedirs(OUT, exist_ok=True)
    for fn in ("index.html", "style.css", "app.js"):
        shutil.copyfile(os.path.join(WEB, fn), os.path.join(OUT, fn))
    # GitHub Pages 가 Jekyll 처리 없이 폴더/파일 그대로 서빙하도록
    open(os.path.join(OUT, ".nojekyll"), "w").close()

    # 2) 데이터 JSON 생성 (서버 API와 동일 스키마)
    home = diff.home_data()
    _write(os.path.join(OUT, "data", "home.json"), home)

    for mid in MANAGERS:
        _write(os.path.join(OUT, "data", "managers", f"{mid}.json"), diff.manager_payload(mid))

    n = 0
    for e in etfs:
        _write(os.path.join(OUT, "data", "etfs", f"{e['etf_id']}.json"), diff.compute_diff(e["etf_id"]))
        n += 1

    print(f"docs/ 생성 완료 · ETF {n}종 · 기준일 {home.get('as_of')} · 리밸런싱 {len(home.get('rebalanced', []))}종")
    print(f"  미리보기: py -m http.server 8860 --directory \"{OUT}\"")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    build()
