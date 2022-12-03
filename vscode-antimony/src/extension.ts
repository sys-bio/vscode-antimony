import * as vscode from 'vscode';
import * as utils from './utils/utils';
import * as path from 'path';
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

export async function activate(context: vscode.ExtensionContext) {
	annotatedVariableIndicatorOn = vscode.workspace.getConfiguration('vscode-antimony').get('annotatedVariableIndicatorOn');
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
	
	// SBMLDiagram
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.convertAntimonyToDiagram',
			(...args: any[]) => {
				convertAntimonyToDiagram(context, args);
			}));

	// custom editor
	context.subscriptions.push(await SBMLEditorProvider.register(context, client));
	context.subscriptions.push(await AntimonyEditorProvider.register(context, client));
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.startSBMLWebview',
			(...args: any[]) => startSBMLWebview(context, args)));
	context.subscriptions.push(
		vscode.commands.registerCommand('antimony.startAntimonyWebview',
			(...args: any[]) => startAntimonyWebview(context, args)));

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
			console.log("Decorations are updated");
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

async function convertAntimonyToDiagram(context: vscode.ExtensionContext, args: any[]) {
	if (!client) {
		utils.pythonInterpreterError();
		return;
	}
	await client.onReady();

	await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");

	const doc = vscode.window.activeTextEditor.document;
	const uri = doc.uri.toString();

	let speciesStr;
	vscode.commands.executeCommand('antimony.getDiagramQuickpick', uri).then(async (result) => {
		speciesStr = result;
		let speciesList = speciesStr.species_list.split(' ');
		let selectedSpeciesList = await vscode.window.showQuickPick(speciesList, {canPickMany: true, placeHolder: 'select species to include in your diagram'});
		if (selectedSpeciesList && selectedSpeciesList.length === 0) {
			vscode.window.showErrorMessage('Please select at least one species!');
		} else {
			const options: vscode.OpenDialogOptions = {
				openLabel: "Select",
				canSelectFolders: true,
				canSelectFiles: false,
				canSelectMany: false,
				filters: {
					'Images': ['png']
				},
				title: "Select a location to save your SBML diagram"
			};
			vscode.window.showOpenDialog(options).then(fileUri => {
				if (fileUri && fileUri[0]) {
				 let diagram;
						vscode.commands.executeCommand('antimony.antFiletoDiagram', vscode.window.activeTextEditor.document, 
							fileUri[0].fsPath, selectedSpeciesList).then(async (result) => {
						 let error = await checkSBMLDiagramResult(result);
						 diagram = result;
						 if (!diagram.error) {
							 const panel = vscode.window.createWebviewPanel(
								 'antimony',
								 'SBMLDiagram',
								 vscode.ViewColumn.Two,
								 {
								   localResourceRoots: [vscode.Uri.file(path.dirname(diagram.file))]
								 }
							 );
							 const pngSrc = panel.webview.asWebviewUri(vscode.Uri.file(diagram.file));
							 panel.webview.html = getWebviewContent(pngSrc);
						 }
					 });
				}
			});
		}
	});
}

function getWebviewContent(uri: vscode.Uri) {
	return `<!DOCTYPE html>
  <html lang="en">
  <head>
	  <meta charset="UTF-8">
	  <meta name="viewport" content="width=device-width, initial-scale=1.0">
	  <title>SBMLDiagram</title>
  </head>
  <body>
	  <img src=${uri} width="300" />
  </body>
  </html>`;
  }

async function checkSBMLDiagramResult(result) {
	if (result.error) {
		vscode.window.showErrorMessage(`Could not convert file to diagram: ${result.error}`);
	} else {
		vscode.window.showInformationMessage(`${result.msg}`);
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
function promptToReloadWindow() {
	const action = 'Reload';
  
	vscode.window
	  .showInformationMessage(
		`Reload window in order for visual indication change in Antimony to take effect.`,
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

	promptToReloadWindow();
}

vscode.workspace.onDidChangeConfiguration(async (e) => {
	if (!e.affectsConfiguration('vscode-antimony.highlightColor')) {
		return;
	}
	promptToReloadWindow();
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
