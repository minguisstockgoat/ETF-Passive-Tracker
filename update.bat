@echo off
REM ETF 구성비중 대시보드 - 일일 최신 영업일 수집 (평일 아침 실행 권장)
cd /d "%~dp0"
py ingest.py --latest >> "%~dp0data\update.log" 2>&1
