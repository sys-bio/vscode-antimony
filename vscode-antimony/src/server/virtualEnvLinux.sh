#!/bin/bash

TMP_FILE="/tmp/progress_output.txt"

ve() {
    local venv="vscode_antimony_virtual_env"
    echo "Creating and activating virtual environment ${venv}"

    python3 -m venv $HOME/${venv} --system-site-package

    echo $'appdirs==1.4.4\ncertifi==2020.12.5\nchardet==4.0.0\ncolorama==0.4.4\ncolorlog==4.8.0 \neasydev==0.11.0\nidna==2.10\ngit+https://github.com/lark-parser/lark.git@5b8c04ca83b9#egg=lark_parser\nlibChEBIpy==1.0.10\npexpect==4.8.0\nptyprocess==0.7.0\npygls==0.9.1\nrequests==2.25.1\nrequests-cache==0.5.2\nsix==1.15.0\nurllib3==1.26.4\nantimony\nbioservices==1.8.3\n==0.0.9\norjson==3.8.0\npython-libsbml' > $HOME/${venv}/all-requirements.txt

    total_steps=$(wc -l < $HOME/${venv}/all-requirements.txt)
    current_step=0

    # Install each dependency one at a time
    while IFS= read -r dependency; do
        current_step=$((current_step + 1))
        echo "Installing $dependency... ($current_step/$total_steps)"

        # Execute the command and capture the output
        output=$(python3 -m pip --disable-pip-version-check install -t $HOME/${venv}/lib/python3.9/site-packages --no-cache-dir --upgrade $dependency 2>&1)

        # Write the progress and output to a temporary file
        echo "step:$current_step" > $TMP_FILE
        echo "totalSteps:$total_steps" >> $TMP_FILE
        echo "output:$output" >> $TMP_FILE

        echo "Installed $dependency"
    done < $HOME/${venv}/all-requirements.txt

    # Update the progress to 100% once the command execution is completed
    echo "step:$total_steps" > $TMP_FILE
    echo "totalSteps:$total_steps" >> $TMP_FILE

    success=1
}

ve "$@"