$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BrowserPath = Join-Path $Root ".playwright-browsers"
$DistPath = Join-Path $Root "dist"
$ReleasePath = Join-Path $DistPath "release"

Set-Location $Root
python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

$env:PLAYWRIGHT_BROWSERS_PATH = $BrowserPath
python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "Playwright Chromium installation failed." }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
python -m PyInstaller --clean --noconfirm adxray-spy.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
$SmokeProcess = Start-Process -FilePath (Join-Path $DistPath "adxray-spy\adxray-spy.exe") -ArgumentList "--smoke-test" -WorkingDirectory $env:TEMP -Wait -PassThru
if ($SmokeProcess.ExitCode -ne 0) { throw "Packaged smoke test failed: $($SmokeProcess.ExitCode)" }

if (Test-Path $ReleasePath) {
    Remove-Item -LiteralPath $ReleasePath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $ReleasePath | Out-Null
$PortableZip = Join-Path $ReleasePath "adxray-spy-portable-win-x64.zip"
Compress-Archive -Path (Join-Path $DistPath "adxray-spy\*") -DestinationPath $PortableZip

$IsccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($Iscc) {
    & $Iscc (Join-Path $Root "installer\adxray-spy.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed." }
} else {
    Write-Warning "Inno Setup 6 not found. Portable ZIP was built; installer was skipped."
}

$Artifacts = Get-ChildItem -Path $ReleasePath -File | Where-Object { $_.Name -ne "SHA256SUMS.txt" }
$Checksums = foreach ($Artifact in $Artifacts) {
    $Hash = Get-FileHash -Algorithm SHA256 -LiteralPath $Artifact.FullName
    "$($Hash.Hash.ToLower())  $($Artifact.Name)"
}
$Checksums | Set-Content -Encoding ascii (Join-Path $ReleasePath "SHA256SUMS.txt")
Write-Host "Release artifacts: $ReleasePath"
