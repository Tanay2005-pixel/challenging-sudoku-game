@echo off
echo ========================================
echo Markdown to PDF Converter
echo ========================================
echo.

REM Check if pandoc is installed
where pandoc >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Pandoc is not installed!
    echo.
    echo Please install Pandoc from:
    echo https://pandoc.org/installing.html
    echo.
    echo Or use VS Code with Markdown PDF extension instead.
    pause
    exit /b 1
)

echo Pandoc found! Converting files...
echo.

REM Convert README_CPP.md
echo Converting README_CPP.md...
pandoc README_CPP.md -o README_CPP.pdf --pdf-engine=wkhtmltopdf -V geometry:margin=1in
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] README_CPP.pdf created
) else (
    echo [FAILED] README_CPP.pdf conversion failed
)
echo.

REM Convert README_PYTHON_BACKEND.md
echo Converting README_PYTHON_BACKEND.md...
pandoc README_PYTHON_BACKEND.md -o README_PYTHON_BACKEND.pdf --pdf-engine=wkhtmltopdf -V geometry:margin=1in
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] README_PYTHON_BACKEND.pdf created
) else (
    echo [FAILED] README_PYTHON_BACKEND.pdf conversion failed
)
echo.

REM Convert README_SQL.md
echo Converting README_SQL.md...
pandoc README_SQL.md -o README_SQL.pdf --pdf-engine=wkhtmltopdf -V geometry:margin=1in
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] README_SQL.pdf created
) else (
    echo [FAILED] README_SQL.pdf conversion failed
)
echo.

echo ========================================
echo Conversion Complete!
echo ========================================
echo.
echo PDF files created in current directory:
echo - README_CPP.pdf
echo - README_PYTHON_BACKEND.pdf
echo - README_SQL.pdf
echo.
pause
