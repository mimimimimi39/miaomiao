param(
  [string]$Dest = "<AiQQ>_transfer",
  [switch]$WithNodeModules,
  [switch]$WithMedia
)

$ErrorActionPreference = "Stop"
$src = "<AiQQ>"

if (-not (Test-Path $src)) { throw "source not found: $src" }
New-Item -ItemType Directory -Path $Dest -Force | Out-Null

$xd = @(
  "$src\Cortico\deployments\mybot\data\runs",
  "$src\NapCat\logs",
  "$src\NapCat\cache",
  "$src\backups"
)
if (-not $WithNodeModules) { $xd += "$src\Cortico\node_modules" }
if (-not $WithMedia) { $xd += "$src\Cortico\deployments\mybot\data\media" }

$xf = @("*.log", "qrcode.png", "instance.lock")

$rcArgs = @($src, $Dest, "/E", "/COPY:DAT", "/DCOPY:T", "/R:1", "/W:1", "/NFL", "/NDL", "/NP")
if ($xd.Count -gt 0) { $rcArgs += "/XD"; $rcArgs += $xd }
if ($xf.Count -gt 0) { $rcArgs += "/XF"; $rcArgs += $xf }

Write-Host "Packing $src -> $Dest ..."
& robocopy @rcArgs | Out-Host
$code = $LASTEXITCODE
if ($code -ge 8) { throw "robocopy failed: $code" }

Write-Host ""
Write-Host "Done. Next steps:"
Write-Host "  1) copy $Dest to target machine (same path <AiQQ> recommended)"
Write-Host "  2) install Node 22+ / Python 3.10+ (pillow) / QQ NT on target"
Write-Host "  3) if path differs: python tools\rebind_paths.py '<AiQQ>' '<new path>'"
if (-not $WithNodeModules) { Write-Host "  4) cd <new path>\Cortico ; pnpm install (then check docs\补丁清单.md)" }
Write-Host "  5) run start_cortico.bat ; scan QR code"
