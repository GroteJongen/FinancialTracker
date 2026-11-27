# No Docker daemon, registry, real credentials or user database: all commands are mocked.
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('financialtracker-ghcr-tests-' + [guid]::NewGuid().ToString('N'))
$savedVersion = $env:APP_VERSION
$savedPrefix = $env:IMAGE_PREFIX
$savedToken = $env:GH_TOKEN
$global:FtGhcrTestsha = 'a' * 40
$global:FtGhcrTestversion = 'sha-' + $global:FtGhcrTestsha
$global:FtGhcrTestcommands = [Collections.Generic.List[string]]::new()
$global:FtGhcrTestfailure = ''
$global:FtGhcrTestwrongLabel = $false
$global:FtGhcrTestnoPublished = $false
$global:FtGhcrTestapiCalls = 0
function Assert-True($condition, $message) { if (-not $condition) { throw $message } }
function docker {
    $line = $args -join ' '
    $global:FtGhcrTestcommands.Add($line)
    $global:LASTEXITCODE = 0
    if ($global:FtGhcrTestfailure -and $line.Contains($global:FtGhcrTestfailure)) { $global:LASTEXITCODE = 1; return }
    if ($line.StartsWith('image inspect')) {
        $revision = if ($global:FtGhcrTestwrongLabel) { 'b' * 40 } else { $global:FtGhcrTestsha }
        return '{"org.opencontainers.image.revision":"' + $revision + '"}'
    }
}
function Invoke-RestMethod {
    param($Uri, $Headers, $TimeoutSec)
    $global:FtGhcrTestapiCalls++
    if ($Uri.Contains('/jobs?')) {
        $jobs = if ($global:FtGhcrTestnoPublished -or $Uri.Contains('/1/jobs?')) { @() } else { @(@{ name = 'publish-images'; conclusion = 'success' }) }
        return @{ jobs = $jobs }
    }
    return @{ workflow_runs = @(
        @{ id = 1; head_branch = 'main'; event = 'push'; conclusion = 'success'; head_sha = ('b' * 40) },
        @{ id = 2; head_branch = 'main'; event = 'push'; conclusion = 'success'; head_sha = $global:FtGhcrTestsha }
    ) }
}
function Reset-Case {
    $global:FtGhcrTestcommands.Clear(); $global:FtGhcrTestfailure = ''; $global:FtGhcrTestwrongLabel = $false
    $global:FtGhcrTestnoPublished = $false; $global:FtGhcrTestapiCalls = 0
}
function Expect-Failure([scriptblock]$action) {
    $caught = $false
    try { & $action } catch { $caught = $true }
    Assert-True $caught 'Expected a controlled update failure'
}

try {
    New-Item -ItemType Directory -Path (Join-Path $testRoot 'scripts') -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $sourceRoot 'scripts/update.ps1') -Destination (Join-Path $testRoot 'scripts/update.ps1')
    Copy-Item -LiteralPath (Join-Path $sourceRoot 'compose.ghcr.yaml') -Destination $testRoot
    [IO.File]::WriteAllText((Join-Path $testRoot '.env'), 'POSTGRES_PASSWORD=synthetic-tests-only')
    $updater = Join-Path $testRoot 'scripts/update.ps1'
    $pin = Join-Path $testRoot '.env.ghcr'
    $env:APP_VERSION = 'inherited-wrong-version'; $env:IMAGE_PREFIX = 'inherited-wrong-registry'; $env:GH_TOKEN = $null

    & $updater -PullOnly
    Assert-True ($global:FtGhcrTestapiCalls -eq 3) 'Must skip old CI without a successful publisher'
    Assert-True (($global:FtGhcrTestcommands | Where-Object { $_ -match ' (up|run) ' }).Count -eq 0) 'PullOnly must not start services or migrate'
    Assert-True ((Get-Content -Raw -LiteralPath $pin).Contains($global:FtGhcrTestversion)) 'Selected release must be saved'
    Assert-True ($env:APP_VERSION -eq 'inherited-wrong-version') 'Caller environment must be restored'
    Write-Host 'PASS: latest published run lookup, pull-only and environment restoration'

    Reset-Case
    & $updater -Version $global:FtGhcrTestversion
    $commands = $global:FtGhcrTestcommands -join "`n"
    Assert-True ($commands.IndexOf(' pull') -lt $commands.IndexOf('run --rm')) 'Pull before migration'
    Assert-True ($commands.IndexOf('run --rm') -lt $commands.IndexOf('up -d --no-deps')) 'Migration before app containers'
    Assert-True ($global:FtGhcrTestapiCalls -eq 0) 'Explicit version must not depend on GitHub API'
    Write-Host 'PASS: explicit version and ordered pull / database / migration / application start'

    foreach ($failure in @(' pull', 'run --rm')) {
        Reset-Case; $global:FtGhcrTestfailure = $failure
        [IO.File]::WriteAllText($pin, 'previous-release')
        Expect-Failure { & $updater -Version $global:FtGhcrTestversion }
        Assert-True ((Get-Content -Raw -LiteralPath $pin) -eq 'previous-release') 'Failure must preserve selected release'
        Assert-True (($global:FtGhcrTestcommands | Where-Object { $_ -match 'up -d --no-deps' }).Count -eq 0) 'Failed pull/migration must not start application'
    }
    Write-Host 'PASS: failed pull and migration stop deployment and preserve pin'

    Reset-Case; $global:FtGhcrTestfailure = 'up -d --no-deps'
    [IO.File]::WriteAllText($pin, 'previous-release')
    Expect-Failure { & $updater -Version $global:FtGhcrTestversion }
    Assert-True (($global:FtGhcrTestcommands | Where-Object { $_ -match 'up -d --no-deps.* frontend$' }).Count -eq 0) 'Failed backend readiness must not start frontend'
    Assert-True ((Get-Content -Raw -LiteralPath $pin) -eq 'previous-release') 'Startup failure must preserve pin'
    Write-Host 'PASS: backend startup failure stops frontend and preserves pin'

    Reset-Case; $global:FtGhcrTestwrongLabel = $true
    Expect-Failure { & $updater -Version $global:FtGhcrTestversion }
    Assert-True (($global:FtGhcrTestcommands | Where-Object { $_ -match ' (up|run) ' }).Count -eq 0) 'Wrong image revision must stop before database changes'
    Reset-Case; $global:FtGhcrTestnoPublished = $true
    Expect-Failure { & $updater }
    Assert-True ($global:FtGhcrTestcommands.Count -eq 0) 'No published release must not invoke Docker'
    Write-Host 'PASS: mismatched image and unpublished CI are rejected'
} finally {
    $env:APP_VERSION = $savedVersion; $env:IMAGE_PREFIX = $savedPrefix; $env:GH_TOKEN = $savedToken
    $absoluteTestRoot = [IO.Path]::GetFullPath($testRoot)
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if (-not $absoluteTestRoot.StartsWith($tempRoot) -or (Split-Path -Leaf $absoluteTestRoot) -notmatch '^financialtracker-ghcr-tests-[a-f0-9]{32}$') {
        throw 'Unexpected temporary test path; refusing cleanup.'
    }
    if (Test-Path -LiteralPath $absoluteTestRoot) { Remove-Item -LiteralPath $absoluteTestRoot -Recurse -Force }
}
