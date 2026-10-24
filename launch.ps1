param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'environment.ps1')
$logDirectory = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Force $logDirectory | Out-Null
$stateFile = Join-Path $logDirectory 'services.json'
if (Test-Path $stateFile) {
    throw 'A previous launch record exists. Run stop.ps1 before starting again.'
}
foreach ($port in @(8080, 5000, 5173)) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $connected = $client.ConnectAsync('127.0.0.1', $port).Wait(500)
        if ($connected -and $client.Connected) { throw "Port $port is already in use. Stop the existing service first." }
    } catch [System.AggregateException] { } finally { $client.Dispose() }
}
$jar = Join-Path $PSScriptRoot 'backend/springboot/target/odm-tracker-1.0.0.jar'
if (!(Test-Path $jar)) { throw 'Build the backend first: mvn.cmd -f backend/springboot/pom.xml -DskipTests package' }
$services = @()
function Start-ServiceProcess($Name, $Executable, $Arguments, $Directory) {
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $Directory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory "$Name.out.log") -RedirectStandardError (Join-Path $logDirectory "$Name.err.log")
    return [PSCustomObject]@{ Name=$Name; ProcessId=$process.Id; StartedUtcTicks=$process.StartTime.ToUniversalTime().Ticks.ToString() }
}
try {
    $services += Start-ServiceProcess 'springboot' (Join-Path $env:JAVA_HOME 'bin/java.exe') @('-jar', "`"$jar`"") (Join-Path $PSScriptRoot 'backend/springboot')
    $services += Start-ServiceProcess 'flask' (Join-Path $PSScriptRoot 'backend/flask/.venv/Scripts/python.exe') @('-m','flask','--app','app','run','--host','127.0.0.1','--port','5000') (Join-Path $PSScriptRoot 'backend/flask')
    $vite = Join-Path $PSScriptRoot 'frontend/node_modules/vite/bin/vite.js'
    $services += Start-ServiceProcess 'frontend' (Join-Path $nodeDirectory 'node.exe') @("`"$vite`"",'--host','127.0.0.1','--strictPort') (Join-Path $PSScriptRoot 'frontend')
    $services | ConvertTo-Json | Set-Content $stateFile
    $ready = $false
    for ($attempt=0; $attempt -lt 45; $attempt++) {
        $ready = $true
        foreach ($url in @('http://127.0.0.1:8080/api/health','http://127.0.0.1:5000/api/summary','http://127.0.0.1:5173/')) {
            try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 10 | Out-Null }
            catch {
                Add-Content -LiteralPath (Join-Path $logDirectory 'startup.log') -Value "$url : $($_.Exception.Message)"
                $ready = $false
                break
            }
        }
        if ($ready) { break }
        Start-Sleep -Seconds 1
    }
    if (!$ready) { throw "Services did not become ready. See logs in $logDirectory" }
    Write-Host 'Ready: http://127.0.0.1:5173/'
    if (!$NoBrowser) { Start-Process 'http://127.0.0.1:5173/' }
} catch {
    foreach ($service in $services) {
        $process = Get-Process -Id $service.ProcessId -ErrorAction SilentlyContinue
        if ($process -and $process.StartTime.ToUniversalTime().Ticks.ToString() -eq $service.StartedUtcTicks) {
            & "$env:SystemRoot\System32\taskkill.exe" /PID $service.ProcessId /T /F | Out-Null
            $process.WaitForExit(10000) | Out-Null
        }
    }
    if (Test-Path $stateFile) { Remove-Item -LiteralPath $stateFile }
    throw
}
