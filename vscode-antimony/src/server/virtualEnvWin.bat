@echo off

echo "script runs"

setlocal
set py=%1
if "%py%"=="" set py=python3.9
set venv=venv_vscode_antimony_virtual_env

echo "running install virtual env"

rem If not already in virtualenv
rem %VIRTUAL_ENV% is being set from %venv%\Scripts\activate.bat script
if "%VIRTUAL_ENV%"=="" (
    if not exist %venv% (
        echo Creating and activating virtual environment %venv%
        echo "%USERPROFILE%\%venv%"
        py -m venv "%USERPROFILE%\%venv%" --system-site-package
        echo Upgrading pip
        py -m pip install --upgrade pip
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
        echo AMAS-sb==0.0.1 ^  
        echo orjson==3.8.0
        echo tellurium
        echo jupyter) > "%USERPROFILE%\%venv%"\all-requirements.txt
        py -m pip --disable-pip-version-check install -t "%USERPROFILE%\%venv%\Lib\site-packages" --no-cache-dir --upgrade -r "%USERPROFILE%\%venv%"\all-requirements.txt && success=1
    ) else (
        echo Virtual environment %venv% already exists, activating...
    )
) else (
    echo Already in a virtual environment!
)
