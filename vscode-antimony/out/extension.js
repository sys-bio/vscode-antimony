"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const vscode = require("vscode");
const utils = require("./utils/utils");
const path = require("path");
const node_1 = require("vscode-languageclient/node");
const annotationInput_1 = require("./annotationInput");
const SBMLEditor_1 = require("./SBMLEditor");
const AntimonyEditor_1 = require("./AntimonyEditor");
let client = null;
let pythonInterpreter = null;
let lastChangeInterp = 0;
let timestamp = new Date();
async function activate(context) {
    // start the language server
    await startLanguageServer(context);
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
    context.subscriptions.push(vscode.commands.registerCommand('antimony.createAnnotationDialog', (...args) => createAnnotationDialog(context, args)));
    // convertion
    context.subscriptions.push(vscode.commands.registerCommand('antimony.convertAntimonyToSBML', (...args) => convertAntimonyToSBML(context, args)));
    context.subscriptions.push(vscode.commands.registerCommand('antimony.convertSBMLToAntimony', (...args) => convertSBMLToAntimony(context, args)));
    // custom editor
    context.subscriptions.push(await SBMLEditor_1.SBMLEditorProvider.register(context, client));
    context.subscriptions.push(await AntimonyEditor_1.AntimonyEditorProvider.register(context, client));
    context.subscriptions.push(vscode.commands.registerCommand('antimony.startSBMLWebview', (...args) => startSBMLWebview(context, args)));
    context.subscriptions.push(vscode.commands.registerCommand('antimony.startAntimonyWebview', (...args) => startAntimonyWebview(context, args)));
    // language config for CodeLens
    const docSelector = {
        language: 'antimony',
        scheme: 'file',
    };
    let codeLensProviderDisposable = vscode.languages.registerCodeLensProvider(docSelector, new AntCodeLensProvider());
    context.subscriptions.push(codeLensProviderDisposable);
}
exports.activate = activate;
async function startSBMLWebview(context, args) {
    if (!client) {
        utils.pythonInterpreterError();
        return;
    }
    await client.onReady();
    await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");
    vscode.commands.executeCommand("vscode.openWith", vscode.window.activeTextEditor.document.uri, "antimony.sbmlEditor", 2);
}
async function startAntimonyWebview(context, args) {
    if (!client) {
        utils.pythonInterpreterError();
        return;
    }
    await client.onReady();
    await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");
    vscode.commands.executeCommand("vscode.openWith", vscode.window.activeTextEditor.document.uri, "antimony.antimonyEditor", 2);
}
async function saveSBMLWebview(context, args) {
}
async function convertAntimonyToSBML(context, args) {
    if (!client) {
        utils.pythonInterpreterError();
        return;
    }
    await client.onReady();
    await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");
    const options = {
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
            vscode.commands.executeCommand('antimony.antFiletoSBMLFile', vscode.window.activeTextEditor.document, fileUri[0].fsPath).then(async (result) => {
                await checkConversionResult(result, "SBML");
            });
        }
    });
}
async function convertSBMLToAntimony(context, args) {
    if (!client) {
        utils.pythonInterpreterError();
        return;
    }
    await client.onReady();
    await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");
    const options = {
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
            vscode.commands.executeCommand('antimony.sbmlFileToAntFile', vscode.window.activeTextEditor.document, folderUri[0].fsPath).then(async (result) => {
                await checkConversionResult(result, "Antimony");
            });
        }
    });
}
async function checkConversionResult(result, type) {
    if (result.error) {
        vscode.window.showErrorMessage(`Could not convert file to ${type}: ${result.error}`);
    }
    else {
        vscode.window.showInformationMessage(`${result.msg}`);
        const document = await vscode.workspace.openTextDocument(`${result.file}`);
        vscode.window.showTextDocument(document);
    }
}
async function createAnnotationDialog(context, args) {
    // wait till client is ready, or the Python server might not have started yet.
    // note: this is necessary for any command that might use the Python language server.
    if (!client) {
        utils.pythonInterpreterError();
        return;
    }
    await client.onReady();
    await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");
    // dialog for annotation
    const selection = vscode.window.activeTextEditor.selection;
    // get the selected text
    const doc = vscode.window.activeTextEditor.document;
    const selectedText = doc.getText(selection);
    // get the position for insert
    var line = selection.start.line;
    while (line < doc.lineCount - 1) {
        const text = doc.lineAt(line).text;
        if (text.localeCompare("end", undefined, { sensitivity: 'accent' }) == 0) {
            line -= 1;
            break;
        }
        line += 1;
    }
    const initialEntity = selectedText || 'entityName';
    let initialQuery;
    // get current file
    if (args.length == 2) {
        initialQuery = args[1];
    }
    else {
        initialQuery = selectedText;
    }
    const selectedItem = await (0, annotationInput_1.multiStepInput)(context, initialQuery);
    await insertAnnotation(selectedItem, initialEntity, line);
}
function deactivate() {
    if (!client) {
        return undefined;
    }
    // shut down the language client
    return client.stop();
}
exports.deactivate = deactivate;
// ****** helper functions ******
// starting language server
async function startLanguageServer(context) {
    pythonInterpreter = getPythonInterpreter();
    // verify the interpreter
    const error = await verifyInterpreter(pythonInterpreter);
    if (error !== 0) {
        let errMessage;
        if (error === 1) {
            errMessage = `Failed to launch language server: "${pythonInterpreter}" is not Python 3.7+`;
        }
        else {
            errMessage = `Failed to launch language server: Unable to run "${pythonInterpreter}"`;
        }
        const choice = await vscode.window.showErrorMessage(errMessage, 'Edit in settings');
        if (choice === 'Edit in settings') {
            await vscode.commands.executeCommand('workbench.action.openSettings', 'vscode-antimony.pythonInterpreter');
        }
        return;
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
    const pythonMain = context.asAbsolutePath(path.join('src', 'server', 'main.py'));
    const args = [pythonMain];
    // Add debug options here if needed
    const serverOptions = { command: pythonInterpreter, args };
    const clientOptions = {
        documentSelector: [
            { scheme: "file", language: "antimony" },
        ],
    };
    // Create the language client and start the client.
    client = new node_1.LanguageClient('AntimonyLanguage', 'Antimony Language Server', serverOptions, clientOptions);
    // Start the client. This will also launch the server
    const clientDisposable = client.start();
    context.subscriptions.push(clientDisposable);
}
// getting python interpretor
function getPythonInterpreter() {
    const config = vscode.workspace.getConfiguration('vscode-antimony');
    return config.get('pythonInterpreter');
}
// verify python interpeter
async function verifyInterpreter(path) {
    try {
        const result = await utils.execPromise(`"${path}" -c "import sys; print(sys.version_info >= (3, 7))"`);
        if (result['stdout'].trim() === 'True') {
            return 0;
        }
        return 1;
    }
    catch (e) {
        return 2;
    }
}
// Provides the CodeLens link to the usage guide if the file is empty.
class AntCodeLensProvider {
    async provideCodeLenses(document) {
        // Only provide CodeLens if file is antimony and is empty
        if (document.languageId === 'antimony' && !document.getText().trim()) {
            const topOfDocument = new vscode.Range(0, 0, 0, 0);
            // TODO: change the link
            let c = {
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
async function insertAnnotation(selectedItem, entityName, line) {
    const entity = selectedItem.entity;
    const id = entity['id'];
    const prefix = entity['prefix'];
    const snippetText = `\n\${1:${entityName}} identity "http://identifiers.org/${prefix}/${id}"`;
    const snippetStr = new vscode.SnippetString(snippetText);
    const doc = vscode.window.activeTextEditor.document;
    const pos = doc.lineAt(line).range.end;
    vscode.window.activeTextEditor.insertSnippet(snippetStr, pos);
}
//# sourceMappingURL=extension.js.map