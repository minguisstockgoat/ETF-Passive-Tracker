# -*- coding: utf-8 -*-
"""SQLite 저장소: ETF 메타 + 일자별 구성종목 스냅샷 + 수집로그."""
from __future__ import annotations
import os
import sqlite3
import datetime as dt
from typing import Optional

from config import DB_PATH


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS etfs(
                etf_id       TEXT PRIMARY KEY,   -- 티커(6자리) = 캐노니컬 id
                manager      TEXT,               -- SOL / RISE / TIGER
                name         TEXT,               -- 공식명(KRX)
                request_name TEXT,               -- 사용자 요청명
                isin         TEXT,
                ticker       TEXT,
                sol_fund_cd  TEXT,
                rise_code    TEXT,
                updated_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS snapshots(
                etf_id     TEXT,
                base_date  TEXT,                 -- 'YYYYMMDD' (구성 기준일)
                stock_code TEXT,
                stock_name TEXT,
                shares     REAL,
                amount     REAL,
                weight     REAL,                 -- 구성비중(%)
                PRIMARY KEY(etf_id, base_date, stock_code)
            );
            CREATE TABLE IF NOT EXISTS fetch_log(
                etf_id     TEXT,
                base_date  TEXT,
                fetched_at TEXT,
                n          INTEGER,
                source     TEXT,
                PRIMARY KEY(etf_id, base_date)
            );
            CREATE INDEX IF NOT EXISTS idx_snap ON snapshots(etf_id, base_date);
            """
        )
        # 개요 정보 컬럼(기초지수/설명/기타 JSON) - 없으면 추가
        cols = {r[1] for r in c.execute("PRAGMA table_info(etfs)").fetchall()}
        for col in ("index_name", "index_desc", "info_json"):
            if col not in cols:
                c.execute(f"ALTER TABLE etfs ADD COLUMN {col} TEXT")


def update_info(etf_id: str, index_name=None, index_desc=None, info: dict | None = None) -> None:
    import json as _json
    with _conn() as c:
        c.execute(
            "UPDATE etfs SET index_name=?, index_desc=?, info_json=? WHERE etf_id=?",
            (index_name, index_desc, _json.dumps(info or {}, ensure_ascii=False), etf_id),
        )


def upsert_etf(r) -> None:
    """r: resolve.ResolvedETF 또는 dict."""
    d = r if isinstance(r, dict) else r.__dict__
    with _conn() as c:
        c.execute(
            """INSERT INTO etfs(etf_id,manager,name,request_name,isin,ticker,sol_fund_cd,rise_code,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(etf_id) DO UPDATE SET
                 manager=excluded.manager, name=excluded.name, request_name=excluded.request_name,
                 isin=excluded.isin, ticker=excluded.ticker, sol_fund_cd=excluded.sol_fund_cd,
                 rise_code=excluded.rise_code, updated_at=excluded.updated_at""",
            (d["etf_id"], d["manager"], d.get("name"), d.get("request_name"), d.get("isin"),
             d.get("ticker"), d.get("sol_fund_cd"), d.get("rise_code"),
             dt.datetime.now().isoformat(timespec="seconds")),
        )


def save_snapshot(etf_id: str, base_date: str, holdings: list, source: str = "") -> int:
    """holdings: list[Holding]. 해당 (etf,date) 스냅샷을 교체 저장. 저장 행 수 반환."""
    if not holdings:
        return 0
    with _conn() as c:
        c.execute("DELETE FROM snapshots WHERE etf_id=? AND base_date=?", (etf_id, base_date))
        c.executemany(
            "INSERT OR REPLACE INTO snapshots VALUES(?,?,?,?,?,?,?)",
            [(etf_id, base_date, h.stock_code, h.stock_name, h.shares, h.amount, h.weight)
             for h in holdings],
        )
        c.execute(
            "INSERT OR REPLACE INTO fetch_log VALUES(?,?,?,?,?)",
            (etf_id, base_date, dt.datetime.now().isoformat(timespec="seconds"), len(holdings), source),
        )
    return len(holdings)


def signature(etf_id: str, base_date: str) -> frozenset:
    """구성 시그니처(code, 비중 2자리) - 휴일 phantom 중복 감지용."""
    rows = get_holdings(etf_id, base_date)
    return frozenset((r["stock_code"], round(r["weight"], 2)) for r in rows)


def get_dates(etf_id: str) -> list[str]:
    """해당 ETF의 스냅샷 기준일들(최신순)."""
    with _conn() as c:
        rows = c.execute(
            "SELECT DISTINCT base_date FROM snapshots WHERE etf_id=? ORDER BY base_date DESC",
            (etf_id,),
        ).fetchall()
    return [r["base_date"] for r in rows]


def get_holdings(etf_id: str, base_date: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT stock_code,stock_name,shares,amount,weight FROM snapshots "
            "WHERE etf_id=? AND base_date=? ORDER BY weight DESC",
            (etf_id, base_date),
        ).fetchall()
    return [dict(r) for r in rows]


def list_etfs() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM etfs ORDER BY manager, name").fetchall()
    return [dict(r) for r in rows]


def get_etf(etf_id: str) -> Optional[dict]:
    with _conn() as c:
        r = c.execute("SELECT * FROM etfs WHERE etf_id=?", (etf_id,)).fetchone()
    return dict(r) if r else None


def has_date(etf_id: str, base_date: str) -> bool:
    with _conn() as c:
        r = c.execute(
            "SELECT 1 FROM snapshots WHERE etf_id=? AND base_date=? LIMIT 1", (etf_id, base_date)
        ).fetchone()
    return r is not None


if __name__ == "__main__":
    init_db()
    print("DB initialized at", DB_PATH)
