#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidatePattern('^sha-[0-9a-f]{40}$')]
    [string]$Version,
    [switch]$PullOnly,
    [ValidatePattern('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')]
    [string]$Repository = 'GroteJongen/FinancialTracker'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot 'compose.ghcr.yaml'
$privateEnv = Join-Path $projectRoot '.env'
$releaseEnv = Join-Path $projectRoot '.env.ghcr'

function Invoke-Docker {
    param([string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'Polecenie Docker nie powiodlo sie. Aktualizacja przerwana; sprawdz komunikat powyzej.'
    }
}

function Get-PublishedVersion {
    $headers = @{ Accept = 'application/vnd.github+json'; 'User-Agent' = 'FinancialTracker-Updater' }
    if ($env:GH_TOKEN) { $headers.Authorization = 'Bearer ' + $env:GH_TOKEN }
    $api = 'https://api.github.com/repos/' + $Repository
    # Completed CI alone is insufficient: older runs did not publish images.
    $runs = Invoke-RestMethod -Uri ($api + '/actions/workflows/ci.yml/runs?branch=main&event=push&status=success&per_page=20') -Headers $headers -TimeoutSec 20
    foreach ($run in $runs.workflow_runs) {
        if ($run.head_branch -ne 'main' -or $run.event -ne 'push' -or
            $run.conclusion -ne 'success' -or $run.head_sha -notmatch '^[0-9a-f]{40}$') { continue }
        $jobs = Invoke-RestMethod -Uri ($api + '/actions/runs/' + $run.id + '/jobs?filter=latest&per_page=100') -Headers $headers -TimeoutSec 20
        $published = @($jobs.jobs | Where-Object { $_.name -eq 'publish-images' -and $_.conclusion -eq 'success' })
        if ($published.Count -gt 0) { return 'sha-' + $run.head_sha }
    }
    throw 'Nie znaleziono opublikowanego wydania. Poczekaj na udany publish-images po merge do main albo podaj -Version sha-<commit>.'
}

if (-not (Test-Path -LiteralPath $privateEnv -PathType Leaf)) {
    throw 'Brak .env. Skopiuj .env.example do .env i ustaw lokalne haslo bazy. Nie nadpisuj istniejacej konfiguracji.'
}
if (-not (Test-Path -LiteralPath $composeFile -PathType Leaf)) { throw 'Brak compose.ghcr.yaml.' }
# Avoid PowerShell 5.1 default TLS versions for GitHub's HTTPS API.
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
if (-not $Version) { $Version = Get-PublishedVersion }
$imagePrefix = 'ghcr.io/' + $Repository.ToLowerInvariant()
$releaseText = "APP_VERSION=$Version`nIMAGE_PREFIX=$imagePrefix`n"
$candidate = Join-Path ([IO.Path]::GetTempPath()) ('financialtracker-release-' + [guid]::NewGuid().ToString('N') + '.env')
$priorVersion = $env:APP_VERSION
$priorPrefix = $env:IMAGE_PREFIX

try {
    [IO.File]::WriteAllText($candidate, $releaseText, [Text.UTF8Encoding]::new($false))
    $compose = @('compose', '--project-directory', $projectRoot, '--env-file', $privateEnv,
        '--env-file', $candidate, '-f', $composeFile)
    # Explicitly override inherited shell values to keep every service on the selected release.
    $env:APP_VERSION = $Version
    $env:IMAGE_PREFIX = $imagePrefix
    Invoke-Docker -DockerArgs ($compose + @('config', '--quiet'))
    Write-Host ('Pobieranie wydania ' + $Version)
    Invoke-Docker -DockerArgs ($compose + @('pull'))
    foreach ($component in @('backend', 'frontend')) {
        $labelJson = & docker image inspect ($imagePrefix + '-' + $component + ':' + $Version) --format '{{json .Config.Labels}}'
        if ($LASTEXITCODE -ne 0) { throw ('Nie mozna sprawdzic obrazu ' + $component + '.') }
        $labels = ($labelJson -join '') | ConvertFrom-Json
        if ($labels.'org.opencontainers.image.revision' -ne $Version.Substring(4)) {
            throw ('Obraz ' + $component + ' nie potwierdza wybranego commita. Aktualizacja przerwana.')
        }
    }
    if (-not $PullOnly) {
        Invoke-Docker -DockerArgs ($compose + @('up', '-d', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '300', 'db'))
        Invoke-Docker -DockerArgs ($compose + @('run', '--rm', '--no-deps', '--pull', 'never', 'migrate'))
        # Run app containers only after a successful migration of this exact backend image.
        Invoke-Docker -DockerArgs ($compose + @('up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '300', 'backend', 'frontend'))
    }
    [IO.File]::WriteAllText($releaseEnv, $releaseText, [Text.UTF8Encoding]::new($false))
    Write-Host ('Zapisano wybrane wydanie w .env.ghcr: ' + $Version)
    if ($PullOnly) { Write-Host 'Obrazy pobrane. Kontenery pozostaly bez zmian; polecenie uruchomienia znajdziesz w docs/ghcr.md.' }
    else { Write-Host 'Aplikacja gotowa: http://127.0.0.1:5173' }
} finally {
    $env:APP_VERSION = $priorVersion
    $env:IMAGE_PREFIX = $priorPrefix
    if (Test-Path -LiteralPath $candidate) { Remove-Item -LiteralPath $candidate }
}
