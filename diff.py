# -*- coding: utf-8 -*-
"""
일간 구성 변화 계산.

핵심: 구성비중(%)은 보유종목의 '가격 변동'만으로도 매일 바뀌므로 홈에서는 의미가 약하다.
따라서 홈은 **CU(설정단위)당 개별 종목의 보유주수(수량)가 실제로 바뀐 경우 = 리밸런싱**
(편입/편출/주수 증감)을 선별해 보여준다. (현금성·스왑 등 비주식은 제외)

- 종목별: 비중 변화(%p), 보유수량 변화, 편입/편출  (상세 화면용)
- ETF별 요약: 리밸런싱 종목 수(편입/편출/주수변경), 거래비중(주수변동 평가액/CU가치), 대표 변동종목
"""
from __future__ import annotations
from typing import Optional
import json

import store
from config import MANAGERS


def _fmt_date(yyyymmdd: str) -> str:
    if yyyymmdd and len(yyyymmdd) == 8:
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return yyyymmdd or ""


def _is_cash(code: str, name: str) -> bool:
    """현금성·스왑·예금 등 비주식(리밸런싱 판정 제외 대상)."""
    c = (code or "").upper()
    if c.startswith(("KRD", "CASH", "SWAP", "MMF", "KRW", "KR4")):
        return True
    n = (name or "").replace(" ", "")
    return any(k in n for k in ["현금", "예금", "설정", "스왑", "콜론", "환매조건부", "RP", "유동성"])


def compute_diff(etf_id: str) -> dict:
    """ETF 상세: 최신/직전 구성 + 종목별 변화."""
    etf = store.get_etf(etf_id) or {"etf_id": etf_id}
    dates = store.get_dates(etf_id)
    latest = dates[0] if dates else None
    prev = dates[1] if len(dates) > 1 else None

    latest_rows = store.get_holdings(etf_id, latest) if latest else []
    prev_rows = store.get_holdings(etf_id, prev) if prev else []
    lmap = {r["stock_code"]: r for r in latest_rows}
    pmap = {r["stock_code"]: r for r in prev_rows}

    rows = []
    for code in set(lmap) | set(pmap):
        l = lmap.get(code)
        p = pmap.get(code)
        name = (l or p)["stock_name"]
        w_l = l["weight"] if l else 0.0
        w_p = p["weight"] if p else 0.0
        sh_l = l["shares"] if l else 0.0
        sh_p = p["shares"] if p else 0.0
        amt_l = l["amount"] if l else 0.0
        amt_p = p["amount"] if p else 0.0
        status = "new" if (l and not p) else ("removed" if (p and not l) else "same")

        # 주수변동 평가액(거래액 추정): same=Δ수량×현재가, new=편입액, removed=편출액
        price_l = (amt_l / sh_l) if sh_l else 0.0
        if status == "same":
            traded = abs(sh_l - sh_p) * price_l
        elif status == "new":
            traded = amt_l
        else:
            traded = amt_p
        cash = _is_cash(code, name)
        share_changed = (not cash) and (status != "same" or abs(sh_l - sh_p) > 1e-6)

        rows.append({
            "stock_code": code, "stock_name": name,
            "weight": round(w_l, 3), "weight_prev": round(w_p, 3), "weight_delta": round(w_l - w_p, 3),
            "shares": sh_l, "shares_prev": sh_p, "shares_delta": round(sh_l - sh_p, 4),
            "amount": amt_l, "amount_prev": amt_p,
            "status": status, "is_cash": cash,
            "share_changed": bool(prev and share_changed),
            "traded": traded,
        })

    rows.sort(key=lambda x: (x["status"] == "removed", -(x["weight"] or x["weight_prev"])))
    summary = _summarize(rows, latest_rows, has_prev=prev is not None)

    info = {
        "index_name": etf.get("index_name"),
        "index_desc": etf.get("index_desc"),
    }
    try:
        info.update(json.loads(etf.get("info_json") or "{}"))
    except Exception:
        pass

    return {
        "etf_id": etf_id, "manager": etf.get("manager"), "name": etf.get("name"),
        "request_name": etf.get("request_name"), "ticker": etf.get("ticker"),
        "latest_date": _fmt_date(latest) if latest else None,
        "prev_date": _fmt_date(prev) if prev else None,
        "has_prev": prev is not None,
        "available_dates": [_fmt_date(d) for d in dates],
        "n_holdings": len(latest_rows),
        "rows": [{k: v for k, v in r.items() if k != "traded"} for r in rows],
        "summary": summary,
        "info": info,
    }


def _summarize(rows: list[dict], latest_rows: list[dict], has_prev: bool) -> dict:
    total_val = sum(r["amount"] for r in latest_rows) or 1.0

    stock_rows = [r for r in rows if not r["is_cash"]]
    changed = [r for r in stock_rows if r["share_changed"] and r["status"] == "same"]
    news = [r for r in stock_rows if r["status"] == "new"]
    removed = [r for r in stock_rows if r["status"] == "removed"]

    n_share_changed = len(changed)
    n_new, n_removed = len(news), len(removed)
    n_rebalanced = n_share_changed + n_new + n_removed
    share_turnover = round(sum(r["traded"] for r in (changed + news + removed)) / total_val * 100, 3) if has_prev else 0.0

    # 대표 변동 종목(주수변동 평가액 큰 순)
    movers = sorted(changed + news + removed, key=lambda x: -x["traded"])
    top_changes = [{
        "name": r["stock_name"], "shares_delta": r["shares_delta"],
        "status": r["status"], "weight": r["weight"], "weight_prev": r["weight_prev"],
    } for r in movers[:6]]

    # 비중(가격변동 포함) 요약 - 상세화면 보조용
    turnover = round(sum(abs(r["weight_delta"]) for r in rows) / 2.0, 3) if has_prev else 0.0
    max_abs = max((abs(r["weight_delta"]) for r in rows), default=0.0) if has_prev else 0.0

    return {
        "n_share_changed": n_share_changed, "n_new": n_new, "n_removed": n_removed,
        "n_rebalanced": n_rebalanced, "share_turnover": share_turnover,
        "is_rebalanced": bool(has_prev and n_rebalanced > 0),
        "top_changes": top_changes,
        "new_names": [r["stock_name"] for r in news][:5],
        "removed_names": [r["stock_name"] for r in removed][:5],
        # 비중 기준(참고)
        "turnover": turnover, "max_abs_delta": round(max_abs, 3),
    }


def etf_card(etf_id: str) -> dict:
    d = compute_diff(etf_id)
    return {
        "etf_id": etf_id, "manager": d["manager"], "name": d["name"],
        "request_name": d["request_name"], "ticker": d["ticker"],
        "latest_date": d["latest_date"], "prev_date": d["prev_date"],
        "has_prev": d["has_prev"], "n_holdings": d["n_holdings"],
        "summary": d["summary"], "info": {"index_name": d["info"].get("index_name")},
    }


def manager_payload(mid: str) -> dict:
    """특정 운용사의 ETF 카드 목록(리밸런싱 큰 순)."""
    cards = [etf_card(e["etf_id"]) for e in store.list_etfs() if e["manager"] == mid]
    cards.sort(key=lambda c: (c["summary"]["is_rebalanced"], c["summary"]["n_rebalanced"],
                              c["summary"]["share_turnover"]), reverse=True)
    return {"manager": mid, "etfs": cards}


def home_data() -> dict:
    """초기화면: 운용사별 목록 + 오늘 보유수량(리밸런싱) 변화 ETF."""
    etfs = store.list_etfs()
    cards = [etf_card(e["etf_id"]) for e in etfs]

    managers = []
    for mid, minfo in MANAGERS.items():
        m_cards = [c for c in cards if c["manager"] == mid]
        managers.append({
            "id": mid, "name": minfo["name"], "company": minfo["company"], "color": minfo["color"],
            "n_etf": len(m_cards),
            "n_rebalanced": sum(1 for c in m_cards if c["summary"]["is_rebalanced"]),
        })

    rebal = [c for c in cards if c["summary"]["is_rebalanced"]]
    rebal.sort(key=lambda c: (c["summary"]["n_rebalanced"], c["summary"]["share_turnover"]), reverse=True)

    latest_dates = sorted({c["latest_date"] for c in cards if c["latest_date"]}, reverse=True)
    return {
        "managers": managers,
        "rebalanced": rebal,
        "as_of": latest_dates[0] if latest_dates else None,
        "n_total": len(cards),
        "n_no_prev": sum(1 for c in cards if not c["has_prev"]),
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    hd = home_data()
    print("as_of:", hd["as_of"], "총 ETF:", hd["n_total"], "비교불가:", hd["n_no_prev"])
    print("운용사:", [(m["id"], m["n_etf"], f"rebal={m['n_rebalanced']}") for m in hd["managers"]])
    print("\n보유수량 변화(리밸런싱) ETF:")
    for c in hd["rebalanced"]:
        s = c["summary"]
        tops = ", ".join(f"{t['name']}{'+' if t['shares_delta']>=0 else ''}{int(t['shares_delta'])}주"
                         for t in s["top_changes"][:3])
        print(f"  {c['manager']:<6}{c['name']:<26} 변경 {s['n_rebalanced']:>2}종목 "
              f"(편입{s['n_new']}/편출{s['n_removed']}/주수{s['n_share_changed']}) "
              f"거래비중 {s['share_turnover']:>5}%  [{tops}]  {c['prev_date']}→{c['latest_date']}")
