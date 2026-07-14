# -*- coding: utf-8 -*-
"""
수집 오케스트레이션: 코드해석 -> 구성종목 fetch -> 스냅샷 저장.

  py ingest.py             # 전체 해석 + 과거 백필(TIGER/RISE) + 최신(SOL)
  py ingest.py --latest    # 최신 영업일 1개만 (일일 갱신용)
  py ingest.py --days 10   # 백필 영업일 수 지정
"""
from __future__ import annotations
import sys
import time
import argparse
import datetime as dt

import store
import resolve
import fetchers
from config import BACKFILL_BIZ_DAYS


def business_days_back(latest: dt.date, n: int) -> list[dt.date]:
    """latest(포함)부터 과거로 영업일(주말 제외) n개."""
    out, d = [], latest
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= dt.timedelta(days=1)
    return out


def _store_series(etf_id: str, dates: list[dt.date], fetch_fn, source: str) -> int:
    """dates(최신순)에 대해 fetch/저장. 휴일 phantom 중복은 스킵. 저장한 일자 수 반환."""
    stored, last_sig = 0, None
    for d in dates:
        try:
            holdings = fetch_fn(d)
        except Exception as e:
            print(f"    ! {d} fetch 실패: {e!r}")
            continue
        if not holdings:
            continue
        sig = frozenset((h.stock_code, round(h.weight, 2)) for h in holdings)
        if sig == last_sig:        # 직전 저장분과 동일 = 휴일/미갱신 → 스킵
            continue
        bd = d.strftime("%Y%m%d")
        store.save_snapshot(etf_id, bd, holdings, source)
        last_sig = sig
        stored += 1
        time.sleep(0.12)
    return stored


def update_info_all() -> None:
    """ETF 개요(기초지수·구성방식·보수 등) 수집·저장. 스냅샷과 무관, 가끔만 갱신."""
    store.init_db()
    tiger, sol, rise = fetchers.TigerFetcher(), fetchers.SolFetcher(), fetchers.RiseFetcher()
    print("== ETF 개요 정보 수집 ==")
    for e in store.list_etfs():
        try:
            if e["manager"] == "TIGER" and e.get("isin"):
                info = tiger.info(e["isin"])
            elif e["manager"] == "SOL" and e.get("sol_fund_cd"):
                info = sol.info(e["sol_fund_cd"])
            elif e["manager"] == "RISE" and e.get("rise_code"):
                info = rise.info(e["rise_code"])
            else:
                info = {}
            index_name = info.pop("index_name", None)
            index_desc = info.pop("index_desc", None)
            info["method"] = fetchers.derive_method(e.get("name", ""), index_name or "")
            store.update_info(e["etf_id"], index_name, index_desc, info)
            print(f"  [{e['manager']}] {e['name']}: 지수={index_name} 보수={info.get('fee')} 상장={info.get('listing')}")
        except Exception as ex:
            print(f"  [{e['manager']}] {e['name']}: info 오류 {ex!r}")


def ingest_all(backfill_days: int = BACKFILL_BIZ_DAYS, latest_only: bool = False) -> None:
    store.init_db()
    print("== 코드 해석 ==")
    etfs = resolve.resolve_all(verbose=True)
    for r in etfs:
        store.upsert_etf(r)

    tiger, sol, rise = fetchers.TigerFetcher(), fetchers.SolFetcher(), fetchers.RiseFetcher()
    today = dt.date.today()
    ndays = 1 if latest_only else backfill_days

    print(f"\n== 구성종목 수집 (backfill={ndays}일{' [latest]' if latest_only else ''}) ==")
    for r in etfs:
        tag = f"[{r.manager}] {r.name}({r.etf_id})"
        try:
            if r.manager == "TIGER":
                if not r.isin:
                    print(f"  {tag}: ISIN 없음, 스킵"); continue
                latest = tiger.latest_date(r.isin) or (today - dt.timedelta(days=1))
                dates = business_days_back(latest, ndays)
                n = _store_series(r.etf_id, dates, lambda d: tiger.fetch(r.isin, d), "TIGER")

            elif r.manager == "RISE":
                if not r.rise_code:
                    print(f"  {tag}: rise_code 없음, 스킵"); continue
                latest = rise.latest_date(r.rise_code) or today
                dates = business_days_back(latest, ndays)
                n = _store_series(r.etf_id, dates, lambda d: rise.fetch(r.rise_code, d), "RISE")

            elif r.manager == "SOL":
                if not r.sol_fund_cd:
                    print(f"  {tag}: FUND_CD 없음, 스킵"); continue
                holdings, work_dt = sol.fetch(r.sol_fund_cd)
                n = 1 if store.save_snapshot(r.etf_id, work_dt, holdings, "SOL") else 0
            else:
                n = 0
            dates_have = store.get_dates(r.etf_id)
            print(f"  {tag}: +{n}일 저장, 보유일수 {len(dates_have)} 최신 {dates_have[0] if dates_have else '-'}")
        except Exception as e:
            print(f"  {tag}: 오류 {e!r}")

    update_info_all()
    print("\n완료.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--latest", action="store_true", help="최신 1영업일만")
    ap.add_argument("--days", type=int, default=BACKFILL_BIZ_DAYS, help="백필 영업일 수")
    ap.add_argument("--info", action="store_true", help="개요 정보만 갱신")
    a = ap.parse_args()
    if a.info:
        update_info_all()
    else:
        ingest_all(backfill_days=a.days, latest_only=a.latest)
