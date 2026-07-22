@echo off
call .venv\Scripts\activate
python main.py
if errorlevel 1 pause
