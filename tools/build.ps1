$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Crie a .venv e instale requirements-dev.txt antes de gerar o exe.'
}
& $pythonExe -m PyInstaller --noconfirm --onefile --windowed `
    --name 'Dota-Minigame-Auto-Calibrado' `
    --distpath (Join-Path $projectRoot 'dist') `
    --workpath (Join-Path $projectRoot 'build') `
    --specpath (Join-Path $projectRoot 'build') `
    --add-data "$(Join-Path $projectRoot 'launch_ready.png');." `
    --add-data "$(Join-Path $projectRoot 'default_calibration');default_calibration" `
    --add-data "$(Join-Path $projectRoot 'licenses');licenses" `
    (Join-Path $projectRoot 'gui.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar o executável.' }
