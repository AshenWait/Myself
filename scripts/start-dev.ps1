param(
  [switch]$SkipAgentBackend,
  [switch]$BuildAgentBackend
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$PortfolioDir = Join-Path $Root 'apps/portfolio'
$AgentDir = Join-Path $Root 'apps/knowledge-agent'
$AgentFrontendDir = Join-Path $AgentDir 'frontend'

function Test-Port {
  param([int]$Port)

  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $connect = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
    if (-not $connect.AsyncWaitHandle.WaitOne(700)) {
      return $false
    }
    $client.EndConnect($connect)
    return $true
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

function Wait-Port {
  param(
    [int]$Port,
    [int]$Seconds = 20
  )

  $deadline = (Get-Date).AddSeconds($Seconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-Port $Port) {
      return $true
    }
    Start-Sleep -Milliseconds 500
  }
  return $false
}

function Start-NpmDev {
  param(
    [string]$Name,
    [string]$Directory,
    [int]$Port
  )

  if (Test-Port $Port) {
    Write-Host "$Name already running on http://127.0.0.1:$Port/"
    return
  }

  Start-Process `
    -FilePath 'npm.cmd' `
    -ArgumentList @('run', 'dev', '--', '--host', '127.0.0.1', '--port', "$Port") `
    -WorkingDirectory $Directory `
    -WindowStyle Hidden

  if (Wait-Port $Port) {
    Write-Host "$Name started on http://127.0.0.1:$Port/"
  } else {
    Write-Warning "$Name did not open port $Port in time."
  }
}

function Test-AgentEnv {
  $envPath = Join-Path $AgentDir '.env'
  if (-not (Test-Path $envPath)) {
    return $false
  }

  $envText = Get-Content -Raw $envPath
  $hasDeepseek = $envText -match '(?m)^DEEPSEEK_API_KEY\s*=\s*(?!replace-with|你的|\s*$).+'
  $hasDashscope = $envText -match '(?m)^DASHSCOPE_API_KEY\s*=\s*(?!replace-with|你的|\s*$).+'
  return $hasDeepseek -and $hasDashscope
}

function Test-Docker {
  docker info *> $null
  return $LASTEXITCODE -eq 0
}

Start-NpmDev -Name 'Portfolio' -Directory $PortfolioDir -Port 5173
Start-NpmDev -Name 'Knowledge Agent frontend' -Directory $AgentFrontendDir -Port 5174

if ($SkipAgentBackend) {
  Write-Host 'Knowledge Agent backend skipped.'
  exit 0
}

if (-not (Test-AgentEnv)) {
  Write-Warning 'Knowledge Agent backend skipped: apps/knowledge-agent/.env is missing or API keys are still placeholders.'
  exit 0
}

if (-not (Test-Docker)) {
  Write-Warning 'Knowledge Agent backend skipped: Docker Desktop is not running.'
  exit 0
}

$composeArgs = @('compose', 'up', '-d')
if ($BuildAgentBackend) {
  $composeArgs += '--build'
}

Start-Process `
  -FilePath 'docker' `
  -ArgumentList $composeArgs `
  -WorkingDirectory $AgentDir `
  -WindowStyle Hidden

if (Wait-Port 8000 -Seconds 60) {
  Write-Host 'Knowledge Agent API started on http://127.0.0.1:8000/'
} else {
  Write-Warning 'Knowledge Agent API did not open port 8000 in time. Check Docker Desktop and docker compose logs.'
}
