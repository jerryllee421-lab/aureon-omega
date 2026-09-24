param(
  [Parameter(Mandatory=$true)][string]$RunnerToken,
  [string]$RepoUrl='https://github.com/jerryllee421-lab/aureon-omega',
  [string]$RunnerDir='C:\actions-runner',
  [string]$RunnerName=$env:COMPUTERNAME,
  [string]$Labels='mt5,aureon'
)

$ErrorActionPreference='Stop'

function Assert-Admin {
  $id=[Security.Principal.WindowsIdentity]::GetCurrent()
  $p=New-Object Security.Principal.WindowsPrincipal($id)
  if(-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    throw 'Run PowerShell as Administrator.'
  }
}

function Install-Python {
  if(Get-Command python -ErrorAction SilentlyContinue){ return }
  if(Get-Command winget -ErrorAction SilentlyContinue){
    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    $env:Path=[Environment]::GetEnvironmentVariable('Path','Machine')+';'+[Environment]::GetEnvironmentVariable('Path','User')
  }
  if(-not (Get-Command python -ErrorAction SilentlyContinue)){
    throw 'Python 3.12+ is required. Install it, then rerun this script.'
  }
}

function Install-PrimeXBTMT5 {
  $root='C:\AUREON_MT5'
  if(Test-Path "$root\terminal64.exe"){ return }
  $url='https://download.terminal.free/cdn/web/pxbt.trading.ltd/mt5/pxbttrading5setup.exe'
  $installer=Join-Path $env:TEMP 'pxbttrading5setup.exe'
  Invoke-WebRequest -Uri $url -OutFile $installer
  if((Get-Item $installer).Length -lt 100000){ throw 'PrimeXBT MT5 installer download is unexpectedly small.' }
  $p=Start-Process -FilePath $installer -ArgumentList @('/auto',"/path:$root") -PassThru
  if(-not $p.WaitForExit(600000)){ $p.Kill(); throw 'PrimeXBT MT5 installer timed out.' }
  $deadline=(Get-Date).AddMinutes(3)
  while((Get-Date)-lt $deadline -and -not (Test-Path "$root\terminal64.exe")){ Start-Sleep 2 }
  if(-not (Test-Path "$root\terminal64.exe")){ throw 'PrimeXBT MT5 terminal64.exe was not installed.' }
  [Environment]::SetEnvironmentVariable('AUREON_MT5_ROOT',$root,'Machine')
}

function Install-Runner {
  New-Item -ItemType Directory -Force -Path $RunnerDir | Out-Null
  Set-Location $RunnerDir

  if(-not (Test-Path '.\config.cmd')){
    $release=Invoke-RestMethod -Headers @{'User-Agent'='AUREON-Runner-Setup'} -Uri 'https://api.github.com/repos/actions/runner/releases/latest'
    $asset=$release.assets | Where-Object { $_.name -match '^actions-runner-win-x64-.*\.zip$' } | Select-Object -First 1
    if(-not $asset){ throw 'Could not resolve latest GitHub Actions Windows x64 runner.' }
    $zip=Join-Path $env:TEMP $asset.name
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $RunnerDir -Force
  }

  if(Test-Path '.runner'){
    Write-Host 'Runner is already configured. Skipping registration.'
  } else {
    & .\config.cmd --unattended --url $RepoUrl --token $RunnerToken --name $RunnerName --labels $Labels --work '_work' --runasservice
    if($LASTEXITCODE -ne 0){ throw 'GitHub Actions runner registration failed.' }
  }

  $svc=Get-Service | Where-Object { $_.Name -like 'actions.runner.*' } | Select-Object -First 1
  if($svc -and $svc.Status -ne 'Running'){ Start-Service $svc.Name }
}

Assert-Admin
Install-Python
python -m pip install --upgrade pip
python -m pip install MetaTrader5 pandas numpy pyarrow requests
Install-PrimeXBTMT5
Install-Runner

Write-Host ''
Write-Host 'AUREON self-hosted Windows runner is ready.'
Write-Host 'Labels: self-hosted, Windows, X64, mt5, aureon'
Write-Host 'GitHub self-hosted runner execution does not consume GitHub-hosted Actions minutes.'
Write-Host 'Do not paste runner registration tokens or broker passwords into chat.'
