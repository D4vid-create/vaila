@echo off
REM This script installs or updates the vailá environment on Windows

echo Starting vailá installation on Windows...

REM Ensure the script is running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo This script requires administrative privileges. Please run as administrator.
    exit /b
)

REM Ensure the script is running in Anaconda PowerShell
if not defined CONDA_PREFIX (
    echo This script must be run in Anaconda PowerShell. Please open Anaconda PowerShell and run this script.
    exit /b
)

REM Check if winget is available in the system path
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo Winget not found. Please install Winget manually.
    exit /b
)

REM Check if conda is available in the system path
where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo Conda not found. Please make sure Anaconda or Miniconda is installed and added to the PATH.
    exit /b
)

REM Check if the "vaila" environment already exists
echo Checking if vailá Conda environment exists...
conda env list | findstr /i "vaila" >nul 2>&1
if %errorlevel% equ 0 (
    echo Conda environment 'vaila' already exists. Updating it...
    REM Update the existing environment
    conda env update -f yaml_for_conda_env\vaila_win.yaml --prune
    if %errorlevel% neq 0 (
        echo Failed to update 'vaila' environment.
        exit /b
    ) else (
        echo 'vaila' environment updated successfully.
    )
) else (
    REM Create the environment if it does not exist
    echo Creating Conda environment from vaila_win.yaml...
    conda env create -f yaml_for_conda_env\vaila_win.yaml
    if %errorlevel% neq 0 (
        echo Failed to create 'vaila' environment.
        exit /b
    ) else (
        echo 'vaila' environment created successfully.
    )
)

REM Install FFmpeg using winget
echo Installing FFmpeg...
winget install ffmpeg -e --id Gyan.FFmpeg

REM Configure vailá in the Windows Terminal JSON
echo Configuring Windows Terminal...

REM Path to the Windows Terminal settings JSON (adjust as needed)
set WT_CONFIG_PATH=%LocalAppData%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json

REM Define the vailá profile JSON entry
set VAILA_PROFILE={"colorScheme": "Vintage", "commandline": "pwsh.exe -ExecutionPolicy ByPass -NoExit -Command \"& 'C:\\ProgramData\\anaconda3\\shell\\condabin\\conda-hook.ps1'; conda activate 'vaila'; python 'vaila.py'\"", "guid": "{17ce5bfe-17ed-5f3a-ab15-5cd5baafed5b}", "hidden": false, "icon": "C:\\vaila_programs\\vaila\\vaila\\images\\vaila_ico.png", "name": "vailá", "startingDirectory": "C:\\vaila_programs\\vaila"}

REM Backup the current settings.json
copy "%WT_CONFIG_PATH%" "%WT_CONFIG_PATH%.bak"

REM Try to use PowerShell to insert the profile into the JSON
echo Attempting to automatically add the vailá profile to Windows Terminal...
powershell -Command "(Get-Content -Raw '%WT_CONFIG_PATH%') -replace '\"profiles\": {', '\"profiles\": {\n    \"list\": [%VAILA_PROFILE%, ' | Set-Content -Path '%WT_CONFIG_PATH%'"

REM Check if the modification was successful
if %errorlevel% neq 0 (
    echo.
    echo Automatic insertion into Windows Terminal settings failed.
    echo.
    echo Please add the following profile to your Windows Terminal settings.json file manually:
    echo ---------------------------------------------------------
    echo {
    echo     "colorScheme": "Vintage",
    echo     "commandline": "pwsh.exe -ExecutionPolicy ByPass -NoExit -Command \"& 'C:\\ProgramData\\anaconda3\\shell\\condabin\\conda-hook.ps1' ; conda activate 'vaila' ; python 'vaila.py' \"",
    echo     "guid": "{17ce5bfe-17ed-5f3a-ab15-5cd5baafed5b}",
    echo     "hidden": false,
    echo     "icon": "C:\\vaila_programs\\vaila\\vaila\\images\\vaila_ico.png",
    echo     "name": "vailá",
    echo     "startingDirectory": "C:\\vaila_programs\\vaila"
    echo }
    echo ---------------------------------------------------------
    echo You can find the settings.json file at:
    echo %WT_CONFIG_PATH%
    echo.
    echo Installation completed with manual steps required.
) else (
    echo Installation and configuration completed successfully!
)

pause

