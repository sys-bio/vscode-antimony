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
import { singleStepInputRec } from './annotationRecommender';
import { annotationMultiStepInput } from './annotationInput';
import { rateLawSingleStepInput } from './rateLawInput';
import { SBMLEditorProvider } from './SBMLEditor';
import { AntimonyEditorProvider } from './AntimonyEditor';
import { modelSearchInput } from './modelBrowse';
import { ProgressLocation, TextDocument, window } from 'vscode';
import { exec } from 'child_process';

let client: LanguageClient | null = null;
let pythonInterpreter: string | null = null;
let lastChangeInterp = 0;

let timestamp = new Date();

let highlightColor = "indigo";

// Decoration type for annotated variables
const annDecorationType = vscode.window.createTextEditorDecorationType({
	backgroundColor: vscode.workspace.getConfiguration('vscode-antimony').get('highlightColor'),
});

// User Setting Configuration for Switching Annotations On/Off
let annotatedVariableIndicatorOn: boolean | null = null;

let activeEditor = vscode.window.activeTextEditor;

// RoundTripping SBML to Antimony
let roundTripping: boolean | null = null;

// change the annotation decoration of non-annotated variables
function updateDecorations() {
	let annVars: string;
	let regexFromAnnVarsHelp: RegExp;
	let regexFromAnnVars: RegExp;
	let config =  vscode.workspace.getConfiguration('vscode-antimony').get('annotatedVariableIndicatorOn');

	const doc = activeEditor.document;
	const uri = doc.uri.toString();

	if (config === true) {
		vscode.commands.executeCommand('antimony.getAnnotation', uri).then(async (result: string) => {

			annVars = result;
			if (annVars == "" || annVars == null || annVars == " "){
				vscode.workspace.getConfiguration('vscode-antimony').update('annotatedVariableIndicatorOn', false, true);
				annDecorationType.dispose();
				return;
			}
			regexFromAnnVarsHelp = new RegExp(annVars,'g');
			regexFromAnnVars = new RegExp('\\b(' + regexFromAnnVarsHelp.source + ')\\b', 'g');

			if (!activeEditor) {
				return;
			}

			const text = activeEditor.document.getText();
			const annotated: vscode.DecorationOptions[] = [];
			let match;
			while ((match = regexFromAnnVars.exec(text))) {
				const startPos = activeEditor.document.positionAt(match.index);
				const endPos = activeEditor.document.positionAt(match.index + match[0].length);
				const decoration = { range: new vscode.Range(startPos, endPos) };
					annotated.push(decoration);
			}
			activeEditor.setDecorations(annDecorationType, annotated);
		});
	}
}

var current_path_to_tsscript = path.join(__dirname, '..', 'src', 'runshell.ts');
// setup virtual environment
async function createVirtualEnv(context: vscode.ExtensionContext) {
	await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");
	// asking permissions
	if ((os.platform().toString() == 'darwin') && fs.existsSync(path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python"))) {
		if (vscode.workspace.getConfiguration('vscode-antimony').get('pythonInterpreter') !== path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python")) {
			vscode.workspace.getConfiguration('vscode-antimony').update('pythonInterpreter', path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python"), true);
			vscode.window.showInformationMessage('Virtual environment exists, it is activated now.')
		}
	} else if ((os.platform().toString() == 'win32' || os.platform().toString() == 'win64') && fs.existsSync(path.normalize(os.homedir() + "/vscode_antimony_virtual_env"))) {
		if (vscode.workspace.getConfiguration('vscode-antimony').get('pythonInterpreter') !== path.normalize(os.homedir() + "/vscode_antimony_virtual_env/Scripts/python")) {
			vscode.workspace.getConfiguration('vscode-antimony').update('pythonInterpreter', path.normalize(os.homedir() + "/vscode_antimony_virtual_env/Scripts/python"), true);
			vscode.window.showInformationMessage('Virtual environment exists, it is activated now.')
		}
	} else if (os.platform().toString() == 'linux' && fs.existsSync(path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python3.10"))) {
		if (vscode.workspace.getConfiguration('vscode-antimony').get('pythonInterpreter') !== path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python3.10")) {
			vscode.workspace.getConfiguration('vscode-antimony').update('pythonInterpreter', path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python3.10"), true);
			vscode.window.showInformationMessage('Virtual environment exists, it is activated now.')
		}
	} else {
		if (os.platform().toString() == 'linux') {
			vscode.window.showInformationMessage('[IMPORTANT: Linux users will have to install python3.10, venv python3.10 package, pip, and NodeJS.] To install dependencies so the extension works properly, allow installation of virtual environment', ...['Yes', 'No'])
			.then(async selection => {
				// installing virtual env
				if (selection === 'Yes') {
					fixVirtualEnv();
				} else if (selection === 'No') {
					vscode.window.showInformationMessage('The default python interpreter will be used.')
				}
			});
		} else if (os.platform().toString() == 'win32' || os.platform().toString() == 'win64'){
			vscode.window.showInformationMessage('[IMPORTANT: Windows users MUST install python3.10 (must be version 3.10), and NodeJS.] To install dependencies so the extension works properly, allow installation of virtual environment', ...['Yes', 'No'])
			.then(async selection => {
				// installing virtual env
				if (selection === 'Yes') {
					fixVirtualEnv();
				} else if (selection === 'No') {
					vscode.window.showInformationMessage('The default python interpreter will be used.')
				}
			});
		} else if (os.platform().toString() == 'darwin') {
			vscode.window.showInformationMessage('[IMPORTANT: Mac users MUST install python3.9 (must be version 3.9), and NodeJS.] To install dependencies so the extension works properly, allow installation of virtual environment', ...['Yes', 'No'])
			.then(async selection => {
				// installing virtual env
				if (selection === 'Yes') {
					fixVirtualEnv();
				} else if (selection === 'No') {
					vscode.window.showInformationMessage('The default python interpreter will be used.')
				}
			});
		}
	}
}

async function progressBar(filePath: string) {
    window.withProgress({            
        location: ProgressLocation.Notification,
        title: "Running virtual environment installation. Will take a few minutes, do not close VSCode",
        cancellable: true
    }, ( progress, token ) => {
        return new Promise<void>(resolve => {
            exec(`${filePath}`, (error, stdout, stderr) => {
				if (error) {
					vscode.window.showInformationMessage('Installation Error. Try again. Error Message: "' + error)
					throw error;
				} else {
					if (os.platform().toString() == 'darwin') {
						vscode.workspace.getConfiguration('vscode-antimony').update('pythonInterpreter', path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python"), true);
					} else if (os.platform().toString() == 'win32' || os.platform().toString() == 'win64') {
						vscode.workspace.getConfiguration('vscode-antimony').update('pythonInterpreter', path.normalize(os.homedir() + "/vscode_antimony_virtual_env/Scripts/python"), true);
					} else if (os.platform().toString() == 'linux') {
						vscode.workspace.getConfiguration('vscode-antimony').update('pythonInterpreter', path.normalize(os.homedir() + "/vscode_antimony_virtual_env/bin/python3.10"), true);
					}
		
					const action = 'Reload';
		
					vscode.window
					.showInformationMessage(
						`Installation finished. Reload to activate. Right click in the editor after reload to view features.`,
						action
					)
					.then(selectedAction => {
						if (selectedAction === action) {
							vscode.commands.executeCommand('workbench.action.reloadWindow');
						}
					});
				}
                resolve();
            });
        });
    });
}

// setup virtual environment
async function fixVirtualEnv() {
	var current_path_to_tsscript = path.join(__dirname, '..', 'src', 'server', 'runshell.js');
	// shell.exec('npx ts-node ' + current_path_to_tsscript, (err, stdout, stderr) => {
	// });
	progressBar('node ' + current_path_to_tsscript)
}

async function triggerSBMLEditor(event: TextDocument, sbmlFileNameToPath: Map<any, any>) {
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

export async function activate(context: vscode.ExtensionContext) {
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.openStartPage',
			(...args: any[]) => openStartPage()));
	annotatedVariableIndicatorOn = vscode.workspace.getConfiguration('vscode-antimony').get('annotatedVariableIndicatorOn');
	await createVirtualEnv(context);

	roundTripping = vscode.workspace.getConfiguration('vscode-antimony').get('openSBMLAsAntimony');

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
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.createAnnotationDialog',
			(...args: any[]) => createAnnotationDialog(context, args)));

	// create annotations
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.recommendAnnotationDialog',
			(...args: any[]) => recommendAnnotationDialog(context, args)));

	// insert rate law
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.insertRateLawDialog',
			(...args: any[]) => insertRateLawDialog(context, args)));

	// switch visual annotations on
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.switchIndicationOn',
			(...args: any[]) => switchIndicationOn(context, args)));

	// switch visual annotations off
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.switchIndicationOff',
			(...args: any[]) => switchIndicationOff(context, args)));

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

	// fix virtual env
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.fixVirtualEnv',
			(...args: any[]) => fixVirtualEnv()));

	// export as python
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.exportAsPython',
			(...args: any[]) => exportAsPython(context, args)));

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

	// timer for non annotated variable visual indicator
	let timeout: NodeJS.Timer | undefined = undefined;

	// update the decoration once in a certain time (throttle)
	function triggerUpdateDecorations(throttle = false) {
		if (timeout) {
			clearTimeout(timeout);
			timeout = undefined;
		}
		if (throttle) {
			timeout = setTimeout(updateDecorations, 500);
		} else {
			updateDecorations();
		}
	}

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

	const sbmlFileNameToPath = new Map();

	// when user opens XML
	if (roundTripping) {
		vscode.workspace.onDidOpenTextDocument(async event => {
			triggerSBMLEditor(event, sbmlFileNameToPath);
		});
	
		vscode.workspace.onDidSaveTextDocument((savedDoc) => {
			const fileName = path.basename(savedDoc.fileName, '.git');
			const pathName = path.dirname(savedDoc.fileName);
			const fullPath = path.join(pathName, fileName);
			const pattern = /^(.+?).ant/;
			if (pattern.test(fileName) && pathName === os.tmpdir()) {
				vscode.workspace.openTextDocument(fullPath).then((doc) => {
					vscode.commands.executeCommand('antimony.antStrToSBMLStr', doc.getText())
					.then(async (result: any) => {
						if (result.error) {
							vscode.window.showErrorMessage(`Error while converting: ${result.error}`);
						} else {
							const match = pattern.exec(fileName)[1];
							const sbmlFilePath = path.join(sbmlFileNameToPath[fileName], match + '.xml');
							fs.writeFile(sbmlFilePath, result.sbml_str, (error) => {
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

async function createAnnotationDialog(context: vscode.ExtensionContext, args: any[]) {
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
	const uri = doc.uri.toString();
	const selectedText = doc.getText(selection);
  
	// get the position for insert
	let line = selection.start.line;

	while (line <= doc.lineCount - 1) {
		const text = doc.lineAt(line).text;
		if (text.localeCompare("end", undefined, { sensitivity: 'accent' }) === 0) {
			line -= 1;
			break;
		}
		line += 1;
	}
  
	const positionAt = selection.anchor;
	const lineStr = positionAt.line.toString();
	const charStr = positionAt.character.toString();
	const initialEntity = selectedText || 'entityName';
	let initialQuery;
	// get current file
	if (args.length === 2) {
		initialQuery = args[1];
	} else {
		initialQuery = selectedText;
	}
	vscode.commands.executeCommand('antimony.sendType', lineStr, charStr, uri).then(async (result) => {
		const selectedType = await getResult(result);
		const selectedItem = await annotationMultiStepInput(context, initialQuery, selectedType);
		await insertAnnotation(selectedItem, initialEntity, line);
	});
}

async function recommendAnnotationDialog(context: vscode.ExtensionContext, args: any[]) {
	// wait till client is ready, or the Python server might not have started yet.
	// note: this is necessary for any command that might use the Python language server.
	if (!client) {
		utils.pythonInterpreterError();
		return;
	}
	await client.onReady();
	await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup")
	// dialog for annotation
	const selection = vscode.window.activeTextEditor.selection
	// get the selected text
	const doc = vscode.window.activeTextEditor.document
	const uri = doc.uri.toString();
	const selectedText = doc.getText(selection);
	// get the position for insert
	let line = selection.start.line
	while (line <= doc.lineCount - 1) {
		const text = doc.lineAt(line).text
		if (text.localeCompare("end", undefined, { sensitivity: 'accent' }) == 0) {
			line -= 1;
			break;
		}
		line += 1;
	}
	const positionAt = selection.anchor;
	const lineStr = positionAt.line.toString();
	const charStr = positionAt.character.toString();
	const initialEntity = selectedText || 'entityName';
	let initialQuery;
	// get current file
	if (args.length == 2) {
		initialQuery = args[1];
	} else {
		initialQuery = selectedText;
	}

	await new Promise<void>((resolve, reject) => {
		const selectedItem = singleStepInputRec(context, line, lineStr, charStr, uri, initialQuery, initialEntity); 
		resolve()
    });
}

async function getResult(result) {
	return result.symbol;
}

export function deactivate(): Thenable<void> | undefined {
	if (!client) {
		return undefined;
	}
	// shut down the language client
	return client.stop();
}
/** Prompts user to reload editor window in order for configuration change to take effect. */
function promptToReloadWindow(message: string) {
	const action = 'Reload';
  
	vscode.window
	  .showInformationMessage(
		message,
		action
	  )
	  .then(selectedAction => {
		  if (selectedAction === action) {
		    vscode.commands.executeCommand('workbench.action.reloadWindow');
		  }
	  });
}

async function switchIndicationOff(context: vscode.ExtensionContext, args: any[]) {
	// wait till client is ready, or the Python server might not have started yet.
	// note: this is necessary for any command that might use the Python language server.
	if (!client) {
		utils.pythonInterpreterError();
		return;
	}
	await client.onReady();

	await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");

	annDecorationType.dispose();
	
	annotatedVariableIndicatorOn = false;
	vscode.workspace.getConfiguration('vscode-antimony').update('annotatedVariableIndicatorOn', false, true);
}

async function switchIndicationOn(context: vscode.ExtensionContext, args: any[]) {
	// wait till client is ready, or the Python server might not have started yet.
	// note: this is necessary for any command that might use the Python language server.
	if (!client) {
		utils.pythonInterpreterError();
		return;
	}
	await client.onReady();

	await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");

	annotatedVariableIndicatorOn = true;
	vscode.workspace.getConfiguration('vscode-antimony').update('annotatedVariableIndicatorOn', true, true);

	promptToReloadWindow(`Reload window for visual indication change in Antimony to take effect.`);
}

vscode.workspace.onDidChangeConfiguration(async (e) => {
	if (!e.affectsConfiguration('vscode-antimony.highlightColor')) {
		return;
	}
	promptToReloadWindow(`Reload window for visual indication change in Antimony to take effect.`);
});

vscode.workspace.onDidChangeConfiguration(async (e) => {
	if (!e.affectsConfiguration('vscode-antimony.openSBMLAsAntimony')) {
		return;
	}
	promptToReloadWindow(`Reload window for Open SBML As Antimony change to take effect.`);
});

// insert rate law
async function insertRateLawDialog(context: vscode.ExtensionContext, args: any[]) {
	// wait till client is ready, or the Python server might not have started yet.
	// note: this is necessary for any command that might use the Python language server.
	if (!client) {
		utils.pythonInterpreterError();
		return;
	}
	await client.onReady();
	await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup")
	
	// Get the current focused document
	const doc = vscode.window.activeTextEditor.document

	// Obtain line number position of cursor right click
	const selectionCol = vscode.window.activeTextEditor.selection.active
	const lineNum = doc.lineAt(selectionCol).lineNumber;

	// Obtain text of the line number position
	const selectedLine = doc.lineAt(selectionCol);
	const selectedText = selectedLine.text;

	await new Promise<void>((resolve, reject) => {
		rateLawSingleStepInput(context, lineNum, selectedText); 
		resolve()
    });
}

// search for biomodels
async function browseBioModels(context: vscode.ExtensionContext, args: any[]) {
	// wait till client is ready, or the Python server might not have started yet.
	// note: this is necessary for any command that might use the Python language server.
	if (!client) {
		utils.pythonInterpreterError();
		return;
	}
	await client.onReady();
	await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");
	
	// not await null, change it after adding a function to parse search input
	await new Promise<void>((resolve, reject) => {
		modelSearchInput(context); 
		resolve()
	});
}

function getPythonString(model: string) {
	let pythonString;
	pythonString = `
#%%
import tellurium as te

#%%
r = te.loada(\'\'\'${model}\'\'\')

#%%
# implement and simulate your model here
	`
	return pythonString;
}

// Export Antimony as Python
async function exportAsPython(context: vscode.ExtensionContext, args: any[]) {
	if (!client) {
		utils.pythonInterpreterError();
		return;
	}
	await client.onReady();
	const antimonyConfig = vscode.workspace.getConfiguration('vscode-antimony');

	const promptPythonInterpreter = antimonyConfig.get('promptChangingPython');
	if (promptPythonInterpreter) {
		vscode.window.showInformationMessage("Do you want to change default python interpreter to vscode-antimony one?", ...['Yes', 'No', 'Don\'t show again'])
		.then(async selection => {
			if (selection === "Yes") {
				const antimonyInterpreter = getPythonInterpreter();
				vscode.workspace.getConfiguration('python').update('defaultInterpreterPath', antimonyInterpreter);
				antimonyConfig.update('promptChangingPython', false);
			} else if (selection === 'Don\'t show again') {
				antimonyConfig.update('promptChangingPython', false);
			}
		})
	}

	await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");

	const options: vscode.OpenDialogOptions = {
		openLabel: "Select",
		canSelectFolders: true,
		canSelectFiles: false,
		canSelectMany: false,
		filters: {
			'Python': ['py']
		},
		title: "Select a location to save your Python biomodel file"
	};
   	vscode.window.showOpenDialog(options).then(fileUri => {
	   	if (fileUri && fileUri[0]) {
			let pythonFileName: string = path.basename(vscode.window.activeTextEditor.document.fileName, '.ant') + '.py';
			let outputDir: string = fileUri[0].fsPath;
			let fullPathName: string = path.join(outputDir, pythonFileName);
			let antString: string = vscode.window.activeTextEditor.document.getText();
			let pythonString: string = getPythonString(antString);
			fs.writeFile(fullPathName, pythonString, (error) => {
				if (error) {
					console.error(error);
				} else {
					console.log('The python model was saved to ' + fullPathName);
				}
			});
	   	}
	});
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

async function insertAnnotation(selectedItem, entityName, line) {
	const entity = selectedItem.entity;
	const id = entity['id'];
	const prefix = entity['prefix'];
	let snippetText;
	if (prefix === 'rhea') {
		snippetText = `\n\${1:${entityName}} identity "https://www.rhea-db.org/rhea/${id}"`;
	} else if (prefix === 'ontology') {
		snippetText = `\n\${1:${entityName}} identity "${entity['iri']}"`;
	} else {
		snippetText = `\n\${1:${entityName}} identity "http://identifiers.org/${prefix}/${id}"`;
	}
	const snippetStr = new vscode.SnippetString(snippetText);
	const doc = vscode.window.activeTextEditor.document;
	const pos = doc.lineAt(line).range.end;
	vscode.window.activeTextEditor.insertSnippet(snippetStr, pos);
}
