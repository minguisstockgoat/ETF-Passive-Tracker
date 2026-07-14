@echo off
REM ETF 구성비중 대시보드 실행 -> 브라우저에서 http://127.0.0.1:8850
cd /d "%~dp0"
start "" http://127.0.0.1:8850
py server.py
