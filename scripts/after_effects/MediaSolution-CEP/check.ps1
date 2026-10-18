# check.ps1 - Validation automatique du depot Media Solution CEP v12.0
# Verifie : syntaxe JS client, validite du manifest XML, absence de scories
# (fichiers .bak, chemins developpeur kidpixel, chemins machines en dur).
# Usage : .\check.ps1
# Exit code : 0 = OK, 1 = au moins une verification a echoue.

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$global:Failures = 0

function Test-Step {
    param([string]$Name, [scriptblock]$Body)
    try {
        & $Body | Out-Null
        Write-Host "  [OK] $Name" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $Name : $($_.Exception.Message)" -ForegroundColor Red
        $global:Failures++
    }
}

Write-Host "=== Validation Media Solution CEP ===" -ForegroundColor Cyan

# 1. Syntaxe JavaScript du client
Test-Step "Syntaxe JS client/main.js" {
    node --check "client\main.js"
    if ($LASTEXITCODE -ne 0) { throw "node --check a echoue (code $LASTEXITCODE)" }
}

# 2. Validite du manifest XML + noeuds requis
Test-Step "Manifest CSXS/manifest.xml" {
    if (-not (Test-Path "CSXS\manifest.xml")) { throw "manifest.xml absent" }
    [xml]$manifest = Get-Content "CSXS\manifest.xml" -Raw
    if ($manifest.ExtensionManifest.ExtensionList.Extension -eq $null) { throw "ExtensionList/Extension manquant" }
    if ($manifest.ExtensionManifest.DispatchInfoList.Extension.DispatchInfo -eq $null) { throw "DispatchInfo manquant" }
    $mainPath = $manifest.ExtensionManifest.DispatchInfoList.Extension.DispatchInfo.Resources.MainPath
    if ($mainPath -ne "./client/index.html") { throw "MainPath inattendu : $mainPath" }
    $scriptPath = $manifest.ExtensionManifest.DispatchInfoList.Extension.DispatchInfo.Resources.ScriptPath
    if ($scriptPath -ne "./host/MediaSolution.jsx") { throw "ScriptPath inattendu : $scriptPath" }
}

# 3. Absence de fichiers temporaires
Test-Step "Aucun fichier .bak" {
    $baks = Get-ChildItem -Recurse -File -Filter "*.bak" -ErrorAction SilentlyContinue
    if ($baks) { throw "Fichiers .bak trouves : $($baks.FullName -join ', ')" }
}

# 4. Absence de chemins developpeur en dur
# docs/AUDIT.md est le rapport historique : il cite volontairement les constats
# (chemins kidpixel) comme preuves de l'audit - il est exclu du scan.
Test-Step "Aucun chemin 'kidpixel'" {
    $hits = Get-ChildItem -Recurse -File -Include *.js,*.jsx,*.html,*.py,*.md -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notlike "*\docs\AUDIT.md" } |
        Select-String -Pattern "kidpixel" -SimpleMatch -ErrorAction SilentlyContinue
    if ($hits) { throw "References kidpixel : $($hits | ForEach-Object { "$($_.Path):$($_.LineNumber)" } | Select-Object -First 5) ..." }
}

# 5. Absence de chemins machines en dur (F:\Adobe, Python311/312/313 absolus)
Test-Step "Aucun chemin machine en dur" {
    $hits = Get-ChildItem -Recurse -File -Include *.js,*.jsx,*.html,*.py,*.md -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notlike "*\docs\AUDIT.md" } |
        Select-String -Pattern "F:\\Adobe","Python31[123]\\" -ErrorAction SilentlyContinue
    if ($hits) { throw "Chemins machines : $($hits | ForEach-Object { "$($_.Path):$($_.LineNumber)" } | Select-Object -First 5) ..." }
}

# 6. Syntaxe Python
Test-Step "Syntaxe Python entry.py / manifest.py" {
    $pythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
    if ($pythonCmd) {
        python -m py_compile "entry.py" "manifest.py"
        if ($LASTEXITCODE -ne 0) { throw "py_compile a echoue (code $LASTEXITCODE)" }
    } else {
        Write-Host "    (python non trouve - verification Python ignoree)" -ForegroundColor Yellow
    }
}

Write-Host ""
if ($global:Failures -eq 0) {
    Write-Host "=== Validation terminee : OK ===" -ForegroundColor Green
    exit 0
} else {
    Write-Host "=== Validation terminee : $global:Failures echec(s) ===" -ForegroundColor Red
    exit 1
}
