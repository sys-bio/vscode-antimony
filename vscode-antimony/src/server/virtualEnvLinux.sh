#!/bin/bash

# Logical conditions:
# 0. If not already in virtualenv:
# 0.1. If virtualenv already exists activate it,
# 0.2. If not create it with global packages, update pip then activate it
# 1. If already in virtualenv: just give info
#
# Usage:
# Without arguments it will create virtualenv named .venv_vscode_antimony_virtual_env with python3 version
# $ ve
# or for a specific python version
# $ ve python3.10
# or for a specific python version and environment name;
# $ ve python3.10 ./.venv-diff

ve() {
    local py=${1:-python3}
    local venv="venv_vscode_antimony_virtual_env"

    echo "Creating and activating virtual environment ${venv}"
    python3 -m venv $HOME/${venv}

    echo 'appdirs==1.4.4
certifi==2020.12.5
chardet==4.0.0
colorama==0.4.4
colorlog==4.8.0
easydev==0.11.0
idna==2.10
git+https://github.com/lark-parser/lark.git@5b8c04ca83b9#egg=lark_parser
libChEBIpy==1.0.10
pexpect==4.8.0
ptyprocess==0.7.0
pygls==0.9.1
requests==2.25.1
requests-cache==0.5.2
six==1.15.0
urllib3==1.26.4
antimony
bioservices==1.8.3
# ols_client==0.0.9
AMAS-sb==0.0.1
orjson==3.8.0' > $HOME/${venv}/all-requirements.txt

    python3 -m pip --disable-pip-version-check install -t $HOME/${venv}/lib/python3.10/site-packages --no-cache-dir --upgrade -r $HOME/venv_vscode_antimony_virtual_env/all-requirements.txt && success=1
}

ve "$@"