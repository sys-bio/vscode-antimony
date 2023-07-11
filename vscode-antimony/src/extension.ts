import * as vscode from 'vscode';
import * as utils from './utils/utils';
import * as path from 'path';
import * as os from 'os';
import * as fs from 'fs';
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions
} from 'vscode-languageclient/node';
import { createAnnotationDialog, navigateAnnotation } from './annotationInput';
import { insertRateLawDialog } from './rateLawInput';
import { SBMLEditorProvider } from './SBMLEditor';
import { AntimonyEditorProvider } from './AntimonyEditor';
import { browseBioModels } from './modelBrowse';
import { TextDocument } from 'vscode';
import { createVirtualEnv, venvErrorFix } from './installation';
import { switchIndicationOff, switchIndicationOn, triggerUpdateDecorations } from './annotationHighlight';

let client: LanguageClient | null = null;
let pythonInterpreter: string | null = null;
let lastChangeInterp = 0;

const action = 'Reload';

let activeEditor = vscode.window.activeTextEditor;

// RoundTripping SBML to Antimony
let roundTripping: boolean | null = null;

// Check if the current file is .txt
async function checkFileExtension() {
  const doc = vscode.window.activeTextEditor.document;
  const uri = doc.uri.toString();
  const fileExtension = path.extname(uri);
  if (fileExtension === '.txt') {
    vscode.window.showInformationMessage('Please save the file as .ant to use VSCode-Antimony, otherwise ignore');
    return;
  }
}

// Activate extension
export async function activate(context: vscode.ExtensionContext) {
  await checkFileExtension();

  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.openStartPage', 
        (...args: any[]) => openStartPage()));

  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.deleteVirtualEnv', 
        (...args: any[]) => venvErrorFix()));

  await createVirtualEnv(context);

  roundTripping = vscode.workspace.getConfiguration('vscode-antimony').get('openSBMLAsAntimony');

  // start the language server
  if (await startLanguageServer(context) === 0) {
    return;
  }

  vscode.workspace.onDidChangeConfiguration(async (e) => {
    // restart the language server using the new Python interpreter, if the related
    // setting was changed
    if (!e.affectsConfiguration('vscode-antimony')) {
      return;
    }
    let curTime = Date.now();
    lastChangeInterp = curTime;
    // delay restarting the client by 3 seconds. i.e. if any other changes were made in 3
    // seconds, then don't do the earlier change
    setTimeout(async () => {
      if (curTime !== lastChangeInterp) {
        return;
      }
      // python interpreter changed. restart language client
      if (client) {
        client.stop();
        client = null;
      }
      await startLanguageServer(context);
    }, 3000);

  });

  // create annotations
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.createAnnotationDialog', 
        (...args: any[]) => createAnnotationDialog(context, args)));

  // create annotations
  // context.subscriptions.push(
  // 	vscode.commands.registerCommand('antimony.recommendAnnotationDialog', 
      // (...args: any[]) => recommendAnnotationDialog(context, args)));

  // insert rate law
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.insertRateLawDialog', 
        (...args: any[]) => insertRateLawDialog(context, args)));

  // switch visual annotations on
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.switchIndicationOn', 
        (...args: any[]) => switchIndicationOn(context)));

  // switch visual annotations off
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.switchIndicationOff', 
        (...args: any[]) => switchIndicationOff(context)));

  // convertion
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.convertAntimonyToSBML', 
        (...args: any[]) => convertAntimonyToSBML(context, args)));
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.convertSBMLToAntimony', 
        (...args: any[]) => convertSBMLToAntimony(context, args)));

  // custom editor
  context.subscriptions.push(await SBMLEditorProvider.register(context, client));
  context.subscriptions.push(await AntimonyEditorProvider.register(context, client));
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.startSBMLWebview', 
        (...args: any[]) => startSBMLWebview(context, args)));
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.startAntimonyWebview', 
        (...args: any[]) => startAntimonyWebview(context, args)));

  // browse biomodels
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.browseBiomodels', 
        (...args: any[]) => browseBioModels(context, args)));

  // navigate to annotation
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.navigateAnnotation', 
        (...args: any[]) => navigateAnnotation(context, args)));

  // language config for CodeLens
  const docSelector = {
    language: 'antimony',
    scheme: 'file',
  };
  let codeLensProviderDisposable = vscode.languages.registerCodeLensProvider(
    docSelector,
    new AntCodeLensProvider()
  );
  context.subscriptions.push(codeLensProviderDisposable);

  // update annotation decorations
  if (activeEditor) {
    triggerUpdateDecorations();
  }

  vscode.window.onDidChangeActiveTextEditor(editor => {
    activeEditor = editor;
    if (editor) {
      triggerUpdateDecorations();
    }
  }, null, context.subscriptions);

  // update decorations on change to file
  vscode.workspace.onDidChangeTextDocument(event => {
    if (activeEditor && event.document === activeEditor.document) {
      triggerUpdateDecorations(true);
    }
  }, null, context.subscriptions);

  // highlight color changes
  vscode.workspace.onDidChangeConfiguration(async (e) => {
    if (!e.affectsConfiguration('vscode-antimony.highlightColor')) {
      return;
    }
    promptToReloadWindow(`Reload window for visual indication change in Antimony to take effect.`);
  });
  
  // open SBML as Ant file
  vscode.workspace.onDidChangeConfiguration(async (e) => {
    if (!e.affectsConfiguration('vscode-antimony.openSBMLAsAntimony')) {
      return;
    }
    setTimeout(() => {
      vscode.commands.executeCommand('workbench.action.reloadWindow');
    }, 2000);
  });

  const sbmlFileNameToPath = new Map();

  // when user opens XML
  if (roundTripping) {
    vscode.workspace.onDidOpenTextDocument(async event => {
      triggerSBMLEditor(event, sbmlFileNameToPath);
    });

    vscode.workspace.onDidSaveTextDocument(savedDoc => {
      const fileName = path.basename(savedDoc.fileName, '.git');
      const pathName = path.dirname(savedDoc.fileName);
      const fullPath = path.join(pathName, fileName);
      const pattern = /^(.+?).ant/;
      if (pattern.test(fileName) && pathName === os.tmpdir()) {
        vscode.workspace.openTextDocument(fullPath).then(doc => {
          vscode.commands.executeCommand('antimony.antStrToSBMLStr', doc.getText())
          .then(async (result: any) => {
            if (result.error) {
              vscode.window.showErrorMessage(`Error while converting: ${result.error}`);
            } else {
              const match = pattern.exec(fileName)[1];
              const sbmlFilePath = path.join(sbmlFileNameToPath[fileName], match + '.xml');
              fs.writeFile(sbmlFilePath, result.sbml_str, error => {
                if (error) {
                  console.error(error);
                }
              });
              vscode.window.showInformationMessage(`Edit saved to: ${match}.xml`);
            }
          });
        });
      }
    });
  }

  if (path.extname(vscode.window.activeTextEditor.document.fileName) === '.xml' && roundTripping) {
    triggerSBMLEditor(vscode.window.activeTextEditor.document, sbmlFileNameToPath);
  }
}

async function triggerSBMLEditor(event: TextDocument, sbmlFileNameToPath: Map<any, any>) {
  await client.onReady();

  if (path.extname(event.fileName) === '.xml') {
    // check if the file is sbml, opens up a new file
    await vscode.window.showTextDocument(event, { preview: true, preserveFocus: false });
    await vscode.commands.executeCommand('workbench.action.closeActiveEditor');
    vscode.commands.executeCommand('antimony.sbmlFileToAntStr', event).then(async (result: any) => {
      if (result.error) {
        vscode.window.showErrorMessage(`Error while converting: ${result.error}`)
      } else {
        const sbmlFileName = path.basename(event.fileName, '.xml');
        const tempDir = os.tmpdir();
        var tempFileName = `${sbmlFileName}.ant`;
        var tempFilePath = path.join(tempDir, tempFileName);
        sbmlFileNameToPath[tempFileName] = path.dirname(event.fileName);
        fs.writeFile(tempFilePath, result.ant_str, (error) => {
          if (error) {
            console.error(error);
          } else {
            console.log('The file was saved to ' + tempFilePath);
          }
        });
        // Create the temporary file and open it in the editor
        const tempFile = vscode.workspace.openTextDocument(tempFilePath).then((doc) => {
          vscode.window.showTextDocument(doc, { preview: false });
          vscode.window.showInformationMessage("Opened " + sbmlFileName + ".xml as Antimony.");
        });

      }
    });
  }
}

async function startSBMLWebview(context: vscode.ExtensionContext, args: any[]) {
  if (!client) {
    utils.pythonInterpreterError();
    return;
  }
  await client.onReady();

  await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");

  vscode.commands.executeCommand("vscode.openWith",
    vscode.window.activeTextEditor.document.uri, "antimony.sbmlEditor", 2);
}

async function startAntimonyWebview(context: vscode.ExtensionContext, args: any[]) {
  if (!client) {
    utils.pythonInterpreterError();
    return;
  }
  await client.onReady();

  await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");

  vscode.commands.executeCommand("vscode.openWith",
    vscode.window.activeTextEditor.document.uri, "antimony.antimonyEditor", 2);
}

async function convertAntimonyToSBML(context: vscode.ExtensionContext, args: any[]) {
  if (!client) {
    utils.pythonInterpreterError();
    return;
  }
  await client.onReady();

  await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");

  const options: vscode.OpenDialogOptions = {
    openLabel: "Select",
    canSelectFolders: true,
    canSelectFiles: false,
    canSelectMany: false,
    filters: {
      'SBML': ['xml']
    },
    title: "Select a location to save your SBML file"
  };
   vscode.window.showOpenDialog(options).then(fileUri => {
     if (fileUri && fileUri[0]) {
         vscode.commands.executeCommand('antimony.antFiletoSBMLFile', vscode.window.activeTextEditor.document,
           fileUri[0].fsPath).then(async (result) => {
        await checkConversionResult(result, "SBML");
      });
     }
   });
}

async function convertSBMLToAntimony(context: vscode.ExtensionContext, args: any[]) {
  if (!client) {
    utils.pythonInterpreterError();
    return;
  }
  await client.onReady();

  await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");

  const options: vscode.OpenDialogOptions = {
      openLabel: "Save",
      canSelectFolders: true,
      canSelectFiles: false,
      canSelectMany: false,
      filters: {
        'Antimony': ['ant']
      },
      title: "Select a location to save your Antimony file"
  };
  vscode.window.showOpenDialog(options).then(folderUri => {
    if (folderUri && folderUri[0]) {
        vscode.commands.executeCommand('antimony.sbmlFileToAntFile', vscode.window.activeTextEditor.document,
        folderUri[0].fsPath).then(async (result) => {
          await checkConversionResult(result, "Antimony");
        });
    }
  });
}

async function checkConversionResult(result, type) {
  if (result.error) {
    vscode.window.showErrorMessage(`Could not convert file to ${type}: ${result.error}`)
  } else {
    vscode.window.showInformationMessage(`${result.msg}`)
    const document = await vscode.workspace.openTextDocument(`${result.file}`)
    vscode.window.showTextDocument(document);
  }
}

export function deactivate(): Thenable<void> | undefined {
  if (!client) {
    return undefined;
  }
  // shut down the language client
  return client.stop();
}

// ****** helper functions ******

// starting language server
async function startLanguageServer(context: vscode.ExtensionContext) {
  pythonInterpreter = getPythonInterpreter();
  // verify the interpreter
  const error = await verifyInterpreter(pythonInterpreter);
  if (error !== 0) {
    let errMessage: string;
    if (error === 1) {
      errMessage = `Failed to launch language server: "${pythonInterpreter}" is not Python 3.7+`;
    } else {
      errMessage = `Failed to launch language server: Unable to run "${pythonInterpreter}"`;
    }
    const choice = await vscode.window.showErrorMessage(errMessage, 'Edit in settings');
    if (choice === 'Edit in settings') {
      await vscode.commands.executeCommand('workbench.action.openSettings', 'vscode-antimony.pythonInterpreter');
    }
    return 0;
  }
  // install dependencies
  // const parentDir = context.asAbsolutePath(path.join(''));
  // console.log(parentDir)
  // const cp = require('child_process')
  // const command = pythonInterpreter + " -m pip --disable-pip-version-check install --no-cache-dir --upgrade -r ./all-requirements.txt"
  // cp.exec("dir", {cwd: parentDir}, (err, stdout, stderr) => {
  // 	console.log('stdout: ' + stdout);
  // 	console.log('stderr: ' + stderr);
  // 	if (err) {
  // 		vscode.window.showErrorMessage(err);
  // 	}
  // });
  // create language client and launch server
  const pythonMain = context.asAbsolutePath(
    path.join('src', 'server', 'main.py')
  );
  const args = [pythonMain];
  // Add debug options here if needed
  const serverOptions: ServerOptions = { command: pythonInterpreter, args };
  const clientOptions: LanguageClientOptions = {
    documentSelector: [
      { scheme: "file", language: "antimony" },
    ],
  };
  // Create the language client and start the client.
  client = new LanguageClient(
    'AntimonyLanguage',
    'Antimony Language Server',
    serverOptions,
    clientOptions
  );
  // Start the client. This will also launch the server
  const clientDisposable = client.start();
  context.subscriptions.push(clientDisposable);
  return 1;
}

// getting python interpretor
function getPythonInterpreter(): string {
  const config = vscode.workspace.getConfiguration('vscode-antimony');
  return config.get('pythonInterpreter');
}

// verify python interpeter
async function verifyInterpreter(path: string) {
  try {
    const result = await utils.execPromise(`"${path}" -c "import sys; print(sys.version_info >= (3, 7))"`);
    if (result['stdout'].trim() === 'True') {
      return 0;
    }
    return 1;
  } catch (e) {
    return 2;
  }
}

// prompting reload window
function promptToReloadWindow(message: string) {
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

// open start page
async function openStartPage() {
  const openStartPage = vscode.workspace.getConfiguration('vscode-antimony').get('openStartPage');
  const startPageStr = `A -> B; k1*A
B -> C; k2*B
k1 = 1
k2 = 2
A = 10
B = 0
C = 0`;
  if (openStartPage) {
    const startPageDir = os.tmpdir();
    var startPageName = `startPage.ant`;
    var startPagePath = path.join(startPageDir, startPageName);
    fs.writeFile(startPagePath, startPageStr, (error) => {
      if (error) {
        console.error(error);
      } else {
        console.log('The file was saved to ' + startPagePath);
      }
    });
    // Create the temporary file and open it in the editor
    const startPageFile = vscode.workspace.openTextDocument(startPagePath).then((doc) => {
      vscode.window.showTextDocument(doc, { preview: false });
    });
  }
}

// Provides the CodeLens link to the usage guide if the file is empty.
class AntCodeLensProvider implements vscode.CodeLensProvider {
  async provideCodeLenses(document: vscode.TextDocument): Promise<vscode.CodeLens[]> {
    // Only provide CodeLens if file is antimony and is empty
    if (document.languageId === 'antimony' && !document.getText().trim()) {
      const topOfDocument = new vscode.Range(0, 0, 0, 0);
      // TODO: change the link
      let c: vscode.Command = {
        title: 'vscode-antimony Help Page',
        command: 'vscode.open',
        arguments: [vscode.Uri.parse('https://github.com/evilnose/vscode-antimony#usage')],
      };
      let codeLens = new vscode.CodeLens(topOfDocument, c);
      return [codeLens];
    }
    return [];
  }
}
