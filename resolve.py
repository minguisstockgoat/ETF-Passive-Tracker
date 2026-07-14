# -*- coding: utf-8 -*-
"""
대상 ETF(요청명) -> 운용사별 코드 자동 해석(resolve).

- 캐노니컬 식별: KRX 파인더(전 ETF: 공식명/ISIN/티커)에 유사매칭
- 운용사 코드:
    TIGER -> ISIN(ksdFund)
    SOL   -> SOL 리스트의 FUND_CD (티커 ETF_CD6 로 연결)
    RISE  -> RISE 파인더의 rise_code (공식명으로 연결)
유사매칭 점수를 함께 출력하여 오매칭을 눈으로 확인할 수 있게 한다.
"""
from __future__ import annotations
import re
import difflib
from dataclasses import dataclass, asdict
from typing import Optional

from config import TARGET_ETFS
import fetchers


def _norm(s: str) -> str:
    """비교용 정규화: 공백/특수문자 제거, 소문자."""
    s = re.sub(r"[\s\-&()·,\.\/]", "", s)
    return s.lower()


def _best(target: str, candidates: list[str]) -> tuple[int, float]:
    """candidates 중 target 과 가장 유사한 항목의 (index, score)."""
    tn = _norm(target)
    best_i, best_score = -1, 0.0
    for i, c in enumerate(candidates):
        score = difflib.SequenceMatcher(None, tn, _norm(c)).ratio()
        # 부분포함 가산점 (요청명이 공식명의 앞부분을 이룰 때)
        if tn in _norm(c) or _norm(c) in tn:
            score = max(score, 0.9)
        if score > best_score:
            best_i, best_score = i, score
    return best_i, best_score


@dataclass
class ResolvedETF:
    etf_id: str          # 캐노니컬 id = 티커(6자리)
    manager: str
    request_name: str    # 사용자가 요청한 이름
    name: str            # 공식명(KRX)
    isin: str
    ticker: str
    sol_fund_cd: Optional[str] = None
    rise_code: Optional[str] = None
    match_score: float = 0.0
    note: str = ""


def resolve_all(verbose: bool = True) -> list[ResolvedETF]:
    krx = fetchers.krx_etf_universe()
    krx_names = [x["name"] for x in krx]

    sol_list = fetchers.SolFetcher().list_products()
    sol_names = [x.get("ETF_NAME", "") for x in sol_list]

    rise = fetchers.RiseFetcher()

    resolved: list[ResolvedETF] = []
    seen_ids = set()
    for manager, req_name in TARGET_ETFS:
        # 1) KRX 유사매칭 -> 공식명/ISIN/티커
        i, score = _best(req_name, krx_names)
        krec = krx[i] if i >= 0 else {"isin": "", "ticker": "", "name": req_name}
        note = ""

        r = ResolvedETF(
            etf_id=krec["ticker"] or req_name,
            manager=manager, request_name=req_name,
            name=krec["name"], isin=krec["isin"], ticker=krec["ticker"],
            match_score=round(score, 3),
        )

        # 2) 운용사별 코드
        if manager == "SOL":
            # 티커로 SOL 리스트 연결, 실패 시 이름 유사매칭
            fund = next((x for x in sol_list if str(x.get("ETF_CD6")) == r.ticker), None)
            if fund is None:
                j, sc = _best(req_name, sol_names)
                fund = sol_list[j] if j >= 0 else None
                if fund is not None:
                    note += f"SOL이름매칭({sc:.2f}) "
                    # SOL 리스트 기준으로 티커/이름 보정
                    r.ticker = str(fund.get("ETF_CD6") or r.ticker)
                    r.etf_id = r.ticker
                    if not r.name:
                        r.name = fund.get("ETF_NAME", req_name)
            if fund is not None:
                r.sol_fund_cd = str(fund.get("FUND_CD"))
            else:
                note += "SOL-FUND_CD미해결 "

        elif manager == "RISE":
            # 파인더 검색 결과 카드에서 정확 매칭 (인버스/커버드콜 변형 배제)
            cands = rise.search(r.name or req_name)
            cnames = [c["name"] for c in cands]
            j, sc = _best(r.name or req_name, cnames) if cnames else (-1, 0.0)
            if j >= 0 and sc >= 0.7:
                r.rise_code = cands[j]["rise_code"]
                note += f"RISE매칭({sc:.2f}:{cnames[j]}) "
            else:
                note += "RISE-code미해결 "

        # TIGER 는 ISIN 그대로 사용
        if manager == "TIGER" and not r.isin:
            note += "TIGER-ISIN미해결 "

        r.note = note.strip()
        if r.etf_id in seen_ids:
            r.note = (r.note + " [중복]").strip()
            continue
        seen_ids.add(r.etf_id)
        resolved.append(r)

    if verbose:
        print(f"{'요청명':<28}{'공식명(KRX)':<30}{'티커':<8}{'score':<7}{'코드':<12}{'note'}")
        print("-" * 110)
        for r in resolved:
            code = r.sol_fund_cd or r.rise_code or r.isin or ""
            print(f"{r.request_name:<28}{r.name:<30}{r.ticker:<8}{r.match_score:<7}{str(code):<12}{r.note}")
    return resolved


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    resolve_all(verbose=True)
