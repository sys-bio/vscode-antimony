@echo off

setlocal
set "py=%USERPROFILE%\Downloads\VSCode-Antimony-Dependency-Installer\python\python"
set "venv=vscode_antimony_virtual_env"
set "spacePath=%USERPROFILE%\%venv%"
set "hasSpace=0"
set "reqs=%spacePath%\all-requirements.txt"
set "sitePacks=%spacePath%\Lib\site-packages"

setlocal enabledelayedexpansion
set "modified=!USERNAME: =!"
echo %USERNAME%
echo %modified%
if not "%USERNAME%"=="%modified%" (
    echo "We have a space in the username"
    set py="%USERPROFILE%\Downloads\VSCode-Antimony-Dependency-Installer\python\python"
    set reqs="%spacePath%\all-requirements.txt"
    set sitePacks="%spacePath%\Lib\site-packages"
    set spacePath="%USERPROFILE%\%venv%"
)

echo running install virtual env

rem If not already in virtualenv
rem %VIRTUAL_ENV% is being set from %venv%\Scripts\activate.bat script

echo Creating and activating environment %venv%

%py% -m pip install virtualenv
%py% -m virtualenv %spacePath%

(echo appdirs==1.4.4
echo certifi==2020.12.5
echo chardet==4.0.0 ^ 
echo colorama==0.4.4 ^ 
echo colorlog==4.8.0 ^ 
echo easydev==0.11.0 ^ 
echo idna==2.10 ^ 
echo git+https://github.com/lark-parser/lark.git@5b8c04ca83b9#egg=lark_parser ^ 
echo libChEBIpy==1.0.10 ^ 
echo pexpect==4.8.0 ^ 
echo ptyprocess==0.7.0 ^ 
echo pygls==0.9.1 ^ 
echo requests==2.25.1 ^ 
echo requests-cache==0.5.2 ^ 
echo six==1.15.0 ^ 
echo urllib3==1.26.4 ^ 
echo antimony ^ 
echo bioservices==1.8.3 ^ 
echo # ols_client==0.0.9 ^ 
echo AMAS-sb==0.0.4 ^ 
echo orjson==3.8.0 ^ 
echo numpy==1.24.2) > %reqs%

(echo step:1
echo totalSteps:2
echo output:Installing dependencies...) > %TEMP%\progress_output.txt

%py% -m pip --disable-pip-version-check install -t %sitePacks% --no-cache-dir --upgrade -r %reqs% && (
  (echo step:2
  echo totalSteps:2
  echo output:Installation finished successfully.) > %TEMP%\progress_output.txt
  exit /b 0
) || (
  (echo step:2
  echo totalSteps:2
  echo output:Installation encountered an error.) > %TEMP%\progress_output.txt
  exit /b 1
)