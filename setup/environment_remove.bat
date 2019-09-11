@echo off
REM - This script removes the environment "ENVIRONMENT_NAME"

REM - Read setup configuration
call %~dp0\setup_config.bat

IF EXIST %ENVIRONMENT_FOLDER% (
	@echo on
	echo Please wait while the environment %ENVIRONMENT_FOLDER% is removed ...
	call %MINICONDA_INSTALL_FOLDER%\Scripts\activate.bat %MINICONDA_INSTALL_FOLDER% && conda remove -n %ENVIRONMENT_NAME% --all -y
)
