#!/usr/bin/env bash

echo "script runs"

ve() {
  local venv="vscode_antimony_virtual_env"
  echo "Creating and activating virtual environment ${venv}"

  PYTHON39_PATH=$(which python3.9)

  if [[ -z "$PYTHON39_PATH" ]]; then
      echo "Python 3.9 is not installed or not found"
      exit 1
  fi

  sudo -u $USER "$PYTHON39_PATH" -m venv $HOME/${venv} --system-site-package
  
  echo $'appdirs==1.4.4\ncertifi==2020.12.5\nchardet==4.0.0\ncolorama==0.4.4\ncolorlog==4.8.0 \neasydev==0.11.0\nidna==2.10\ngit+https://github.com/lark-parser/lark.git@5b8c04ca83b9#egg=lark_parser\nlibChEBIpy==1.0.10\npexpect==4.8.0\nptyprocess==0.7.0\npygls==0.9.1\nrequests==2.25.1\nrequests-cache==0.5.2\nsix==1.15.0\nurllib3==1.26.4\nantimony\nbioservices==1.8.3\n# ols_client==0.0.9\n# AMAS-sb==0.0.4\norjson==3.8.0' > $HOME/${venv}/all-requirements.txt
  
  # Install each dependency one at a time
  while IFS= read -r dependency; do
      echo "Installing $dependency..."
      "$PYTHON39_PATH" -m pip --disable-pip-version-check install -t $HOME/${venv}/lib/python3.9/site-packages --no-cache-dir --upgrade $dependency
      echo "Installed $dependency"
  done < $HOME/${venv}/all-requirements.txt
}

ve "$@"