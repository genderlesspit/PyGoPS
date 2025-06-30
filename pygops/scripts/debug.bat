@echo off
REM debug.bat - general purpose Go launcher
echo Debug Start Script Directory: %~dp0
cd /d "%~dp0"

echo.
echo Running basic Go file with config...
powershell -ExecutionPolicy Bypass -File ".\go_launcher.ps1" -GoFile "go_dummy.go" -GoArgs "[\"-config_file\", \"prod.json\"]" -Verbose

echo.
echo Running server mode example...
powershell -ExecutionPolicy Bypass -File ".\go_launcher.ps1" -GoFile "go_dummy.go" -GoArgs "[\"-port\", \"8080\"]" -ServerMode -Port 8080 -StopExisting -Verbose

echo.
echo Running dry run example...
powershell -ExecutionPolicy Bypass -File ".\go_launcher.ps1" -GoFile "go_dummy.go" -GoArgs "[]" -DryRun -Verbose

echo.
echo All tests completed.
REM Pause so you can inspect the output
pause