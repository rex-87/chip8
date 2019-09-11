@echo off
REM - Read setup configuration
call %~dp0\setup_config.bat

@echo off
REM - Export environment settings to file
echo Please wait while %~dp0\environment.yml is generated ...
call %MINICONDA_INSTALL_FOLDER%\Scripts\activate.bat %ENVIRONMENT_FOLDER% && conda env export > %~dp0\environment.yml
