# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    # Restart the script with admin privileges
    Start-Process pwsh.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Now running as admin - set location to script directory
Set-Location $PSScriptRoot

# Activate virtual environment
& .\.pxlenv\Scripts\Activate.ps1

# Run the Python script
python stopwatch.py

# Keep window open if there's an error
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nPress any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
