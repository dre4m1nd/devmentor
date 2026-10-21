# DevMentor install script - add devmentor command to PATH
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1

param(
    [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"

if (-not $InstallDir) { $InstallDir = Join-Path $env:USERPROFILE ".devmentor" }

$ProjectRoot = $PSScriptRoot
$JarSource = Join-Path (Join-Path $ProjectRoot "target") "devmentor-0.0.1-SNAPSHOT.jar"

# --- 1. Build JAR if needed ---
if (-not (Test-Path $JarSource)) {
    Write-Host "JAR not found, building..." -ForegroundColor Yellow
    $javaHome = $null
    # Scan ~/.jdks for JDK 17+ (match by dir name)
    $jdkDir = Join-Path $env:USERPROFILE ".jdks"
    if (Test-Path $jdkDir) {
        $found = Get-ChildItem $jdkDir -Directory |
            Where-Object { $_.Name -match "^(open)?jdk-(17|[2-9]\d|1[89])" } |
            Where-Object { Test-Path (Join-Path $_.FullName "bin\java.exe") } |
            Sort-Object Name -Descending | Select-Object -First 1
        if ($found) { $javaHome = $found.FullName }
    }
    # Fallback: check JAVA_HOME if it looks like 17+
    if (-not $javaHome -and $env:JAVA_HOME) {
        if (($env:JAVA_HOME -match "17|18|19|2[0-9]") -and (Test-Path (Join-Path $env:JAVA_HOME "bin\java.exe"))) {
            $javaHome = $env:JAVA_HOME
        }
    }
    if (-not $javaHome) {
        Write-Host "Cannot find JDK 17+." -ForegroundColor Red
        exit 1
    }
    Write-Host ("Using JDK: " + $javaHome) -ForegroundColor Gray
    $env:JAVA_HOME = $javaHome
    $mvn = $null
    if (Test-Path "D:\DevEnvironment\apache-maven-3.9.16\bin\mvn.cmd") {
        $mvn = "D:\DevEnvironment\apache-maven-3.9.16\bin\mvn.cmd"
    }
    if (-not $mvn) { $mvn = (Get-Command mvn -ErrorAction SilentlyContinue).Source }
    if (-not $mvn) {
        Write-Host "Cannot find Maven." -ForegroundColor Red
        exit 1
    }
    & $mvn -f $ProjectRoot package -DskipTests -q
    if (-not (Test-Path $JarSource)) {
        Write-Host "Build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "Build complete" -ForegroundColor Green
}

# --- 2. Install files ---
$LibDir = Join-Path $InstallDir "lib"
$BinDir = Join-Path $InstallDir "bin"

New-Item -ItemType Directory -Path $LibDir -Force | Out-Null
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null

Copy-Item $JarSource (Join-Path $LibDir "devmentor.jar") -Force
Write-Host ("JAR installed to " + $LibDir) -ForegroundColor Green

Copy-Item (Join-Path (Join-Path $ProjectRoot "bin") "devmentor.cmd") (Join-Path $BinDir "devmentor.cmd") -Force
Write-Host ("Launcher installed to " + $BinDir) -ForegroundColor Green

# --- 3. Add to PATH ---
$pathParts = $env:PATH -split ";"
if ($pathParts -notcontains $BinDir) {
    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike ("*" + $BinDir + "*")) {
        [Environment]::SetEnvironmentVariable("PATH", ($userPath + ";" + $BinDir), "User")
        Write-Host ("Added " + $BinDir + " to user PATH (restart terminal to take effect)") -ForegroundColor Green
    }
    $env:PATH = $env:PATH + ";" + $BinDir
} else {
    Write-Host ($BinDir + " already in PATH") -ForegroundColor Green
}

# --- 4. Done ---
Write-Host ""
Write-Host "Install complete!" -ForegroundColor Green
Write-Host "  Type devmentor in terminal to start." -ForegroundColor Cyan
Write-Host "  Set API key: set OPENROUTER_API_KEY=sk-or-..." -ForegroundColor Gray
Write-Host "  Set Java: set DEVMENTOR_JAVA_HOME=C:\path\to\jdk17" -ForegroundColor Gray