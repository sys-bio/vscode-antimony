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
    local venv="vscode_antimony_virtual_env"
    echo "running install virtual env"

    echo "Creating and activating virtual environment ${venv}"
    # virtualenv ~/[${venv}]
    current_script_path=$(dirname "$0")
    current_path_to_python="$current_script_path/../server/VscodeAntimonySetup/bin/python3.9"
    sudo -u $USER $current_path_to_python -m venv $HOME/${venv} --system-site-package
    echo $'appdirs==1.4.4\ncertifi==2020.12.5\nchardet==4.0.0\ncolorama==0.4.4\ncolorlog==4.8.0 \neasydev==0.11.0\nidna==2.10\ngit+https://github.com/lark-parser/lark.git@5b8c04ca83b9#egg=lark_parser\nlibChEBIpy==1.0.10\npexpect==4.8.0\nptyprocess==0.7.0\npygls==0.9.1\nrequests==2.25.1\nrequests-cache==0.5.2\nsix==1.15.0\nurllib3==1.26.4\nantimony\nbioservices==1.8.3\n# ols_client==0.0.9\nAMAS-sb==0.0.1\norjson==3.8.0\nnumpy==1.24.2' > $HOME/${venv}/all-requirements.txt
    $current_path_to_python -m pip --disable-pip-version-check install -t $HOME/${venv}/lib/python3.9/site-packages --no-cache-dir --upgrade -r $HOME/${venv}/all-requirements.txt && success=1
}

ve "$@"     