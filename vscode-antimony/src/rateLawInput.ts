/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *  Modified by Gary Geng and Steve Ma for the Antimony VSCode extension project.
 *--------------------------------------------------------------------------------------------*/

import * as vscode from 'vscode';
import { QuickPickItem, window, Disposable, QuickInputButton, QuickInput, ExtensionContext, QuickInputButtons, QuickPick } from 'vscode';
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
export async function rateLawSingleStepInput(context: ExtensionContext, line: number, initialEntity: string = null,) {
    let databases = [];
    let rateLawDict;
    vscode.commands.executeCommand('antimony.getRateLawDict', initialEntity).then(async (result) => {
        rateLawDict = result;
        
        if (rateLawDict.error) {
            vscode.window
	        .showErrorMessage(
		        rateLawDict.error,
	        )
            return;
        }        
        for (let i = 0; i < rateLawDict.length; i++) {
            databases.push({id: rateLawDict[i].expression, label: rateLawDict[i].name, index: i}); 
        }

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

    const title = 'Insert Rate Law';

    async function pickDatabase(input: MultiStepInput, state: Partial<State>) {
        const pick = await input.showQuickPick({
            title,
            step: 1,
            totalSteps: 1,
            placeholder: 'Select rate law',
            items: databases,
            activeItem: state.database,
            shouldResume: shouldResume,
            onInputChanged: null,
        });
        state.database = pick;
        onQueryUpdated(state.database['id'], state.database['label'], state.database['index'], input)
    }

    async function onQueryUpdated(expresion: string, rateLawName: string, rateLawIndex: number, input: MultiStepInput) {
        const snippetStr = new vscode.SnippetString(" " + expresion + ";");

        const doc = vscode.window.activeTextEditor.document;
        const pos = doc.lineAt(line).range.end;

        let count = 0;
        let ix = initialEntity.length - 1;
        while (ix >= 0 && (/\s/).test(initialEntity[ix--])) {
            count += 1;
        }
        const endRange = new vscode.Range(pos.line, pos.character - count, pos.line, pos.character - count);
        vscode.window.activeTextEditor.insertSnippet(snippetStr, endRange);
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
    });
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
            return result;
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

// insert rate law
export async function insertRateLawDialog(context: vscode.ExtensionContext, args: any[]) {
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