#!/bin/bash

import * as os from 'os';
import * as path from 'path';

console.log('Hello from TypeScript!');

var shell = require('shelljs');
shell.echo ("script runs");
var current_path_to_silicon_shell = path.join(__dirname, '..', 'src', 'server', 'virtualEnvSilicon.sh');

console.log(os.platform().toString())

if (os.platform().toString() == 'darwin' || os.platform().toString() == 'linux') {
    shell.exec('sh ' + current_path_to_silicon_shell)
} else if (os.platform().toString() == 'win32') {
    console.log(path.join(__dirname, 'server'))
    var path_to_win_shell = path.join(__dirname, 'server');
    var path_to_user_folder = path.join(__dirname, '..', '..')
    console.log(path_to_user_folder)
    // shell.exec('cd ~')
    shell.cd(path_to_win_shell)
    shell.exec(path_to_win_shell + '\\virtualEnvWin.bat')
}