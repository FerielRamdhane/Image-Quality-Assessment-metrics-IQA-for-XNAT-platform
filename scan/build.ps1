# Build the scan-level IQA images on Windows (PowerShell), from the repository root.
#   .\build.ps1 xnat
#   .\build.ps1 eucaim
param([Parameter(Mandatory=$true)][ValidateSet("xnat","eucaim")][string]$Target)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Version = (Select-String -Path src/iqa_common.py -Pattern '^TOOL_VERSION = "(.+)"').Matches[0].Groups[1].Value
if ($Target -eq "xnat") {
    $Base = if ($env:MCR_BASE) { $env:MCR_BASE } else { "mcr-riciannoiselevel:r2024b" }
    docker image inspect $Base *> $null
    if ($LASTEXITCODE -ne 0) { Write-Error "Shared MATLAB Runtime base '$Base' not found on this machine" }
    docker build -f xnat/Dockerfile --build-arg MCR_BASE=$Base -t "iqaxnat_scan:$Version-xnat" .
} else {
    docker build -f eucaim/Dockerfile -t "iqaxnat_scan:$Version" .
}
if ($LASTEXITCODE -ne 0) { Write-Error "Build failed" }
Write-Host "=== Done ==="
