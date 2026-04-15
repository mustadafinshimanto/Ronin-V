<# 
╔══════════════════════════════════════════════════════════╗
║              RONIN-V — Bootstrap Script                  ║
║         One-click environment setup for Windows          ║
╚══════════════════════════════════════════════════════════╝

Run this script in PowerShell (as Admin recommended):
  .\scripts\bootstrap.ps1
#>

param(
    [switch]$SkipOllama,
    [switch]$SkipModel,
    [switch]$SkipVenv
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host ""
Write-Host "  ██████╗  ██████╗ ███╗   ██╗██╗███╗   ██╗" -ForegroundColor Green
Write-Host "  ██╔══██╗██╔═══██╗████╗  ██║██║████╗  ██║" -ForegroundColor Green
Write-Host "  ██████╔╝██║   ██║██╔██╗ ██║██║██╔██╗ ██║" -ForegroundColor Green
Write-Host "  ██╔══██╗██║   ██║██║╚██╗██║██║██║╚██╗██║" -ForegroundColor Green
Write-Host "  ██║  ██║╚██████╔╝██║ ╚████║██║██║ ╚████║" -ForegroundColor Green
Write-Host "  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝" -ForegroundColor Green
Write-Host ""
Write-Host "  >> BOOTSTRAP INSTALLER <<" -ForegroundColor Cyan
Write-Host ""

# ─── Step 1: Check Python ───
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Python not found. Install Python 3.11+ first." -ForegroundColor Red
    exit 1
}
Write-Host "  Found: $pythonVersion" -ForegroundColor Green

# ─── Step 2: Install Ollama ───
if (-not $SkipOllama) {
    Write-Host "[2/5] Checking Ollama..." -ForegroundColor Yellow
    $ollamaCheck = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaCheck) {
        Write-Host "  Ollama not found. Downloading installer..." -ForegroundColor Cyan
        $installerUrl = "https://ollama.com/download/OllamaSetup.exe"
        $installerPath = "$env:TEMP\OllamaSetup.exe"
        
        try {
            Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
            Write-Host "  Running Ollama installer (follow the prompts)..." -ForegroundColor Cyan
            Start-Process -FilePath $installerPath -Wait
            Write-Host "  Ollama installed. You may need to restart this terminal." -ForegroundColor Green
        } catch {
            Write-Host "  Failed to download Ollama. Please install manually from https://ollama.com/download" -ForegroundColor Red
            Write-Host "  Then re-run this script with -SkipOllama" -ForegroundColor Yellow
        }
    } else {
        $ollamaVersion = ollama --version 2>&1
        Write-Host "  Found: $ollamaVersion" -ForegroundColor Green
    }
} else {
    Write-Host "[2/5] Skipping Ollama check." -ForegroundColor DarkGray
}

# ─── Step 3: Pull Model ───
if (-not $SkipModel) {
    Write-Host "[3/5] Pulling dolphin-llama3:8b model..." -ForegroundColor Yellow
    Write-Host "  This may take 5-15 minutes depending on your connection." -ForegroundColor DarkGray
    
    $ollamaCheck = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCheck) {
        ollama pull dolphin-llama3:8b
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Model pulled successfully!" -ForegroundColor Green
            
            # Create custom model from Modelfile
            Write-Host "  Creating custom ronin-dolphin model..." -ForegroundColor Cyan
            $modelfilePath = Join-Path $ProjectRoot "modelfiles\Modelfile.dolphin"
            if (Test-Path $modelfilePath) {
                ollama create ronin-dolphin -f $modelfilePath
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  ronin-dolphin model created!" -ForegroundColor Green
                } else {
                    Write-Host "  WARNING: Custom model creation failed. Will fall back to base model." -ForegroundColor Yellow
                }
            } else {
                Write-Host "  WARNING: Modelfile not found at $modelfilePath" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ERROR: Model pull failed. Check Ollama is running." -ForegroundColor Red
        }
    } else {
        Write-Host "  Ollama not available. Skipping model pull." -ForegroundColor Red
    }
} else {
    Write-Host "[3/5] Skipping model pull." -ForegroundColor DarkGray
}

# ─── Step 4: Create Virtual Environment ───
if (-not $SkipVenv) {
    Write-Host "[4/5] Setting up Python virtual environment..." -ForegroundColor Yellow
    $venvPath = Join-Path $ProjectRoot ".venv"
    
    if (-not (Test-Path $venvPath)) {
        python -m venv $venvPath
        Write-Host "  Virtual environment created at .venv\" -ForegroundColor Green
    } else {
        Write-Host "  Virtual environment already exists." -ForegroundColor Green
    }
    
    # Activate and install deps
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    & $activateScript
    
    Write-Host "  Installing dependencies..." -ForegroundColor Cyan
    $reqPath = Join-Path $ProjectRoot "requirements.txt"
    pip install -r $reqPath --quiet
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Dependencies installed!" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Some dependencies may have failed." -ForegroundColor Yellow
    }
} else {
    Write-Host "[4/5] Skipping venv setup." -ForegroundColor DarkGray
}

# ─── Step 5: Create Data Directories ───
Write-Host "[5/5] Creating data directories..." -ForegroundColor Yellow
$dataDirs = @(
    (Join-Path $ProjectRoot "data\chroma_db"),
    (Join-Path $ProjectRoot "data\sessions"),
    (Join-Path $ProjectRoot "data\reports")
)
foreach ($dir in $dataDirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}
Write-Host "  Data directories ready." -ForegroundColor Green

# ─── Done ───
Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  BOOTSTRAP COMPLETE" -ForegroundColor Green
Write-Host "══════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  To activate the environment:" -ForegroundColor Cyan
Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  To launch Ronin-V:" -ForegroundColor Cyan
Write-Host "    python ronin.py" -ForegroundColor White
Write-Host ""
Write-Host "  To check system status:" -ForegroundColor Cyan
Write-Host "    python ronin.py status" -ForegroundColor White
Write-Host ""
