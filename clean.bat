@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: TruthLens AI - Clean Script (Windows)
:: ============================================================================
:: Removes generated files and installed dependencies for a fresh installation
:: ============================================================================

title TruthLens AI - Clean

echo.
echo =====================================================================
echo                     TruthLens AI - Clean                             
echo               Deepfake ^& Scam Detection Platform                     
echo =====================================================================
echo.

set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"
set "VENV_DIR=%BACKEND_DIR%\venv"
set "MODELS_DIR=%BACKEND_DIR%\models"

for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "BLUE=%ESC%[94m"
set "CYAN=%ESC%[96m"
set "RESET=%ESC%[0m"

:: Parse arguments
set "CLEAN_ALL=false"
set "CLEAN_ENV=false"
set "CLEAN_MODELS=false"
set "CONFIRM=true"

:parse_args
if "%~1"=="" goto :start_clean
if "%~1"=="--help" goto :show_help
if "%~1"=="-h" goto :show_help
if "%~1"=="--all" set "CLEAN_ALL=true" & shift & goto :parse_args
if "%~1"=="--env" set "CLEAN_ENV=true" & shift & goto :parse_args
if "%~1"=="--models" set "CLEAN_MODELS=true" & shift & goto :parse_args
if "%~1"=="--yes" set "CONFIRM=false" & shift & goto :parse_args
if "%~1"=="-y" set "CONFIRM=false" & shift & goto :parse_args
shift
goto :parse_args

:show_help
echo Usage: clean.bat [options]
echo.
echo Removes generated files and dependencies for a fresh install.
echo By default, cleans venv, node_modules, caches, and build output.
echo.
echo Options:
echo   --all        Clean everything including .env and downloaded models
echo   --env        Also remove the .env configuration file
echo   --models     Also remove downloaded ML models
echo   --yes, -y    Skip confirmation prompt
echo   --help, -h   Show this help
echo.
echo Examples:
echo   clean.bat              ^< Clean standard files (venv, node_modules, caches)
echo   clean.bat --all        ^< Clean everything for a completely fresh start
echo   clean.bat --models     ^< Also remove downloaded models
echo   clean.bat --all -y     ^< Clean everything without confirmation
echo.
pause
exit /b 0

:start_clean
if "%CLEAN_ALL%"=="true" (
    set "CLEAN_ENV=true"
    set "CLEAN_MODELS=true"
)

echo  The following will be removed:
echo.
echo    [ALWAYS]
echo      - Backend virtual environment     (backend\venv)
echo      - Frontend node_modules           (frontend\node_modules)
echo      - Frontend build output           (frontend\dist)
echo      - Python caches                   (__pycache__, .pytest_cache, *.pyc)
echo      - Misc caches                     (.mypy_cache, .ruff_cache)
if "%CLEAN_MODELS%"=="true" (
    echo      - Downloaded ML models            (backend\models)
)
if "%CLEAN_ENV%"=="true" (
    echo      - Environment config              (.env)
)
echo.

if "%CONFIRM%"=="true" (
    set /p "ANSWER=  Are you sure? [y/N] "
    if /i not "!ANSWER!"=="y" (
        call :print_color "%YELLOW%" "[INFO] Clean cancelled."
        pause
        exit /b 0
    )
)
echo.

echo %CYAN%=====================================================================%RESET%
echo %CYAN%  Cleaning Backend                                                    %RESET%
echo %CYAN%=====================================================================%RESET%
echo.

:: Deactivate venv if currently active
if defined VIRTUAL_ENV (
    call deactivate 2>nul
    call :print_color "%BLUE%" "[INFO] Deactivated virtual environment"
)

:: Remove virtual environment
if exist "%VENV_DIR%" (
    call :print_color "%BLUE%" "[INFO] Removing virtual environment..."
    rmdir /s /q "%VENV_DIR%"
    if errorlevel 1 (
        call :print_color "%YELLOW%" "[WARN] Could not fully remove venv - some files may be locked"
    ) else (
        call :print_color "%GREEN%" "[OK] Removed backend\venv"
    )
) else (
    call :print_color "%BLUE%" "[INFO] No virtual environment found, skipping"
)

:: Remove Python caches
call :print_color "%BLUE%" "[INFO] Removing Python caches..."
set "CACHE_COUNT=0"
for /d /r "%BACKEND_DIR%" %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d" 2>nul
        set /a CACHE_COUNT+=1
    )
)
for /d /r "%BACKEND_DIR%" %%d in (.pytest_cache) do (
    if exist "%%d" (
        rmdir /s /q "%%d" 2>nul
        set /a CACHE_COUNT+=1
    )
)
for /d /r "%BACKEND_DIR%" %%d in (.mypy_cache) do (
    if exist "%%d" (
        rmdir /s /q "%%d" 2>nul
        set /a CACHE_COUNT+=1
    )
)
if exist "%BACKEND_DIR%\.ruff_cache" (
    rmdir /s /q "%BACKEND_DIR%\.ruff_cache" 2>nul
    set /a CACHE_COUNT+=1
)
del /s /q "%BACKEND_DIR%\*.pyc" >nul 2>&1
call :print_color "%GREEN%" "[OK] Removed !CACHE_COUNT! cache directories and .pyc files"

:: Remove downloaded models
if "%CLEAN_MODELS%"=="true" (
    if exist "%MODELS_DIR%" (
        call :print_color "%BLUE%" "[INFO] Removing downloaded models..."
        rmdir /s /q "%MODELS_DIR%"
        call :print_color "%GREEN%" "[OK] Removed backend\models"
    ) else (
        call :print_color "%BLUE%" "[INFO] No models directory found, skipping"
    )
)
echo.

echo %CYAN%=====================================================================%RESET%
echo %CYAN%  Cleaning Frontend                                                   %RESET%
echo %CYAN%=====================================================================%RESET%
echo.

:: Remove node_modules
if exist "%FRONTEND_DIR%\node_modules" (
    call :print_color "%BLUE%" "[INFO] Removing node_modules (this may take a moment)..."
    rmdir /s /q "%FRONTEND_DIR%\node_modules"
    if errorlevel 1 (
        call :print_color "%YELLOW%" "[WARN] Could not fully remove node_modules - some files may be locked"
    ) else (
        call :print_color "%GREEN%" "[OK] Removed frontend\node_modules"
    )
) else (
    call :print_color "%BLUE%" "[INFO] No node_modules found, skipping"
)

:: Remove build output
if exist "%FRONTEND_DIR%\dist" (
    call :print_color "%BLUE%" "[INFO] Removing build output..."
    rmdir /s /q "%FRONTEND_DIR%\dist"
    call :print_color "%GREEN%" "[OK] Removed frontend\dist"
) else (
    call :print_color "%BLUE%" "[INFO] No build output found, skipping"
)
echo.

echo %CYAN%=====================================================================%RESET%
echo %CYAN%  Cleaning Project Root                                               %RESET%
echo %CYAN%=====================================================================%RESET%
echo.

:: Remove root-level caches
if exist "%PROJECT_ROOT%.pytest_cache" (
    rmdir /s /q "%PROJECT_ROOT%.pytest_cache" 2>nul
    call :print_color "%GREEN%" "[OK] Removed root .pytest_cache"
)

:: Remove .env if requested
if "%CLEAN_ENV%"=="true" (
    if exist "%PROJECT_ROOT%.env" (
        call :print_color "%BLUE%" "[INFO] Removing .env configuration..."
        del /q "%PROJECT_ROOT%.env"
        call :print_color "%GREEN%" "[OK] Removed .env"
    ) else (
        call :print_color "%BLUE%" "[INFO] No .env file found, skipping"
    )
)
echo.

echo %GREEN%=====================================================================%RESET%
echo %GREEN%  Clean Complete!                                                     %RESET%
echo %GREEN%=====================================================================%RESET%
echo.
echo  To reinstall everything, run:  setup.bat
echo.
pause
exit /b 0

:print_color
echo %~1%~2%RESET%
goto :eof
