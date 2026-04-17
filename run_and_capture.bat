@echo off
chcp 65001 >nul
cd /d C:\coder\app\ca-analyzer\dist
echo [%date% %time%] Starting exe... >> ..\..\..\..\..\coder\workspace-main\exe_test.log
start /wait /b ca-analyzer.exe 2>&1 >> ..\..\..\..\..\coder\workspace-main\exe_test.log
echo [%date% %time%] Exit code: %errorlevel% >> ..\..\..\..\..\coder\workspace-main\exe_test.log
