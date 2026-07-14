# 패시브 ETF 구성비중 트래커

SOL(신한) · RISE(KB) · TIGER(미래에셋) 주요 테마 ETF 20종의 **구성종목(PDF)** 과
**일간 구성비중 변화** 를 추적하는 로컬 대시보드.

## 화면 흐름
1. **홈** – 운용사(SOL/RISE/TIGER) 카드 + "오늘의 큰 변화" ETF (전일 대비 구성 변화가 큰 순)
2. **운용사** – 해당 운용사 ETF 목록 (회전율 큰 순, 큰 변화 배지)
3. **개별 ETF** – 최신 기준일 vs 직전 영업일 구성비중, 종목별 **비중변화(%p) · 보유수량 변화 · 신규/편출**

## 실행
```
run_dashboard.bat        # 서버 실행 후 http://127.0.0.1:8850 자동 열기
```
또는
```
py server.py             # http://127.0.0.1:8850
```

## 데이터 수집
```
py ingest.py             # 코드 해석 + 과거 7영업일 백필(TIGER/RISE) + 최신(SOL)
py ingest.py --latest    # 최신 영업일 1개만 (일일 갱신)
py ingest.py --days 15   # 백필 영업일 수 지정
```
대시보드 우상단 **↻ 갱신** 버튼으로도 최신 영업일 재수집 가능.

## 일일 자동 갱신 (Windows 작업 스케줄러)
평일 아침 자동 수집 등록 (관리자 CMD):
```
schtasks /create /tn "ETF_PDF_Dashboard_Update" /tr "%CD%\update.bat" ^
  /sc weekly /d MON,TUE,WED,THU,FRI /st 08:40 /f
```
해제:
```
schtasks /delete /tn "ETF_PDF_Dashboard_Update" /f
```

## 데이터 소스 (운용사 공식 공시, 인증 불필요)
| 운용사 | 엔드포인트 | 식별자 | 과거조회 |
|--------|-----------|--------|:-------:|
| TIGER | `investments.miraeasset.com/.../pdfListAjax.ajax` | ISIN(`ksdFund`) + `fixDate` | ✅ |
| SOL | `soletf.com/api/etf/pds/pdf/{FUND_CD}` | FUND_CD | ❌ 최신만 |
| RISE | `riseetf.co.kr/prod/finder/productViewSearchTabJquery3` | rise_code(`fundCd`) + `searchDate` | ✅ |

- **TIGER·RISE** 는 과거 일자를 조회할 수 있어 최초 실행 시 7영업일을 즉시 백필 → 당일부터 전일 대비 비교 표시.
- **SOL** 은 최신 구성만 제공 → 두 번째 수집일(익영업일)부터 비교 표시. 그 전에는 "비교 대기"로 안내.
- 대상 ETF 이름→코드 매칭은 KRX 파인더/각 운용사 리스트에 유사매칭(`resolve.py`)하며 실행 로그로 검증 가능.

## 구성
```
config.py     대상 ETF 20종 + 임계치 설정
fetchers.py   운용사별 수집기(공통 Holding 스키마) + KRX 파인더
resolve.py    요청명 -> 운용사 코드 유사매칭
store.py      SQLite 저장(etfs / snapshots / fetch_log)
ingest.py     수집 오케스트레이션(백필/최신)
diff.py       일간 변화 계산 + 큰 변화 선별
server.py     표준 http.server 백엔드 + JSON API
web/          단일 페이지 대시보드(index.html / style.css / app.js)
data/etf.db   스냅샷 DB (자동 생성)
```

## 큰 변화 판정 (config.py 에서 조정)
- 개별 종목 비중 변화 `≥ 1.0%p`, 또는
- ETF 회전율(Σ|Δ비중|/2) `≥ 3.0%`, 또는
- 신규 편입 / 편출 발생

## 참고
- 구성비중 변화(%p)는 리밸런싱뿐 아니라 당일 가격 변동으로도 발생하며, **보유수량 변화**가 있으면 실제 리밸런싱(편입/편출/증감)을 의미.
- 코드/종목코드는 KRX 6자리 티커로 정규화(해외·현금·스왑은 원본 유지).
