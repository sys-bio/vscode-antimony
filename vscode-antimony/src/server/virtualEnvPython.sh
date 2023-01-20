#!/usr/bin/env bash

# Logical conditions:
# 0. If not already in virtualenv:
# 0.1. If virtualenv already exists activate it,
# 0.2. If not create it with global packages, update pip then activate it
# 1. If already in virtualenv: just give info
#
# Usage:
# Without arguments it will create virtualenv named `.venv_vscode_antimony_virtual_env` with `python3.9` version
# $ ve
# or for a specific python version
# $ ve python3.9
# or for a specific python version and environment name;
# $ ve python3.9 ./.venv-diff

echo "script runs"

ve() {
    local py=${1:-python3.9}
    local venv="venv_vscode_antimony_virtual_env"

    local bin="${venv}/bin/activate"

    echo "running install virtual env"
    # If not already in virtualenv
    # $VIRTUAL_ENV is being set from $venv/bin/activate script
    if [ -z "${VIRTUAL_ENV}" ]; then
        if [ ! -d ${venv} ]; then
            echo "Creating and activating virtual environment ${venv}"
            # chmod u+x /env
            virtualenv ~/[${venv}]
            source ~/[${venv}]/bin/activate
            sudo -u $USER ${py} -m venv ${venv} --system-site-package
            echo "export PYTHON=${py}" >> ${bin}    # overwrite ${python} on .zshenv
            source ${bin}
            echo "Upgrading pip"
            ${py} -m pip install --upgrade pip
            python3 -m pip --disable-pip-version-check install -t ./pythonFiles/lib/python --no-cache-dir --upgrade -r ./all-requirements.txt && success=1
        else
            return "Virtual environment ${venv} already exists, activating..."
        fi
    else
        return "Already in a virtual environment!"
    fi
}

ve "$@"