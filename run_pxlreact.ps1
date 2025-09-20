# PowerShell script to run pxlreactHL.py in admin mode
# Navigate to project directory, activate venv, and run the script

$projectPath = "C:\dev\pxlreact"
$scriptCommand = "cd '$projectPath'; .\.pxlenv\Scripts\Activate.ps1; python .\pxlreactHL.py"

# Start PowerShell as administrator with the command
Start-Process powershell -ArgumentList "-NoExit", "-Command", $scriptCommand -Verb RunAs

