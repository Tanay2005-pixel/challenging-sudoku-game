@echo off
echo Compiling Sudoku C++ Program...
echo.

REM Check if g++ is available
where g++ >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: g++ compiler not found!
    echo Please install MinGW or another C++ compiler
    echo.
    echo For Windows, download from: https://www.mingw-w64.org/
    pause
    exit /b 1
)

REM Compile
echo Compiling sudoku.exe...
g++ -O2 -std=c++17 -o sudoku.exe ^
    main.cpp ^
    generator.cpp ^
    solver.cpp ^
    sudoku_init.cpp ^
    sudoku_graph.cpp ^
    player_graph.cpp

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS! sudoku.exe compiled successfully
    echo.
) else (
    echo.
    echo ERROR! Compilation failed
    echo.
)

pause
