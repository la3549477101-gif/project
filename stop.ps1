$ErrorActionPreference = 'Stop'
$stateFile = Join-Path $PSScriptRoot 'logs/services.json'
if (!(Test-Path $stateFile)) { Write-Host 'No managed services to stop.'; exit 0 }
$services = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
foreach ($service in $services) {
    $process = Get-Process -Id $service.ProcessId -ErrorAction SilentlyContinue
    if ($process) {
        $expectedTicks = if ($service.StartedUtcTicks) { [long]$service.StartedUtcTicks } else { ([datetimeoffset]$service.Started).UtcDateTime.Ticks }
        if ($process.StartTime.ToUniversalTime().Ticks -ne $expectedTicks) {
            throw "Process $($service.ProcessId) has changed. Refusing to stop an unrelated process."
        }
        & "$env:SystemRoot\System32\taskkill.exe" /PID $service.ProcessId /T /F | Out-Null
        if (!$process.WaitForExit(10000)) { throw "Could not stop $($service.Name); service state was retained." }
    }
}
Remove-Item -LiteralPath $stateFile
Write-Host 'Services stopped. Project data retained.'
