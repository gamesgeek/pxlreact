@echo off
cd /d "C:\dev\pxlreact"
powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd C:\dev\pxlreact; .\.pxlenv\Scripts\Activate.ps1; python .\pxlreactHL.py' -Verb RunAs"

