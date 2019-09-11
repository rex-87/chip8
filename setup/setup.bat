@echo off
REM - Read setup configuration
call %~dp0\setup_config.bat

@echo off
REM - Install miniconda if necessary.
call %~dp0\miniconda_install.bat

@echo off
REM - Create environment.
call %~dp0\environment_create.bat

@echo off
REM - Update environment if necessary
IF NOT EXIST %~dp0\ENV_OK (	
	
	call %~dp0\environment_remove.bat
	call %~dp0\environment_create.bat
	
)
