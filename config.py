# -*- coding: utf-8 -*-
"""
패시브 ETF 구성비중 추적 대시보드 - 설정.

대상 ETF 목록(운용사별)과 운용사별 데이터 소스(구성종목 PDF) 정의.
실제 종목코드/식별자는 resolve.py 가 각 운용사/KRX 리스트에 자동 매칭한다.
"""
from __future__ import annotations
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "data", "etf.db")

# 운용사 표시 정보 -----------------------------------------------------------
MANAGERS = {
    "SOL":   {"name": "SOL ETF",   "company": "신한자산운용", "color": "#0046ff"},
    "RISE":  {"name": "RISE ETF",  "company": "KB자산운용",   "color": "#ffb800"},
    "TIGER": {"name": "TIGER ETF", "company": "미래에셋자산운용", "color": "#ff6a00"},
}

# 사용자가 요청한 대상 ETF (운용사, 요청명) --------------------------------
# 요청명은 공식명과 약간 다를 수 있어 resolve.py 에서 유사매칭으로 보정한다.
TARGET_ETFS = [
    # --- SOL (신한) ---
    ("SOL",   "SOL AI반도체TOP2플러스"),
    ("SOL",   "SOL 조선TOP3플러스"),
    ("SOL",   "SOL AI반도체소부장"),
    # --- RISE (KB) ---
    ("RISE",  "RISE 코리아밸류업"),
    ("RISE",  "RISE 네트워크인프라"),
    ("RISE",  "RISE AI전력인프라"),
    ("RISE",  "RISE 현대차고정피지컬AI"),
    ("RISE",  "RISE AI&로봇"),
    ("RISE",  "RISE AI반도체TOP10"),
    ("RISE",  "RISE 2차전지TOP10"),
    # --- TIGER (미래에셋) ---
    ("TIGER", "TIGER 반도체"),
    ("TIGER", "TIGER 코리아AI전력기기TOP3플러스"),
    ("TIGER", "TIGER 2차전지테마"),
    ("TIGER", "TIGER 현대차그룹플러스"),
    ("TIGER", "TIGER 반도체TOP10레버리지"),
    ("TIGER", "TIGER 조선TOP10"),
    ("TIGER", "TIGER 코리아원자력"),
    ("TIGER", "TIGER 코리아휴머노이드로봇산업"),
    ("TIGER", "TIGER K방산&우주"),
    ("TIGER", "TIGER 2차전지소재Fn"),
]

# 대시보드 초기화면 "큰 변화" 강조 임계치 -----------------------------------
# 개별 종목의 구성비중이 하루 만에 이 %p 이상 바뀌면 유의미한 변화로 본다.
BIG_MOVE_WEIGHT_PP = 1.0      # 개별 종목 비중 변화 임계 (%p)
# ETF 단위 회전율(= 종목별 |비중변화| 합 / 2, %) 이 이 값 이상이면 초기화면에 노출
BIG_MOVE_TURNOVER_PCT = 3.0

# 과거 백필(backfill)할 영업일 수 (TIGER/RISE는 과거 조회 지원) -------------
BACKFILL_BIZ_DAYS = 7

# HTTP 공통 --------------------------------------------------------------
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
REQUEST_TIMEOUT = 30

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8850
