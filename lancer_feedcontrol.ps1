# Lancer depuis le dossier de ce script ; ne touche pas aux préférences ni au .env existant.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Création du venv impossible. Installer Python 3.10+.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Installation incomplète ; consulter le message ci-dessus.' }
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
Write-Host 'Ne partagez jamais votre clé. Configurer YOUTUBE_API_KEY dans .env pour les découvertes.'
& '.\.venv\Scripts\python.exe' ai_server.py
exit $LASTEXITCODE
