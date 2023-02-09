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
    echo "Upgrading pip"
    pip install --upgrade pip
    python3 -m pip --disable-pip-version-check install -t $HOME/${venv}/lib/python3.10/site-packages --no-cache-dir --upgrade -r all-requirements.txt && success=1
}

ve "$@"