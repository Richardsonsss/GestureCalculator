# Build the Windows program in the project root:  GestureCalculator.exe  +  _internal\
#
#   pwsh build_exe.ps1
#
# Needs the virtual environment (.venv) with requirements.txt and pyinstaller.
# The program loads its models from models\ next to the exe. It runs without Python and without an internet
# connection.
# To use it on another computer, copy GestureCalculator.exe, _internal\ and models\ together.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$models = Join-Path $root "models"

if (-not (Test-Path (Join-Path $models "hand_landmarker.task"))) { throw "models\hand_landmarker.task is missing - see README, 'Models'" }
if (-not (Get-ChildItem $models -Filter "gesture_*.onnx")) { throw "no gesture model in models\ - run tools\convert_hagrid.py (README, 'Models')" }
if (Get-Process GestureCalculator -ErrorAction SilentlyContinue) { throw "GestureCalculator.exe is running - close it first" }

# PyInstaller's working files name the folders of this computer (and so its user): they go to a temporary
# folder outside the project and are removed at the end.
$work = Join-Path ([IO.Path]::GetTempPath()) ("gesturecalc_build_" + [Guid]::NewGuid().ToString("N"))

& $python -m PyInstaller --noconfirm --clean --windowed --name GestureCalculator `
    --distpath (Join-Path $work "dist") --workpath (Join-Path $work "build") --specpath (Join-Path $work "build") `
    --paths (Join-Path $root "app") --collect-all mediapipe `
    --exclude-module torch --exclude-module torchvision --exclude-module onnx --exclude-module onnxscript `
    --exclude-module pytest --exclude-module tkinter --exclude-module matplotlib `
    (Join-Path $root "app\main.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# move the result to the project root, replacing the previous build
$built = Join-Path $work "dist\GestureCalculator"
$exe = Join-Path $root "GestureCalculator.exe"
$internal = Join-Path $root "_internal"
if (Test-Path $exe) { Remove-Item $exe -Force -Confirm:$false }
if (Test-Path $internal) { Remove-Item $internal -Recurse -Force -Confirm:$false }
Move-Item (Join-Path $built "GestureCalculator.exe") $exe
Move-Item (Join-Path $built "_internal") $internal
Remove-Item $work -Recurse -Force -Confirm:$false

$size = (Get-ChildItem $internal -Recurse | Measure-Object Length -Sum).Sum / 1MB
"built GestureCalculator.exe in {0} (_internal: {1:N0} MB, models\ is used from the same folder)" -f $root, $size
