/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *  Modified by Gary Geng and Steve Ma for the Antimony VSCode extension project.
 *--------------------------------------------------------------------------------------------*/

import * as vscode from 'vscode';
import { QuickPickItem, window, Disposable, QuickInputButton, QuickInput, ExtensionContext, QuickInputButtons, commands, QuickPick, ProgressLocation } from 'vscode';
import { sleep } from './utils/utils';

/**
 * A multi-step input using window.createQuickPick() and window.createInputBox().
 * 
 * This first part uses the helper class `MultiStepInput` that wraps the API for the multi-step case.
 */
export async function rateLawMultiStepInput(context: ExtensionContext, line: number, initialEntity: string = null,) {
    let databases = [];
    let rateLawDict;
    vscode.commands.executeCommand('antimony.getRateLawDict', initialEntity).then(async (result) => {
        rateLawDict = result;
        
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
            totalSteps: 2,
            placeholder: 'Select rate law',
            items: databases,
            activeItem: state.database,
            shouldResume: shouldResume,
            onInputChanged: null,
        });
        state.database = pick;
        onQueryUpdated(state.database['id'], state.database['label'], input)
    }

    // async function inputQuery(input: MultiStepInput, state: Partial<State>) {
    //     const pick = await input.showQuickPick({
    //         title,
    //         step: 2,
    //         totalSteps: 2,
    //         // Later implement dynamic constant and displaying dynamic number of constants 
    //         // and have the user input multiple constants separated by a comma so we can parse
    //         placeholder: 'Input constant',
    //         items: [],
    //         activeItem: null,
    //         shouldResume: shouldResume,
    //         onInputChanged: (value) => {onQueryUpdated(state.database['id'], value, state.database['label'], input)}
    //     });
    //     state.entity = pick;
    // }

    async function onQueryUpdated(expresion: string, rateLawName: string, input: MultiStepInput) {
        await sleep(666);

        let index;
        for (let i = 0; i < rateLawDict.length; i++) {
            if (rateLawDict[i].name === rateLawName) {
                index = i;
                break;
            }
        }

        const constantDict = [];

        for (const element of rateLawDict[index].constants) {
            console.log(element)
            constantDict.push({constant: element._name});
        }

        window.withProgress({
			location: ProgressLocation.Notification,
			title: "Instantiating rate law...",
			cancellable: true
		}, (progress, token) => {
            return commands.executeCommand('antimony.getRateLawStr', expresion, constantDict).then(async (result) => {
                // await input.onQueryResults(result);
                let snippetText;
                snippetText = result;
                const snippetStr = new vscode.SnippetString(" " + snippetText + ";");
                const doc = vscode.window.activeTextEditor.document;
                const pos = doc.lineAt(line).range.end;
                vscode.window.activeTextEditor.insertSnippet(snippetStr, pos);
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
