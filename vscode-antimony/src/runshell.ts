#!/bin/bash

import * as os from 'os';
import * as path from 'path';

var shell = require('shelljs');
var current_path_to_silicon_shell = path.join(__dirname, '..', 'src', 'server', 'virtualEnvSilicon.sh');
var current_path_to_linux_shell = path.join(__dirname, '..', 'src', 'server', 'virtualEnvLinux.sh');
var current_path_to_dir = path.join(__dirname, '..');

if (os.platform().toString() == 'darwin') {
    shell.exec('sh ' + current_path_to_silicon_shell)
} else if (os.platform().toString() == 'win32') {
    var path_to_win_shell = path.join(__dirname, 'server');
    shell.cd(path_to_win_shell)
    shell.exec(path_to_win_shell + '\\virtualEnvWin.bat')
} else if (os.platform().toString() == 'linux') {
    shell.cd(current_path_to_dir)
    shell.exec("sh " + current_path_to_linux_shell);
}