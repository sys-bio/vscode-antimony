#!/bin/bash

const os = require('os');
const path = require('path');

const shell = require('shelljs');
const current_path_to_silicon_shell = path.join(__dirname, '..', 'server', 'virtualEnvSilicon.sh');
const current_path_to_linux_shell = path.join(__dirname, '..', 'server', 'virtualEnvLinux.sh');
const current_path_to_dir = path.join(__dirname, '..');

if (os.platform().toString() === 'darwin') {
    shell.exec(`sh ${current_path_to_silicon_shell}`)
} else if (os.platform().toString() === 'win32') {
    const path_to_win_shell = path.join(__dirname);
    shell.exec(`${path_to_win_shell}\\virtualEnvWin.bat`)
} else if (os.platform().toString() === 'linux') {
    shell.cd(current_path_to_dir)
    shell.exec(`sh ${current_path_to_linux_shell}`);
}