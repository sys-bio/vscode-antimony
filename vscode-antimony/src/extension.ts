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
// import { recSingleStepInput } from './annotationRecommender';
import { annotationMultiStepInput } from './annotationInput';
import { rateLawSingleStepInput } from './rateLawInput';
import { SBMLEditorProvider } from './SBMLEditor';
import { AntimonyEditorProvider } from './AntimonyEditor';
import { modelSearchInput } from './modelBrowse';
import { ProgressLocation, TextDocument, window } from 'vscode';
import { ensureRuntime, reinstallRuntime } from './runtime';

let client: LanguageClient | null = null;
let pythonInterpreter: string | null = null;

// Starting the Python language server takes a beat: process spawn plus the
// antimony and libsbml native imports. Without an indicator the editor looks
// like it has simply ignored the file, and users retry or reload -- which
// makes it slower. A status bar item is the right weight here: visible if you
// look for it, silent if you do not.
let statusItem: vscode.StatusBarItem | null = null;
let resolveServerReady: (() => void) | null = null;
let escalateTimer: NodeJS.Timeout | null = null;

/**
 * Escalating startup indicator.
 *
 * Starting the server means spawning a Python process and importing native
 * libantimony and libsbml bindings. On a warm machine that is fast enough that
 * a notification would be noise; on a cold one it is long enough that silence
 * looks like the extension ignored the file.
 *
 * So: a status bar spinner immediately, plus the status bar progress slot. If
 * the server still is not ready after ESCALATE_MS, a notification toast opens
 * as well, because at that point the user deserves an unmissable answer to
 * "is this doing anything?". Fast starts never show the toast.
 */
const ESCALATE_MS = 1500;

function beginStartupIndicator(message: string) {
  const done = new Promise<void>((resolve) => { resolveServerReady = resolve; });

  showStatus(`$(loading~spin) ${message}`, 'Antimony is starting up');

  // Status bar progress slot, next to the notification bell.
  vscode.window.withProgress(
    { location: vscode.ProgressLocation.Window, title: message },
    () => done
  );

  escalateTimer = setTimeout(() => {
    if (!resolveServerReady) { return; }   // already finished
    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'Starting Antimony',
        cancellable: false,
      },
      async (progress) => {
        progress.report({ message: 'Loading the language server. This only takes a moment.' });
        await done;
      }
    );
  }, ESCALATE_MS);
}

/** Ends every startup indicator, once. Safe to call repeatedly. */
function serverStartupFinished() {
  if (escalateTimer) {
    clearTimeout(escalateTimer);
    escalateTimer = null;
  }
  resolveServerReady?.();
  resolveServerReady = null;
}

function showStatus(text: string, tooltip: string) {
  if (!statusItem) {
    statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  }
  statusItem.text = text;
  statusItem.tooltip = tooltip;
  statusItem.show();
}
let lastChangeInterp = 0;

// Decoration type for annotated variables
const annDecorationType = vscode.window.createTextEditorDecorationType({
  backgroundColor: vscode.workspace.getConfiguration('vscode-antimony').get('highlightColor'),
});

// User Setting Configuration for Switching Annotations On/Off
let annotatedVariableIndicatorOn: boolean | null = null;

let activeEditor = vscode.window.activeTextEditor;

// RoundTripping SBML to Antimony
let roundTripping: boolean | null = null;

const MODEL_EXTENSIONS = new Set(['.ant', '.xml']);

/** Records that the one-time post-install setup has already been attempted. */
const PREFETCH_KEY = 'antimony.runtimePrefetchAttempted';

/**
 * True for documents the extension actually operates on.
 *
 * The scheme check comes first on purpose. A git diff, a search preview, or an
 * output channel can carry an .xml path, and treating those as "the user
 * opened a model" would kick off a ~95 MB download for a read-only peek.
 */
function isModelDocument(doc: vscode.TextDocument | undefined): doc is vscode.TextDocument {
  if (!doc) {
    return false;
  }
  if (doc.uri.scheme !== 'file' && doc.uri.scheme !== 'untitled') {
    return false;
  }
  return MODEL_EXTENSIONS.has(path.extname(doc.uri.fsPath).toLowerCase());
}

/** Guards bootstrap() so the triggers below can fire freely. */
let bootstrapped = false;

// Activate extension
export async function activate(context: vscode.ExtensionContext) {
  // Registered unconditionally. These are the only two commands reachable
  // without a model file open, so they have to survive the case where the rest
  // of activation is deferred.
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.openStartPage', (...args: any[]) => openStartPage()));

  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.reinstallRuntime', (...args: any[]) => reinstallRuntime(context)));

  // Trigger 2: the user opens or switches to a model file. Both events are
  // needed -- onDidOpenTextDocument fires for a newly opened file,
  // onDidChangeActiveTextEditor for switching to a tab that was already open
  // in the background. Neither covers the other.
  //
  // These are registered before the already-open check so that a bootstrap
  // that fails (no network, cancelled download) can be retried simply by
  // opening another model file.
  const trigger = (doc: vscode.TextDocument | undefined) => {
    if (isModelDocument(doc)) {
      void bootstrap(context, doc);
    }
  };

  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument(doc => trigger(doc)),
    vscode.window.onDidChangeActiveTextEditor(editor => trigger(editor?.document))
  );

  // A model file may already be open: window restore, or the user opened one
  // before activation finished. Prefer the focused one, since the SBML
  // handling at the end of bootstrap acts on the document it is given.
  const active = vscode.window.activeTextEditor?.document;
  const alreadyOpen = isModelDocument(active)
    ? active
    : vscode.workspace.textDocuments.find(isModelDocument);
  if (alreadyOpen) {
    await bootstrap(context, alreadyOpen);
    return;
  }

  // Trigger 1: right after the extension is installed, so the first model file
  // the user opens does not stall behind a download. ensureRuntime is a no-op
  // once the runtime is present, so this costs nothing on later launches.
  //
  // The flag is written before the call, not after. If setup fails or the user
  // cancels, re-prompting on every window launch is worse than waiting for
  // them to open a file -- the trigger above still installs on demand.
  if (!context.globalState.get<boolean>(PREFETCH_KEY)) {
    await context.globalState.update(PREFETCH_KEY, true);
    void ensureRuntime(context);
  }
}

/**
 * Everything that needs a working Python: the runtime, the language server,
 * and the editor features built on top of them. Runs at most once per window,
 * and only once a model file is actually in play.
 */
async function bootstrap(context: vscode.ExtensionContext, doc: vscode.TextDocument) {
  if (bootstrapped) {
    return;
  }
  bootstrapped = true;

  const fileExtension = path.extname(doc.uri.fsPath).toLowerCase();

  // Resolve (and on first run, download) the bundled Python runtime. Returns
  // null if the user cancelled or setup failed, in which case bail out rather
  // than starting a language server against an interpreter that isn't there.
  context.subscriptions.push({
    dispose: () => { serverStartupFinished(); statusItem?.dispose(); }
  });

  // Started before ensureRuntime so the indicator covers the whole sequence,
  // including the runtime check and any migration, not just the server spawn.
  beginStartupIndicator('Starting Antimony language server');

  const interpreter = await ensureRuntime(context);
  if (!interpreter) {
    bootstrapped = false;   // allow a retry when another model file is opened
    serverStartupFinished();
    statusItem?.dispose();
    statusItem = null;
    return;
  }

  roundTripping = vscode.workspace.getConfiguration('vscode-antimony').get('openSBMLAsAntimony');

  // start the language server
  if (await startLanguageServer(context, interpreter) === 0) {
    bootstrapped = false;   // allow a retry when another model file is opened
    serverStartupFinished();
    statusItem?.dispose();
    statusItem = null;
    return;
  }

  // Flip to ready once the server has finished initialising. Not awaited: the
  // rest of activation does not depend on it, and blocking here would delay
  // command registration for no benefit.
  client?.onReady().then(
    () => {
      serverStartupFinished();
      showStatus('$(check) Antimony', 'Antimony language server is ready');
    },
    () => {
      serverStartupFinished();
      showStatus('$(warning) Antimony', 'The Antimony language server failed to start');
    }
  );

  // Safety net: if onReady never settles, the window progress would spin
  // forever, which looks worse than no indicator at all.
  setTimeout(() => {
    if (resolveServerReady) {
      serverStartupFinished();
      showStatus('$(warning) Antimony', 'The Antimony language server is taking longer than expected');
    }
  }, 60_000);

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
      const next = await ensureRuntime(context);
      if (next) {
        await startLanguageServer(context, next);
      }
    }, 3000);

  });

  // create annotations
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.createAnnotationDialog', (...args: any[]) => createAnnotationDialog(context, args)));

  // create annotations
  // context.subscriptions.push(
  // 	vscode.commands.registerCommand('antimony.recommendAnnotationDialog', (...args: any[]) => recommendAnnotationDialog(context, args)));

  // insert rate law
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.insertRateLawDialog', (...args: any[]) => insertRateLawDialog(context, args)));

  // switch visual annotations on
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.switchIndicationOn', (...args: any[]) => switchIndicationOn(context)));

  // switch visual annotations off
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.switchIndicationOff', (...args: any[]) => switchIndicationOff(context)));

  // convertion
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.convertAntimonyToSBML', (...args: any[]) => convertAntimonyToSBML(context, args)));
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.convertSBMLToAntimony', (...args: any[]) => convertSBMLToAntimony(context, args)));
  
  // custom editor
  context.subscriptions.push(await SBMLEditorProvider.register(context, client));
  context.subscriptions.push(await AntimonyEditorProvider.register(context, client));
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.startSBMLWebview', (...args: any[]) => startSBMLWebview(context, args)));
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.startAntimonyWebview', (...args: any[]) => startAntimonyWebview(context, args)));
  
  // browse biomodels
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.browseBiomodels', (...args: any[]) => browseBioModels(context, args)));
  
  // navigate to annotation
  context.subscriptions.push(
    vscode.commands.registerCommand('antimony.navigateAnnotation', (...args: any[]) => navigateAnnotation(context, args)));

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

  annotatedVariableIndicatorOn = vscode.workspace.getConfiguration('vscode-antimony').get('annotatedVariableIndicatorOn');

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
    // Focusing the Output panel should not replace the tracked editor, or the
    // decoration pass starts operating on the log view itself.
    if (editor && editor.document.uri.scheme !== 'file') {
      return;
    }
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

  if (path.extname(doc.fileName) === '.xml' && roundTripping) {
    triggerSBMLEditor(doc, sbmlFileNameToPath);
  }
  if (fileExtension == '.xml') {
    vscode.commands.executeCommand('antimony.checkSbml', doc.uri.path).then((result: any) => {
      if (result === true) {
        vscode.window.showWarningMessage("This SBML file contains notes, model history, algebraic rules and unsupported packages. Proceed conversion to Antimony with caution.")
      }
    });
  }
}

vscode.window.onDidChangeActiveTextEditor(() => {
  const activeTextEditor = vscode.window.activeTextEditor;
  if (activeTextEditor) {
    const doc = activeTextEditor.document;
    // Same reason as updateDecorations: skip anything that is not a real file.
    if (doc.uri.scheme !== 'file') {
      return;
    }
    const uri = doc.uri.toString();
    const fileExtension = path.extname(uri);
    if (fileExtension == '.xml') {
      vscode.commands.executeCommand('antimony.checkSbml', doc.uri.path).then((result: any) => {
        if (result === true) {
          vscode.window.showWarningMessage("This SBML file contains notes, model history, algebraic rules, and/or unsupported packages. Proceed conversion to Antimony with caution.");
        }
      });
    }
  }
});

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

  vscode.window.showWarningMessage("Preview SBML only shows the SBML model as text, thus no Antimony features will be available.");

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

  vscode.window.showWarningMessage("Preview Antimony only shows the Antimony model as text, thus no Antimony features will be available.");

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

  if (selectedText === "") {
    vscode.window.showErrorMessage("Please select a variable to annotate.");
    return;
  }
  
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

  const selectedItem = await annotationMultiStepInput(context, initialQuery);
  await insertAnnotation(selectedItem, initialEntity, line);
}

async function navigateAnnotation(context: vscode.ExtensionContext, args: any[]) {
  await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");
  
  // dialog for annotation
  const selection = vscode.window.activeTextEditor.selection;
  
  // get the selected text
  const doc = vscode.window.activeTextEditor.document;
  const uri = doc.uri.toString();
  const text = doc.getText();
  const ind = text.indexOf("http");

  if (ind !== -1) {
    const position = doc.positionAt(ind);
    vscode.window.activeTextEditor.selection = new vscode.Selection(position, position);
    vscode.window.activeTextEditor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenter);
  } else {
    vscode.window.showWarningMessage("No annotations found.");
  }
}

// async function recommendAnnotationDialog(context: vscode.ExtensionContext, args: any[]) {
// 	// wait till client is ready, or the Python server might not have started yet.
// 	// note: this is necessary for any command that might use the Python language server.
// 	if (!client) {
// 		utils.pythonInterpreterError();
// 		return;
// 	}
// 	await client.onReady();
// 	await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup")
// 	// dialog for annotation
// 	const selection = vscode.window.activeTextEditor.selection
// 	// get the selected text
// 	const doc = vscode.window.activeTextEditor.document
// 	const uri = doc.uri.toString();
// 	const selectedText = doc.getText(selection);
// 	// get the position for insert
// 	let line = selection.start.line
// 	while (line <= doc.lineCount - 1) {
// 		const text = doc.lineAt(line).text
// 		if (text.localeCompare("end", undefined, { sensitivity: 'accent' }) == 0) {
// 			line -= 1;
// 			break;
// 		}
// 		line += 1;
// 	}
// 	const positionAt = selection.anchor;
// 	const lineStr = positionAt.line.toString();
// 	const charStr = positionAt.character.toString();
// 	const initialEntity = selectedText || 'entityName';
// 	let initialQuery;
// 	// get current file
// 	if (args.length == 2) {
// 		initialQuery = args[1];
// 	} else {
// 		initialQuery = selectedText;
// 	}

// 	await new Promise<void>((resolve, reject) => {
// 		const selectedItem = singleStepInputRec(context, line, lineStr, charStr, uri, initialQuery, initialEntity); 
// 		resolve()
//     });
// }

// async function getResult(result) {
// 	return result.symbol;
// }

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
  
  vscode.window.showInformationMessage(
    message,
    {modal: true}, 
    action)
    .then(selectedAction => {
      if (selectedAction === action) {
      vscode.commands.executeCommand('workbench.action.reloadWindow');
      }
    });
}

export async function switchIndicationOff(context: vscode.ExtensionContext) {
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

export async function switchIndicationOn(context: vscode.ExtensionContext) {
  // wait till client is ready, or the Python server might not have started yet.
  // note: this is necessary for any command that might use the Python language server.
  if (!client) {
    utils.pythonInterpreterError();
    return;
  }
  await client.onReady();

  await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");

  annotatedVariableIndicatorOn = true;
  await vscode.workspace.getConfiguration('vscode-antimony').update('annotatedVariableIndicatorOn', true, true);

  setTimeout(() => {
    vscode.commands.executeCommand('workbench.action.reloadWindow');
  }, 2000);
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
  setTimeout(() => {
    vscode.commands.executeCommand('workbench.action.reloadWindow');
  }, 2000);
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

/**
 * Open Start Page Function
 */
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

/**
 * Visual Indication Functions
 */

// change the annotation decoration of non-annotated variables
async function updateDecorations() {
  let annVars: string;
  let regexFromAnnVarsHelp: RegExp;
  let regexFromAnnVars: RegExp;
  let config =  vscode.workspace.getConfiguration('vscode-antimony').get('annotatedVariableIndicatorOn');

  if (!activeEditor) {
    return;
  }

  const doc = activeEditor.document;

  // The Output panel, diff views, and Git previews are all TextEditors with
  // non-file schemes (output:, git:, untitled:). Their URIs are not paths, so
  // sending one to the server produces
  //   FileNotFoundError: 'extension-output-stevem.vscode-antimony-#2-...'
  // once per keystroke while that panel has focus. Only real files on disk are
  // meaningful to the language server.
  if (doc.uri.scheme !== 'file' || doc.languageId !== 'antimony') {
    return;
  }

  const uri = doc.uri.toString();

  // wait till client is ready, or the Python server might not have started yet.
  // note: this is necessary for any command that might use the Python language server.
  if (!client) {
    utils.pythonInterpreterError();
    return;
  }
  await client.onReady();

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

// ****** helper functions ******

// starting language server
async function startLanguageServer(context: vscode.ExtensionContext, interpreter: string) {
  pythonInterpreter = interpreter;

  // Verify the interpreter actually runs. With the bundled runtime this should
  // never fail, so if it does the install is damaged rather than misconfigured
  // and the useful offer is a reinstall, not a settings page.
  const error = await verifyInterpreter(pythonInterpreter);
  if (error !== 0) {
    const usingOverride = !!vscode.workspace
      .getConfiguration('vscode-antimony')
      .get<string>('pythonInterpreter', '')
      .trim();

    if (usingOverride) {
      const choice = await vscode.window.showErrorMessage(
        `Antimony could not start its language server using the interpreter you configured ("${pythonInterpreter}"). ` +
        `It must be Python 3.7 or later with the extension's dependencies installed.`,
        'Edit in settings',
        'Use bundled Python'
      );
      if (choice === 'Edit in settings') {
        await vscode.commands.executeCommand('workbench.action.openSettings', 'vscode-antimony.pythonInterpreter');
      } else if (choice === 'Use bundled Python') {
        await vscode.workspace
          .getConfiguration('vscode-antimony')
          .update('pythonInterpreter', '', true);
        await reinstallRuntime(context);
      }
    } else {
      const choice = await vscode.window.showErrorMessage(
        'Antimony could not start its language server. Its components may be damaged or incomplete.',
        'Reinstall components'
      );
      if (choice === 'Reinstall components') {
        await reinstallRuntime(context);
      }
    }
    return 0;
  }

  // create language client and launch server
  const pythonMain = context.asAbsolutePath(
    path.join('src', 'server', 'main.py')
  );
  // Passed as an array, never through a shell, so paths containing spaces
  // (C:\\Users\\Jane Smith) need no quoting.
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