@echo off
cd /d "%~dp0.."
echo ========================================
echo Building DIV Timeline Puzzle EXE
echo ========================================
echo.

REM Install PyInstaller if not already installed
echo Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
) else (
    echo PyInstaller already installed.
)
echo.

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
echo.

REM Build executable using spec file
echo Building executable...
pyinstaller DIV.spec

echo.
if %errorlevel% equ 0 (
    echo ========================================
    echo Build successful!
    echo Executable location: dist\DIV-Timeline-Puzzle.exe
    echo ========================================
    echo.
    echo You can now run: dist\DIV-Timeline-Puzzle.exe
    echo.
) else (
    echo ========================================
    echo Build failed! Please check the errors above.
    echo ========================================
)

pause
