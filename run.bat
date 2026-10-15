@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: TruthLens AI - Project Launch Script (Windows)
:: ============================================================================

title TruthLens AI - Launcher

echo.
echo =====================================================================
echo                     TruthLens AI - Launch                            
echo               Deepfake ^& Scam Detection Platform                     
echo =====================================================================
echo.

set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"
set "VENV_DIR=%BACKEND_DIR%\venv"

for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "BLUE=%ESC%[94m"
set "CYAN=%ESC%[96m"
set "MAGENTA=%ESC%[95m"
set "RESET=%ESC%[0m"

set "MODE=dev"
set "USE_DOCKER=false"
set "BACKEND_ONLY=false"
set "FRONTEND_ONLY=false"
set "SKIP_HEALTH_CHECK=false"

:parse_args
if "%~1"=="" goto :start_run
if "%~1"=="--help" goto :show_help
if "%~1"=="-h" goto :show_help
if "%~1"=="--docker" set "USE_DOCKER=true" & shift & goto :parse_args
if "%~1"=="--prod" set "MODE=prod" & shift & goto :parse_args
if "%~1"=="--backend-only" set "BACKEND_ONLY=true" & shift & goto :parse_args
if "%~1"=="--frontend-only" set "FRONTEND_ONLY=true" & shift & goto :parse_args
if "%~1"=="--skip-health" set "SKIP_HEALTH_CHECK=true" & shift & goto :parse_args
shift
goto :parse_args

:show_help
echo Usage: run.bat [options]
echo.
echo Options:
echo   --docker            Run using Docker Compose
echo   --prod              Run in production mode (with Docker)
echo   --backend-only      Run only the backend server
echo   --frontend-only     Run only the frontend server
echo   --skip-health       Skip backend health check
echo   --help              Show this help
echo.
echo Examples:
echo   run.bat                    ^< Runs both frontend and backend in dev mode
echo   run.bat --backend-only     ^< Runs only backend API
echo   run.bat --frontend-only    ^< Runs only frontend app
echo   run.bat --docker           ^< Runs with Docker Compose
echo.
pause
exit /b 0

:start_run
if "%USE_DOCKER%"=="true" (
    echo %CYAN%=====================================================================%RESET%
    echo %CYAN%  Starting with Docker Compose                                        %RESET%
    echo %CYAN%=====================================================================%RESET%
    echo.
    if "%MODE%"=="prod" (
        call :print_color "%BLUE%" "[INFO] Starting production stack..."
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
    ) else (
        call :print_color "%BLUE%" "[INFO] Starting development stack..."
        docker-compose up -d --build
    )
    if errorlevel 1 (
        call :print_color "%RED%" "[ERROR] Docker Compose failed"
        pause
        exit /b 1
    )
    call :print_color "%GREEN%" "[OK] Docker services started"
    echo.
    echo  Services running:
    echo    - Frontend: http://localhost:5173
    echo    - Backend:  http://localhost:8000
    echo    - API Docs: http://localhost:8000/docs
    echo.
    pause
    exit /b 0
)

echo %CYAN%=====================================================================%RESET%
echo %CYAN%  Starting Local Development Servers                                   %RESET%
echo %CYAN%=====================================================================%RESET%
echo.

if not exist "%VENV_DIR%" (
    call :print_color "%RED%" "[ERROR] Virtual environment not found at %VENV_DIR%"
    call :print_color "%YELLOW%" "[INFO] Run setup.bat first to set up the project"
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules" (
    call :print_color "%RED%" "[ERROR] Frontend dependencies not installed!"
    call :print_color "%YELLOW%" "[INFO] Run setup.bat first to set up the project"
    pause
    exit /b 1
)

call :check_port 8000
set "BACKEND_PORT_FREE=!errorlevel!"
call :check_port 5173
set "FRONTEND_PORT_FREE=!errorlevel!"

if "!BACKEND_PORT_FREE!"=="1" (
    if not "%FRONTEND_ONLY%"=="true" (
        call :print_color "%YELLOW%" "[WARN] Port 8000 may already be in use"
    )
)
if "!FRONTEND_PORT_FREE!"=="1" (
    if not "%BACKEND_ONLY%"=="true" (
        call :print_color "%YELLOW%" "[WARN] Port 5173 may already be in use"
    )
)
echo.

if "%FRONTEND_ONLY%"=="true" goto :skip_backend

echo %MAGENTA%=====================================================================%RESET%
echo %MAGENTA%  Starting Backend - FastAPI                                        %RESET%
echo %MAGENTA%=====================================================================%RESET%
echo.
call :print_color "%GREEN%" "[OK] Launching backend server on http://localhost:8000..."
start "TruthLens Backend" cmd /k "title TruthLens AI - Backend & cd /d "%BACKEND_DIR%" & call "%VENV_DIR%\Scripts\activate.bat" & uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

if "%SKIP_HEALTH_CHECK%"=="true" goto :skip_backend_health
call :print_color "%BLUE%" "[INFO] Waiting for backend to start..."
timeout /t 3 /nobreak >nul
set "HEALTH_OK=false"
for /l %%i in (1,1,10) do (
    if "!HEALTH_OK!"=="false" (
        curl -s -f http://localhost:8000/api/v1/health >nul 2>&1
        if !errorlevel!==0 set "HEALTH_OK=true"
        if "!HEALTH_OK!"=="false" timeout /t 1 /nobreak >nul
    )
)
if "!HEALTH_OK!"=="true" (
    call :print_color "%GREEN%" "[OK] Backend health check passed"
) else (
    call :print_color "%YELLOW%" "[WARN] Backend is starting up in background window"
)
:skip_backend_health
echo.

:skip_backend

if "%BACKEND_ONLY%"=="true" goto :skip_frontend

echo %MAGENTA%=====================================================================%RESET%
echo %MAGENTA%  Starting Frontend - Vite and React                                %RESET%
echo %MAGENTA%=====================================================================%RESET%
echo.
call :print_color "%GREEN%" "[OK] Launching frontend on http://localhost:5173..."
start "TruthLens Frontend" cmd /k "title TruthLens AI - Frontend & cd /d "%FRONTEND_DIR%" & npm run dev -- --host 0.0.0.0 --port 5173"
echo.

:skip_frontend

echo %CYAN%=====================================================================%RESET%
echo %CYAN%  TruthLens AI Servers Launched!                                      %RESET%
echo %CYAN%=====================================================================%RESET%
echo.
if not "%FRONTEND_ONLY%"=="true" (
    echo  Backend API:        http://localhost:8000
    echo  API Docs:           http://localhost:8000/docs
    echo  Health Check:       http://localhost:8000/api/v1/health
    echo.
)
if not "%BACKEND_ONLY%"=="true" (
    echo  Frontend App:       http://localhost:5173
    echo.
)
echo  Both servers are running in their own command prompt windows.
echo  To stop them, close their windows or press Ctrl+C in each.
echo.
echo  Press any key to close this launcher window...
pause >nul
exit /b 0

:check_port
set "P=%~1"
netstat -ano | findstr ":%P% " >nul 2>&1
if %errorlevel%==0 (
    exit /b 1
)
exit /b 0

:print_color
echo %~1%~2%RESET%
goto :eof