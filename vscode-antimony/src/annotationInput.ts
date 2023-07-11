/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *  Modified by Gary Geng and Steve Ma for the Antimony VSCode extension project.
 *--------------------------------------------------------------------------------------------*/

import { QuickPickItem, window, Disposable, QuickInputButton, QuickInput, ExtensionContext, QuickInputButtons, commands, QuickPick } from 'vscode';
import { sleep } from './utils/utils';
import { ProgressLocation } from 'vscode'
import * as vscode from 'vscode';
import {
  LanguageClient
} from 'vscode-languageclient/node';
import * as utils from './utils/utils';

let client: LanguageClient | null = null;

/**
 * A multi-step input using window.createQuickPick() and window.createInputBox().
 *
 * This first part uses the helper class `MultiStepInput` that wraps the API for the multi-step case.
 */
export async function annotationMultiStepInput(context: ExtensionContext, initialEntity: string = null) {
    var databases;
    databases = [
        { label: 'ChEBI', id: 'chebi', detail: 'Commonly Used For: Species'},
        { label: 'UniProt', id: 'uniprot', detail: 'Commonly Used For: Species'},
        { label: 'RHEA', id: 'rhea', detail: 'Commonly Used For: Reactions'},
        { label: 'Gene Ontology', id: 'gontology', detail: 'Commonly Used For: Compartments, Reactions'},
        { label: 'Cell Type Ontology', id: 'contology', detail: 'Commonly Used For: Compartments'},
        { label: 'Protein Ontology', id: 'pontology', detail: 'Commonly Used For: Species'},
        { label: 'Ontology for Biomedical Investigations', id: 'bontology', detail: 'Commonly Used For: Compartments'},
        { label: 'Foundational Model of Anatomy', id: 'fontology', detail: 'Commonly Used For: Compartments'},
        { label: 'Mouse Adult Gross Anatomy', id: 'montology', detail: 'Commonly Used For: Compartments'}];

    interface State {
        title: string;
        step: number;
        totalSteps: number;
        database: QuickPickItem;
        entity: QuickPickItem;
        initialEntity: string;
    }

    async function collectInputs() {
        const state = {initialEntity} as Partial<State>;
        await MultiStepInput.run(input => pickDatabase(input, state));
        return state as State;
    }

    const title = 'Create Annotation';

    async function pickDatabase(input: MultiStepInput, state: Partial<State>) {
        const pick = await input.showQuickPick({
            title,
            step: 1,
            totalSteps: 2,
            placeholder: 'Pick a database to query',
            items: databases,
            activeItem: state.database,
            shouldResume: shouldResume,
            onInputChanged: null,
        });
        // if (pick instanceof MyButton) {
        // 	return (input: MultiStepInput) => inputResourceGroupName(input, state);
        // }
        state.database = pick;
        return (input: MultiStepInput) => inputQuery(input, state);
    }

    async function inputQuery(input: MultiStepInput, state: Partial<State>) {
        const pick = await input.showQuickPick({
            title,
            step: 2,
            totalSteps: 2,
            placeholder: 'Enter query',
            items: [],
            activeItem: null,
            shouldResume: shouldResume,
            onInputChanged: (value) => onQueryUpdated(state.database['id'], value, input),
        });
        state.entity = pick;
    }

    async function onQueryUpdated(database: string, query: string, input: MultiStepInput) {
        await sleep(666);
        if (input.current && input.current.step === 2 && input.instanceOfQuickPick(input.current)) {
            if (input.current.value !== query) {
                return;
            }
        } else {
            return;
        }
        window.withProgress({
            location: ProgressLocation.Notification,
            title: "Searching for annotations...",
            cancellable: true
        }, (progress, token) => {
            return commands.executeCommand('antimony.sendQuery', database, query).then(async (result) => {
                await input.onQueryResults(result);
            });
        })
    }

    function shouldResume() {
        // Could show a notification with the option to resume.
        return new Promise<boolean>((resolve, reject) => {
            // noop
        });
    }

    const state = await collectInputs();
    return {
        'database': state.database.label,
        'entity': state.entity
    }
    // window.showInformationMessage(`Creating Application Service '${state.name}'`);
}


// -------------------------------------------------------
// Helper code that wraps the API for the multi-step case.
// -------------------------------------------------------


class InputFlowAction {
    static back = new InputFlowAction();
    static cancel = new InputFlowAction();
    static resume = new InputFlowAction();
}

type InputStep = (input: MultiStepInput) => Thenable<InputStep | void>;

interface QuickPickParameters<T extends QuickPickItem> {
    title: string;
    step: number;
    totalSteps: number;
    items: T[];
    activeItem?: T;
    placeholder: string;
    buttons?: QuickInputButton[];
    initialValue?: string;
    shouldResume: () => Thenable<boolean>;
    onInputChanged: (v: string) => void;
}

interface InputBoxParameters {
    title: string;
    step: number;
    totalSteps: number;
    value: string;
    prompt: string;
    validate: (value: string) => Promise<string | undefined>;
    buttons?: QuickInputButton[];
    shouldResume: () => Thenable<boolean>;
}

export class MultiStepInput {

    static async run<T>(start: InputStep) {
        const input = new MultiStepInput();
        return input.stepThrough(start);
    }

    current?: QuickInput;
    private steps: InputStep[] = [];
    private lastErrorMillis = 0;

    private async stepThrough<T>(start: InputStep) {
        let step: InputStep | void = start;
        while (step) {
            this.steps.push(step);
            if (this.current) {
                this.current.enabled = false;
                this.current.busy = true;
            }
            try {
                step = await step(this);
            } catch (err) {
                if (err === InputFlowAction.back) {
                    this.steps.pop();
                    step = this.steps.pop();
                } else if (err === InputFlowAction.resume) {
                    step = this.steps.pop();
                } else if (err === InputFlowAction.cancel) {
                    step = undefined;
                } else {
                    throw err;
                }
            }
        }
        if (this.current) {
            this.current.dispose();
        }
    }

    async showQuickPick<T extends QuickPickItem, P extends QuickPickParameters<T>>(
        { title, step, totalSteps, items, activeItem, placeholder, buttons, initialValue, shouldResume, onInputChanged }: P) {
        const disposables: Disposable[] = [];
        try {
            return await new Promise<T | (P extends { buttons: (infer I)[] } ? I : never)>((resolve, reject) => {
                const input = window.createQuickPick<T>();
                input.title = title;
                input.step = step;
                input.totalSteps = totalSteps;
                input.placeholder = placeholder;
                input.items = items;
                if (initialValue) {
                    input.value = initialValue;
                    onInputChanged(initialValue);
                }
                if (activeItem) {
                    input.activeItems = [activeItem];
                }
                input.buttons = [
                    ...(this.steps.length > 1 ? [QuickInputButtons.Back] : []),
                    ...(buttons || [])
                ];
                disposables.push(
                    input.onDidTriggerButton(item => {
                        if (item === QuickInputButtons.Back) {
                            reject(InputFlowAction.back);
                        } else {
                            resolve(<any>item);
                        }
                    }),
                    input.onDidChangeSelection(items => resolve(items[0])),
                    input.onDidHide(() => {
                        (async () => {
                            reject(shouldResume && await shouldResume() ? InputFlowAction.resume : InputFlowAction.cancel);
                        })()
                            .catch(reject);
                    }),
                    ...(onInputChanged ? [input.onDidChangeValue(onInputChanged)] : []),
                );
                if (this.current) {
                    this.current.dispose();
                }
                this.current = input;
                this.current.show();
            });
        } finally {
            disposables.forEach(d => d.dispose());
        }
    }

    instanceOfQuickPick(input): input is QuickPick<QuickPickItem> {
        return 'items' in input;
    }

    async onQueryResults(result) {
        if (this.current && this.current.step === 2) {
            if (this.instanceOfQuickPick(this.current)) {
                if (result.error) {
                    this.current.items = [];

                    // Don't display errors too often
                    const curMillis = new Date().getTime();
                    if (curMillis - this.lastErrorMillis < 1000) {
                        return;
                    }
                    this.lastErrorMillis = curMillis;
                    window.showErrorMessage(`Could not perform query: ${result.error}`).then(() => console.log('finished'));
                    return;
                }

                if (this.current.value === result.query) {
                    if (result.items.length == 0) {
                        window.showInformationMessage("Annotation not found")
                    }
                    this.current.items = result.items.map((item) => {
                        item['label'] = item['name'];
                        item['detail'] = item['detail'];
                        item['description'] = 'description';
                        item['alwaysShow'] = true;
                        return item;
                    });
                }
            }
        }
    }

    async showInputBox<P extends InputBoxParameters>({ title, step, totalSteps, value, prompt, validate, buttons, shouldResume }: P) {
        const disposables: Disposable[] = [];
        try {
            return await new Promise<string | (P extends { buttons: (infer I)[] } ? I : never)>((resolve, reject) => {
                const input = window.createInputBox();
                input.title = title;
                input.step = step;
                input.totalSteps = totalSteps;
                input.value = value || '';
                input.prompt = prompt;
                input.buttons = [
                    ...(this.steps.length > 1 ? [QuickInputButtons.Back] : []),
                    ...(buttons || [])
                ];
                let validating = validate('');
                disposables.push(
                    input.onDidTriggerButton(item => {
                        if (item === QuickInputButtons.Back) {
                            reject(InputFlowAction.back);
                        } else {
                            resolve(<any>item);
                        }
                    }),
                    input.onDidAccept(async () => {
                        const value = input.value;
                        input.enabled = false;
                        input.busy = true;
                        if (!(await validate(value))) {
                            resolve(value);
                        }
                        input.enabled = true;
                        input.busy = false;
                    }),
                    input.onDidChangeValue(async text => {
                        const current = validate(text);
                        validating = current;
                        const validationMessage = await current;
                        if (current === validating) {
                            input.validationMessage = validationMessage;
                        }
                    }),
                    input.onDidHide(() => {
                        (async () => {
                            reject(shouldResume && await shouldResume() ? InputFlowAction.resume : InputFlowAction.cancel);
                        })()
                            .catch(reject);
                    })
                );
                if (this.current) {
                    this.current.dispose();
                }
                this.current = input;
                this.current.show();
            });
        } finally {
            disposables.forEach(d => d.dispose());
        }
    }
}

export async function createAnnotationDialog(context: vscode.ExtensionContext, args: any[]) {
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

export async function insertAnnotation(selectedItem, entityName, line) {
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

export async function navigateAnnotation(context: vscode.ExtensionContext, args: any[]) {
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