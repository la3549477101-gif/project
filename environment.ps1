# Dot-source this script: . ./environment.ps1
$ErrorActionPreference = 'Stop'
$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$toolRoot = Join-Path $workspaceRoot '.tools'
$nodeDirectory = Join-Path $toolRoot 'node-v24.22.1-win-x64'
$javaDirectory = Join-Path $toolRoot 'jdk-21.0.12.1+1'
$mavenDirectory = Join-Path $toolRoot 'apache-maven-3.9.16'
$pythonDirectory = Join-Path $PSScriptRoot 'backend/flask/.venv/Scripts'
foreach ($executable in @("$nodeDirectory/node.exe", "$javaDirectory/bin/java.exe", "$mavenDirectory/bin/mvn.cmd", "$pythonDirectory/python.exe")) {
    if (!(Test-Path -LiteralPath $executable)) { throw "Missing installed tool: $executable" }
}
$env:JAVA_HOME = $javaDirectory
$env:PATH = "$nodeDirectory;$javaDirectory\bin;$mavenDirectory\bin;$pythonDirectory;$env:PATH"
$env:npm_config_cache = Join-Path $workspaceRoot 'work/environment/npm-cache'
$env:PIP_CACHE_DIR = Join-Path $workspaceRoot 'work/environment/pip-cache'
$env:TEMP = Join-Path $workspaceRoot 'work/environment/tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
$mavenRepository = Join-Path $workspaceRoot '.tools/maven-repository'
$env:MAVEN_OPTS = "-Dmaven.repo.local=`"$mavenRepository`" -Djava.io.tmpdir=`"$env:TEMP`""
