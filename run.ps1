param([Parameter(Mandatory=$true)][ValidateSet('springboot','flask','frontend')][string]$Service)
. (Join-Path $PSScriptRoot 'environment.ps1')
switch ($Service) {
    'springboot' {
        Set-Location (Join-Path $PSScriptRoot 'backend/springboot')
        $env:MAVEN_BASEDIR = (Get-Location).Path
        & mvn.cmd spring-boot:run
    }
    'flask' {
        Set-Location (Join-Path $PSScriptRoot 'backend/flask')
        & python.exe -m flask --app app run --host 127.0.0.1 --port 5000
    }
    'frontend' {
        Set-Location (Join-Path $PSScriptRoot 'frontend')
        & npm.cmd run dev -- --host 127.0.0.1
    }
}
exit $LASTEXITCODE
