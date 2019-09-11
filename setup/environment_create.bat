@echo off
REM - This script creates a new environment based on an environment.yml located in this file directory

REM - Read setup configuration
call %~dp0\setup_config.bat

IF NOT EXIST %ENVIRONMENT_FOLDER% (
	@echo on
	echo Please wait while the environment %ENVIRONMENT_FOLDER% is created ...
	
	IF EXIST %~dp0\environment.yml (
		call %MINICONDA_INSTALL_FOLDER%\Scripts\activate.bat %MINICONDA_INSTALL_FOLDER% && conda env create -f %~dp0\environment.yml
	) ELSE (
		call %MINICONDA_INSTALL_FOLDER%\Scripts\activate.bat %MINICONDA_INSTALL_FOLDER% && conda create -y -n %ENVIRONMENT_NAME% python=%PYTHON_VERSION% %PYTHON_DEPENDENCIES%
	)
	
	call copy NUL %~dp0\ENV_OK
	
)
