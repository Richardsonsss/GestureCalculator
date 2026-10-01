# Rebuild manual.docx in the project folder (Windows, PowerShell 7, the project's .venv, Microsoft Word).
#
#   pwsh docs/source/update_manual.ps1
#
# Sources in this folder:
#   manual.html           the text (edit this when the program changes)
#   make_diagrams.py      the diagrams            -> docs/images
#   make_window_shot.py   the annotated screenshot of the real window -> docs/images/window.png
#   build_docx.py         manual.html + pictures  -> manual.docx (Office Open XML, no extra libraries)
# Word is then used only to fill in the page numbers of the table of contents; without Word the document is
# still complete and Word offers to update the table when the file is opened.
$ErrorActionPreference = "Stop"
$src  = $PSScriptRoot
$root = Split-Path (Split-Path $src -Parent) -Parent
$python = Join-Path $root ".venv\Scripts\python.exe"
$docx = Join-Path $root "manual.docx"
$env:PYTHONIOENCODING = "utf-8"

& $python (Join-Path $src "make_diagrams.py")
& $python (Join-Path $src "make_window_shot.py") 2>$null
& $python (Join-Path $src "build_docx.py") $docx

$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object Id)
$job = Start-Job -ScriptBlock {
    param($docx)
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false; $word.DisplayAlerts = 0
    try {
        $doc = $word.Documents.Open($docx, $false, $false, $false)
        foreach ($t in $doc.TablesOfContents) { $t.Update() }
        $doc.RemovePersonalInformation = $true   # do not store the name of the Windows user in the file
        $doc.Save()
        "table of contents updated, pages: " + $doc.ComputeStatistics(2)
        $doc.Close(0)
    } finally { $word.Quit() }
} -ArgumentList $docx
if (Wait-Job $job -Timeout 120) { Receive-Job $job }
else {
    Write-Warning "Word did not respond; the table of contents will be updated when the document is opened."
    Stop-Job $job
    Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } |
        ForEach-Object { Stop-Process -Id $_.Id -Force -Confirm:$false }
}
Remove-Job $job -Force
"done: $docx"
