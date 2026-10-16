@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: TruthLens AI - Project Setup Script (Windows)
:: ============================================================================
:: This script sets up the complete TruthLens AI development environment
:: ============================================================================

title TruthLens AI - Project Setup

echo.
echo =====================================================================
echo                     TruthLens AI - Project Setup                     
echo               Deepfake ^& Scam Detection Platform                     
echo =====================================================================
echo.

net session >nul 2>&1
if %errorLevel% == 0 (
    echo [INFO] Running with Administrator privileges
) else (
    echo [INFO] Running with standard user privileges
)
echo.

set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"
set "MODELS_DIR=%BACKEND_DIR%\models"
set "VENV_DIR=%BACKEND_DIR%\venv"
set "PYTHON_CMD=python"
set "PIP_CMD=pip"
set "NPM_CMD=npm"

for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "BLUE=%ESC%[94m"
set "CYAN=%ESC%[96m"
set "RESET=%ESC%[0m"

call :print_color "%BLUE%" "[INFO] Project root: %PROJECT_ROOT%"
echo.

echo %CYAN%=====================================================================%RESET%
echo %CYAN%  Checking Prerequisites                                              %RESET%
echo %CYAN%=====================================================================%RESET%
echo.

call :check_command "python --version" "Python" "PY_VERSION"
if "!PY_VERSION!"=="" (
    call :print_color "%RED%" "[ERROR] Python not found! Please install Python 3.10+ from https://python.org"
    call :print_color "%RED%" "[ERROR] Make sure to check 'Add Python to PATH' during installation"
    goto :error_exit
)
call :print_color "%GREEN%" "[OK] Python found: !PY_VERSION!"

call :check_command "node --version" "Node.js" "NODE_VERSION"
if "!NODE_VERSION!"=="" (
    call :print_color "%RED%" "[ERROR] Node.js not found! Please install Node.js 18+ from https://nodejs.org"
    goto :error_exit
)
call :print_color "%GREEN%" "[OK] Node.js found: !NODE_VERSION!"

call :check_command "npm --version" "npm" "NPM_VERSION"
if "!NPM_VERSION!"=="" (
    call :print_color "%RED%" "[ERROR] npm not found!"
    goto :error_exit
)
call :print_color "%GREEN%" "[OK] npm found: !NPM_VERSION!"

call :check_command "git --version" "Git" "GIT_VERSION"
if "!GIT_VERSION!"=="" (
    call :print_color "%YELLOW%" "[WARN] Git not found - some features may not work"
) else (
    call :print_color "%GREEN%" "[OK] Git found: !GIT_VERSION!"
)

call :check_command "docker --version" "Docker" "DOCKER_VERSION"
if "!DOCKER_VERSION!"=="" (
    call :print_color "%YELLOW%" "[WARN] Docker not found - containerized deployment unavailable"
) else (
    call :print_color "%GREEN%" "[OK] Docker found: !DOCKER_VERSION!"
    call :check_command "docker-compose --version" "Docker Compose" "COMPOSE_VERSION"
    if "!COMPOSE_VERSION!"=="" (
        call :print_color "%YELLOW%" "[WARN] Docker Compose not found"
    ) else (
        call :print_color "%GREEN%" "[OK] Docker Compose found: !COMPOSE_VERSION!"
    )
)

call :check_command "ffmpeg -version" "FFmpeg" "FFMPEG_VERSION"
if "!FFMPEG_VERSION!"=="" (
    call :print_color "%YELLOW%" "[WARN] FFmpeg not found - video audio extraction will fall back"
) else (
    call :print_color "%GREEN%" "[OK] FFmpeg found"
)
echo.

echo %CYAN%=====================================================================%RESET%
echo %CYAN%  Setting Up Environment Configuration                               %RESET%
echo %CYAN%=====================================================================%RESET%
echo.

if not exist "%PROJECT_ROOT%.env" (
    if exist "%PROJECT_ROOT%.env.example" (
        copy "%PROJECT_ROOT%.env.example" "%PROJECT_ROOT%.env" >nul
        call :print_color "%GREEN%" "[OK] Created .env from .env.example"
    ) else (
        call :print_color "%YELLOW%" "[WARN] .env.example not found, creating basic .env"
        call :create_basic_env
    )
) else (
    call :print_color "%BLUE%" "[INFO] .env already exists, skipping"
)
echo.

echo %CYAN%=====================================================================%RESET%
echo %CYAN%  Setting Up Backend (Python/FastAPI)                                %RESET%
echo %CYAN%=====================================================================%RESET%
echo.

cd /d "%BACKEND_DIR%"

if not exist "%VENV_DIR%" (
    call :print_color "%BLUE%" "[INFO] Creating Python virtual environment..."
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        call :print_color "%RED%" "[ERROR] Failed to create virtual environment"
        goto :error_exit
    )
    call :print_color "%GREEN%" "[OK] Virtual environment created"
) else (
    call :print_color "%BLUE%" "[INFO] Virtual environment already exists"
)

call :print_color "%BLUE%" "[INFO] Activating virtual environment and upgrading pip..."
call "%VENV_DIR%\Scripts\activate.bat"
call "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel >nul 2>&1
call :print_color "%GREEN%" "[OK] Pip upgraded"

call :print_color "%BLUE%" "[INFO] Installing backend dependencies..."
call "%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    call :print_color "%RED%" "[ERROR] Failed to install backend dependencies"
    goto :error_exit
)
call :print_color "%GREEN%" "[OK] Backend dependencies installed"

if not exist "%MODELS_DIR%" (
    mkdir "%MODELS_DIR%"
    call :print_color "%GREEN%" "[OK] Created models directory"
)

call :print_color "%BLUE%" "[INFO] Installing llama-cpp-python (llama.cpp backend for the Qwen LLM)..."
call :print_color "%BLUE%" "[INFO]   Trying CUDA 12.4 build first (loads the model into VRAM)..."
call "%VENV_DIR%\Scripts\python.exe" -m pip install llama-cpp-python==0.3.36 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124 >nul 2>&1
if errorlevel 1 (
    call :print_color "%YELLOW%" "[WARN] CUDA build failed - falling back to CPU build (LLM will run on CPU)"
    call "%VENV_DIR%\Scripts\python.exe" -m pip install llama-cpp-python >nul 2>&1
    if errorlevel 1 (
        call :print_color "%RED%" "[ERROR] Failed to install llama-cpp-python"
        goto :error_exit
    )
    call :print_color "%GREEN%" "[OK] llama-cpp-python installed (CPU build)"
) else (
    call :print_color "%GREEN%" "[OK] llama-cpp-python installed (CUDA 12.4 build - GPU accelerated)"
)

echo.
echo %CYAN%=====================================================================%RESET%
echo %CYAN%  Downloading Qwen3-4B LLM (Q8_0, ~4 GB) into project folder       %RESET%
echo %CYAN%=====================================================================%RESET%
echo.

call :print_color "%BLUE%" "[INFO] Model: Qwen3-4B-Instruct-2507 Q8_0 (fits 8 GB VRAM)"
call :print_color "%BLUE%" "[INFO] Destination: %BACKEND_DIR%\models\llm\"
call :print_color "%BLUE%" "[INFO] The download resumes automatically if interrupted."
echo.

call "%VENV_DIR%\Scripts\python.exe" "%BACKEND_DIR%\download_llm.py"
if errorlevel 1 (
    call :print_color "%YELLOW%" "[WARN] LLM download did not complete."
    call :print_color "%YELLOW%" "[WARN] The app still works - scanning runs without the LLM."
    call :print_color "%YELLOW%" "[WARN] Re-run setup.bat later or run: backend\download_llm.py"
) else (
    call :print_color "%GREEN%" "[OK] Qwen3-4B (Q8_0) is ready in the project models folder"
)

call "%VENV_DIR%\Scripts\deactivate.bat" 2>nul
cd /d "%PROJECT_ROOT%"
echo.

echo %CYAN%=====================================================================%RESET%
echo %CYAN%  Setting Up Frontend (React/TypeScript/Vite)                        %RESET%
echo %CYAN%=====================================================================%RESET%
echo.

cd /d "%FRONTEND_DIR%"

if not exist "node_modules" (
    call :print_color "%BLUE%" "[INFO] Installing frontend dependencies..."
    call %NPM_CMD% install
    if errorlevel 1 (
        call :print_color "%RED%" "[ERROR] Failed to install frontend dependencies"
        goto :error_exit
    )
    call :print_color "%GREEN%" "[OK] Frontend dependencies installed"
) else (
    call :print_color "%BLUE%" "[INFO] node_modules exists, checking frontend packages..."
    call %NPM_CMD% install
    call :print_color "%GREEN%" "[OK] Frontend dependencies ready"
)

cd /d "%PROJECT_ROOT%"
echo.

echo %GREEN%=====================================================================%RESET%
echo %GREEN%  TruthLens AI - Setup Complete!                                      %RESET%
echo %GREEN%=====================================================================%RESET%
echo.
echo  Next steps:
echo    1. Start the project:       run.bat
echo    2. Or run backend only:     run.bat --backend-only
echo    3. Or run frontend only:    run.bat --frontend-only
echo.
echo  Access points:
echo    - Frontend:                 http://localhost:5173
echo    - Backend API:              http://localhost:8000
echo    - API Documentation:        http://localhost:8000/docs
echo.
call :print_color "%CYAN%" "Ready to launch! Run run.bat to start."
echo.
pause
goto :eof

:check_command
set "CMD_TO_CHECK=%~1"
set "TOOL_NAME=%~2"
set "VERSION_VAR=%~3"
for /f "tokens=* delims=" %%i in ('%CMD_TO_CHECK% 2^>nul') do (
    set "%VERSION_VAR%=%%i"
    goto :check_done
)
set "%VERSION_VAR%="
:check_done
goto :eof

:print_color
echo %~1%~2%RESET%
goto :eof

:create_basic_env
(
    echo # TruthLens AI Environment Configuration
    echo DEBUG=true
    echo APP_NAME="TruthLens AI"
    echo APP_VERSION="1.0.0"
    echo HOST=0.0.0.0
    echo PORT=8000
    echo CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
    echo MODEL_DIR=./models
    echo REDIS_URL=redis://localhost:6379/0
    echo LOG_LEVEL=INFO
) > "%PROJECT_ROOT%.env"
goto :eof

:error_exit
echo.
call :print_color "%RED%" "[FATAL] Setup encountered an issue. Please review the output above."
echo.
pause
exit /b 1