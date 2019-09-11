@echo off
REM - This script will download miniconda from the official url and (silently) install it in the user profile directory.
REM - If already installed, this script will not do anything.
REM - Details:
REM -    https://conda.io/projects/conda/en/latest/user-guide/install/windows.html

REM - Read setup configuration
call %~dp0\setup_config.bat

IF NOT EXIST %MINICONDA_INSTALL_FOLDER% (
	@echo on
	echo Downloading Miniconda in %MINICONDA_DOWNLOAD_FOLDER% ...
	powershell -Command "Invoke-WebRequest %MINICONDA_DOWNLOAD_URL% -OutFile %MINICONDA_DOWNLOAD_FOLDER%\%MINICONDA_SETUP_FILENAME%"
	echo Please wait while Miniconda is installed in %MINICONDA_INSTALL_FOLDER% ...
	call %MINICONDA_DOWNLOAD_FOLDER%\%MINICONDA_SETUP_FILENAME% /InstallationType=JustMe /RegisterPython=0 /S /D=%MINICONDA_INSTALL_FOLDER%
)
