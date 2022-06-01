/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *  Modified by Gary Geng and Steve Ma for the Antimony VSCode extension project.
 *--------------------------------------------------------------------------------------------*/

import { QuickPickItem, window, Disposable, CancellationToken, QuickInputButton, QuickInput, ExtensionContext, QuickInputButtons, Uri, commands, QuickPick } from 'vscode';
import { integer, LogMessageNotification } from 'vscode-languageclient';
import { sleep } from './utils/utils';
import { ProgressLocation } from 'vscode'
import { Stats } from 'webpack';

/**
 * A multi-step input using window.createQuickPick() and window.createInputBox().
 * 
 * This first part uses the helper class `MultiStepInput` that wraps the API for the multi-step case.
 */
export async function multiStepInput(context: ExtensionContext, initialEntity: string = null, selectedType: string = null) {
    console.log("3 selected type: " + selectedType);
    var databases;
    if (selectedType === 'compartment') {
        databases = [
            { label: 'Recommended Databases:'},
            { label: '  Gene Ontology', id: 'gontology'},
            { label: '  Cell Type Ontology', id: 'contology'},
            { label: '  Mouse Adult Gross Anatomy', id: 'montology'},
            { label: '  Ontology for Biomedical Investigations', id: 'bontology'},
            { label: '  Foundational Model of Anatomy', id: 'fontology'},
            { label: 'OTHER Databases:'},
            { label: '  ChEBI', id: 'chebi' },
            { label: '  Protein Ontology', id: 'pontology'},
            { label: '  UniProt', id: 'uniprot'},
            { label: '  RHEA', id: 'rhea'}];
    } else if (selectedType === 'species') {
        databases = [
            { label: 'Recommended Databases:'},
            { label: '  ChEBI', id: 'chebi' },
            { label: '  Protein Ontology', id: 'pontology'},
            { label: '  UniProt', id: 'uniprot'},
            { label: 'OTHER Databases:'},
            { label: '  RHEA', id: 'rhea'},
            { label: '  Gene Ontology', id: 'gontology'},
            { label: '  Cell Type Ontology', id: 'contology'},
            { label: '  Mouse Adult Gross Anatomy', id: 'montology'},
            { label: '  Ontology for Biomedical Investigations', id: 'bontology'},
            { label: '  Foundational Model of Anatomy', id: 'fontology'}];
    } else if (selectedType === 'reaction') {
        databases = [
            { label: 'Recommended Databases:'},
            { label: '  Gene Ontology', id: 'gontology'},
            { label: '  RHEA', id: 'rhea'},
            { label: 'OTHER Databases:'},
            { label: '  ChEBI', id: 'chebi' },
            { label: '  Protein Ontology', id: 'pontology'},
            { label: '  UniProt', id: 'uniprot'},
            { label: '  Cell Type Ontology', id: 'contology'},
            { label: '  Mouse Adult Gross Anatomy', id: 'montology'},
            { label: '  Ontology for Biomedical Investigations', id: 'bontology'},
            { label: '  Foundational Model of Anatomy', id: 'fontology'}];
    } else {
        databases = [
            { label: 'ChEBI', id: 'chebi' },
            { label: 'UniProt', id: 'uniprot'},
            { label: 'RHEA', id: 'rhea'},
            { label: 'Gene Ontology', id: 'gontology'},
            { label: 'Cell Type Ontology', id: 'contology'},
            { label: 'Protein Ontology', id: 'pontology'},
            { label: 'Ontology for Biomedical Investigations', id: 'bontology'},
            { label: 'Foundational Model of Anatomy', id: 'fontology'},
            { label: 'Mouse Adult Gross Anatomy', id: 'montology'}];
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
