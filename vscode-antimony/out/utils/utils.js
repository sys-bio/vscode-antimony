"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.sleep = exports.execPromise = exports.pythonInterpreterError = void 0;
const vscode = require("vscode");
const cp = require("child_process");
let debug = vscode.window.createOutputChannel("Debug1");
debug.show();
// util function for showing python interpreter error message
async function pythonInterpreterError() {
    const choice = await vscode.window.showErrorMessage('Language server not running. Select a valid Python interpreter', 'Edit in settings');
    if (choice === 'Edit in settings') {
        await vscode.commands.executeCommand('workbench.action.openSettings', 'vscode-antimony.pythonInterpreter');
    }
}
exports.pythonInterpreterError = pythonInterpreterError;
// convert cp.exec to a promise
function execPromise(command) {
    return new Promise(function (resolve, reject) {
        cp.exec(command, (err, stdout, stderr) => {
            if (err) {
                debug.append(err.toString());
                reject(err);
            }
            else {
                resolve({
                    stdout,
                    stderr,
                });
            }
        });
    });
}
exports.execPromise = execPromise;
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
exports.sleep = sleep;
//# sourceMappingURL=utils.js.map