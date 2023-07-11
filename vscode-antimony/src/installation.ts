import * as shell from 'shelljs'
import * as vscode from 'vscode';
import * as path from 'path';
import * as os from 'os';
import * as fs from 'fs';

const platform = os.platform().toString();
const action = 'Reload';

function activateVirtualEnv(pythonPath) {
  if (vscode.workspace.getConfiguration('vscode-antimony').get('pythonInterpreter') !== pythonPath) {
    vscode.workspace.getConfiguration('vscode-antimony').update('pythonInterpreter', pythonPath, true);
    vscode.window.showInformationMessage('Virtual environment exists, it is activated now.');
  }
}

// setup virtual environment
export async function createVirtualEnv(context: vscode.ExtensionContext) {
  await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");

  const venvPaths = {
    darwin: path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python"),
    win32: path.normalize(os.homedir() + "/vscode_antimony_virtual_env/Scripts/python"),
    win64: path.normalize(os.homedir() + "/vscode_antimony_virtual_env/Scripts/python"),
    linux: path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python3.10"),
  };

  if (fs.existsSync(venvPaths[platform])) {
    activateVirtualEnv(venvPaths[platform]);
  } else {
    let message = `To install dependencies so the extension works properly, allow installation of virtual environment`;

    const win32Win64PackagePath = path.normalize(os.homedir() + "\\Downloads\\VSCode-Antimony-Dependency-Installer");
    const darwinPackagePath = path.normalize(path.join(os.homedir(), "..", "VscodeAntimonySetup", "bin", "python3.9"));

    if (!fs.existsSync(win32Win64PackagePath) && (platform === 'win32' || platform === 'win64')) {
      showInstallPackageMessage("https://github.com/sys-bio/vscode-antimony#installation-required-1");
    } else if (!fs.existsSync(darwinPackagePath) && platform === 'darwin') {
      showInstallPackageMessage("https://github.com/sys-bio/vscode-antimony#installation-required-1");
    } else {
      vscode.window.showInformationMessage(message, { modal: true }, ...['Yes', 'No'])
        .then(async selection => {
          if (selection === 'Yes') {
            installEnv();
          } else if (selection === 'No') {
            vscode.window.showInformationMessage('The default python interpreter will be used.');
          }
        });
    }
  }
}

function showInstallPackageMessage(link: string) {
  vscode.window.showInformationMessage("The required installation package has not been downloaded. Open link to installation instructions?", { modal: true }, ...['Yes', 'No'])
    .then(async selection => {
      if (selection === 'Yes') {
        vscode.env.openExternal(vscode.Uri.parse(link));
        const action = 'Reload';
        vscode.window.showInformationMessage("Once the installation package is downloaded, press Yes to restart window", { modal: true }, "Yes")
          .then(() => {
            vscode.commands.executeCommand('workbench.action.reloadWindow');
          });
      } else if (selection === 'No') {
        vscode.window.showInformationMessage('Vscode-Antimony will not install without the required installation package.');
      }
    });
}

async function installEnv() {
  let shellScriptPath;

  if (platform === 'darwin') {
    const isAppleSilicon = process.arch === 'arm64';
    shellScriptPath = 'sh ' + path.join(__dirname, '..', 'src', 'server', isAppleSilicon ? 'virtualEnvSilicon.sh' : 'virtualEnvIntelMac.sh');
  } else if (platform === 'win32' || platform === 'win64') {
    shellScriptPath = path.join(__dirname, '..', 'src', 'server', 'virtualEnvWin.bat');
  } else if (platform === 'linux') {
    shellScriptPath = 'sh ' + path.join(__dirname, '..', 'src', 'server', 'virtualEnvLinux.sh');
  } else {
    console.error('Unsupported platform:', platform);
    return;
  }

  const virtualEnvPath = process.env.VIRTUAL_ENV;
  if (virtualEnvPath && virtualEnvPath !== path.normalize(os.homedir() + '/vscode_antimony_virtual_env')) {
    await vscode.window.showInformationMessage(`Deactivate current active virtual environment before allowing antimony virtual environment installation.`, action).then((selectedAction) => {
    if (selectedAction === action) {
      vscode.commands.executeCommand('workbench.action.reloadWindow');
    }
    });
  } else {
    const userIsSpaced = os.userInfo().username.includes(' ');
    await executeProgressBar(userIsSpaced ? `"${shellScriptPath}"` : shellScriptPath);
  }
}

async function executeProgressBar(filePath: string) {
  try {
    await progressBar(filePath);
    showInstallationFinishedMessage();
  } catch (error) {
    const isAppleSilicon = process.arch === 'arm64';
    if (isAppleSilicon) {
    showInstallationErrorMessage(
      `Installation Error. Download Python3.9. Click "Retry" once Python3.9 has been installed. Link: https://www.python.org/ftp/python/3.9.13/python-3.9.13-macos11.pkg.`,
      () => {
      console.log(error)
      let shellScriptPath: string;
      shellScriptPath = 'sh ' + path.join(__dirname, '..', 'src', 'server', 'virtualEnvIntelMac.sh');
      progressBar(shellScriptPath).then(() => {
        showInstallationFinishedMessage();
      });
      }
    );
    } else {
    showInstallationErrorMessage("Once window is reloaded, right click and press 'Delete Virtual Environment'. Installation Error. Try again.", () => {
      vscode.commands.executeCommand('workbench.action.reloadWindow');
    });
    }
  }
}

function showInstallationFinishedMessage() {
  vscode.window.showInformationMessage(
    `Installation finished. Reload to activate. Right click in the editor after reload to view features.`,
    { modal: true },
    action
  ).then(selectedAction => {
    if (selectedAction === action) {
    vscode.commands.executeCommand('workbench.action.reloadWindow');
    }
  });
}

function showInstallationErrorMessage(message: string, retryCallback: () => void) {
  vscode.window.showErrorMessage(message, { modal: true }, "Retry")
    .then(async selection => {
    if (selection === 'Retry') {
      retryCallback();
    }
    });
}

async function progressBar(filePath: string) {
  return vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Running installation... Do NOT close VSCode. (Appx 5 minutes)",
      cancellable: false
    },
    async (progress, token) => {
      await new Promise<void>((resolve, reject) => {
        shell.exec(`${filePath}`, (err, stdout, stderr) => {
          if (err || stderr) {
            // Handle the error from the shell script execution
            reject(err);
			return err;
          } else {
            // Continue with the progress if no error occurred
            const interpreterPaths = {
              darwin: path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python"),
              win32: path.normalize(os.homedir() + "/vscode_antimony_virtual_env/Scripts/python"),
              win64: path.normalize(os.homedir() + "/vscode_antimony_virtual_env/Scripts/python"),
              linux: path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python3.10"),
            };

            const pythonInterpreterPath = interpreterPaths[platform];

            vscode.workspace.getConfiguration('vscode-antimony').update('pythonInterpreter', pythonInterpreterPath, true);

            resolve();
          }
        });
      });
    }
  );
}

export async function venvErrorFix() {
  const venvPath = path.normalize(os.homedir() + "/vscode_antimony_virtual_env/");
  const isWin = platform === 'win32' || platform === 'win64';
  const hasPip = fs.existsSync(path.normalize(os.homedir() + "/vscode_antimony_virtual_env/Scripts/pip3.11.exe"));
  const hasPythonDarwin = fs.existsSync(path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python3.9"));
  const hasPythonLinux = fs.existsSync(path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python3.10"));

	if (fs.existsSync(venvPath)) {
		const message = (platform == 'linux' && !hasPythonLinux) || (isWin && !hasPip) || (platform === 'darwin' && !hasPythonDarwin)
			? "The incorrect version of python has been installed. Refer to Vscode-Antimony install instructions before restarting VSCode and reinstalling virtual environment. Open link to installation instructions and delete installed virtual environment?"
			: "Delete installed virtual environment?";

		await deleteVirtualEnv(message);
  }
}

 async function deleteVirtualEnv(message) {
  vscode.window.showInformationMessage(message, { modal: true }, ...['Yes', 'No'])
    .then(async selection => {
      // installing virtual env
      if (selection === 'Yes') {
        if (message === "The incorrect version of python has been installed. Refer to Vscode-Antimony install instructions before restarting VSCode and reinstalling virtual environment. Open link to installation instructions and delete installed virtual environment?") {
          vscode.env.openExternal(vscode.Uri.parse("https://github.com/sys-bio/vscode-antimony#installation-required-1"));
        }
        if (platform == 'win32' || platform == 'win64') {
          fs.rmSync(path.normalize(os.homedir() + "/vscode_antimony_virtual_env/Scripts/python"));
          promptToReloadWindow("Reload for changes to take effect.")
        } else if (platform == "darwin") {
          fs.rmSync(path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python3.9"));
          promptToReloadWindow("Reload for changes to take effect.")
        } else {
          fs.rmSync(path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python3.10"));
          promptToReloadWindow("Reload for changes to take effect.")
        }
      } else if (selection === 'No') {
        vscode.env.openExternal(vscode.Uri.parse("https://github.com/sys-bio/vscode-antimony#installation-required-1"));
        vscode.window.showWarningMessage(`The extension will not work without deleting and reinstalling the virtual environment.`, {modal: true}, action)
          .then(selectedAction => {
            if (selectedAction === action) {
              vscode.commands.executeCommand('workbench.action.reloadWindow');
            }
          });
      }
    });
}

/** Prompts user to reload editor window in order for configuration change to take effect. */
function promptToReloadWindow(message: string) {
    const action = 'Reload';
  
    vscode.window
      .showInformationMessage(
      message,
      {modal: true},
      action
      )
      .then(selectedAction => {
        if (selectedAction === action) {
        vscode.commands.executeCommand('workbench.action.reloadWindow');
        }
      });
  }