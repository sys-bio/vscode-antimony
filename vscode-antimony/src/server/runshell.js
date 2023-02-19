#!/bin/bash

const os = require('os');
const path = require('path');
const { exec } = require("child_process")

const current_path_to_silicon_shell = path.join(__dirname, '..', 'server', 'virtualEnvSilicon.sh');
const current_path_to_linux_shell = path.join(__dirname, '..', 'server', 'virtualEnvLinux.sh');
const current_path_to_dir = path.join(__dirname, '..');

if (os.platform().toString() === 'darwin') {
    exec(`sh ${current_path_to_silicon_shell}`)
} else if (os.platform().toString() === 'win32') {
    const path_to_win_shell = path.join(__dirname);
    exec(`${path_to_win_shell}\\virtualEnvWin.bat`)
} else if (os.platform().toString() === 'linux') {
    shell.cd(current_path_to_dir)
    exec(`bash ${current_path_to_linux_shell}`);
}