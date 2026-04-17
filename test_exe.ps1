$ErrorActionPreference = "SilentlyContinue"
$proc = Start-Process "C:\coder\app\ca-analyzer\dist\ca-analyzer.exe" -PassThru -RedirectStandardError "C:\coder\app\ca-analyzer\exe_err.log" -RedirectStandardOutput "C:\coder\app\ca-analyzer\exe_out.log"
Start-Sleep 3
if (-not $proc.HasExited) {
    Stop-Process $proc.Id -Force
    Write-Host "OK: App was running after 3s (expected on headless server)"
} else {
    Write-Host "Crashed with exit code: $($proc.ExitCode)"
}
$errContent = Get-Content "C:\coder\app\ca-analyzer\exe_err.log" -Raw
$outContent = Get-Content "C:\coder\app\ca-analyzer\exe_out.log" -Raw
if ($errContent) { Write-Host "[stderr] $errContent" }
if ($outContent) { Write-Host "[stdout] $outContent" }
