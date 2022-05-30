"use strict";
/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *  Modified by Gary Geng and Steve Ma for the Antimony VSCode extension project.
 *--------------------------------------------------------------------------------------------*/
Object.defineProperty(exports, "__esModule", { value: true });
exports.MultiStepInput = exports.multiStepInput = void 0;
const vscode_1 = require("vscode");
const utils_1 = require("./utils/utils");
const vscode_2 = require("vscode");
/**
 * A multi-step input using window.createQuickPick() and window.createInputBox().
 *
 * This first part uses the helper class `MultiStepInput` that wraps the API for the multi-step case.
 */
async function multiStepInput(context, initialEntity = null) {
    const databases = [
        { label: 'ChEBI', id: 'chebi' },
        { label: 'UniProt', id: 'uniprot' }
    ];
    async function collectInputs() {
        const state = { initialEntity };
        await MultiStepInput.run(input => pickDatabase(input, state));
        return state;
    }
    const title = 'Create Annotation';
    async function pickDatabase(input, state) {
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
        return (input) => inputQuery(input, state);
    }
    async function inputQuery(input, state) {
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
    async function onQueryUpdated(database, query, input) {
        await (0, utils_1.sleep)(666);
        if (input.current && input.current.step === 2 && input.instanceOfQuickPick(input.current)) {
            if (input.current.value !== query) {
                return;
            }
        }
        else {
            return;
        }
        vscode_1.window.withProgress({
            location: vscode_2.ProgressLocation.Notification,
            title: "Searching for annotations...",
            cancellable: true
        }, (progress, token) => {
            return vscode_1.commands.executeCommand('antimony.sendQuery', database, query).then(async (result) => {
                await input.onQueryResults(result);
            });
        });
    }
    function shouldResume() {
        // Could show a notification with the option to resume.
        return new Promise((resolve, reject) => {
            // noop
        });
    }
    const state = await collectInputs();
    return {
        'database': state.database.label,
        'entity': state.entity
    };
    // window.showInformationMessage(`Creating Application Service '${state.name}'`);
}
exports.multiStepInput = multiStepInput;
// -------------------------------------------------------
// Helper code that wraps the API for the multi-step case.
// -------------------------------------------------------
class InputFlowAction {
}
InputFlowAction.back = new InputFlowAction();
InputFlowAction.cancel = new InputFlowAction();
InputFlowAction.resume = new InputFlowAction();
class MultiStepInput {
    constructor() {
        this.steps = [];
        this.lastErrorMillis = 0;
    }
    static async run(start) {
        const input = new MultiStepInput();
        return input.stepThrough(start);
    }
    async stepThrough(start) {
        let step = start;
        while (step) {
            this.steps.push(step);
            if (this.current) {
                this.current.enabled = false;
                this.current.busy = true;
            }
            try {
                step = await step(this);
            }
            catch (err) {
                if (err === InputFlowAction.back) {
                    this.steps.pop();
                    step = this.steps.pop();
                }
                else if (err === InputFlowAction.resume) {
                    step = this.steps.pop();
                }
                else if (err === InputFlowAction.cancel) {
                    step = undefined;
                }
                else {
                    throw err;
                }
            }
        }
        if (this.current) {
            this.current.dispose();
        }
    }
    async showQuickPick({ title, step, totalSteps, items, activeItem, placeholder, buttons, initialValue, shouldResume, onInputChanged }) {
        const disposables = [];
        try {
            return await new Promise((resolve, reject) => {
                const input = vscode_1.window.createQuickPick();
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
                    ...(this.steps.length > 1 ? [vscode_1.QuickInputButtons.Back] : []),
                    ...(buttons || [])
                ];
                disposables.push(input.onDidTriggerButton(item => {
                    if (item === vscode_1.QuickInputButtons.Back) {
                        reject(InputFlowAction.back);
                    }
                    else {
                        resolve(item);
                    }
                }), input.onDidChangeSelection(items => resolve(items[0])), input.onDidHide(() => {
                    (async () => {
                        reject(shouldResume && await shouldResume() ? InputFlowAction.resume : InputFlowAction.cancel);
                    })()
                        .catch(reject);
                }), ...(onInputChanged ? [input.onDidChangeValue(onInputChanged)] : []));
                if (this.current) {
                    this.current.dispose();
                }
                this.current = input;
                this.current.show();
            });
        }
        finally {
            disposables.forEach(d => d.dispose());
        }
    }
    instanceOfQuickPick(input) {
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
                    vscode_1.window.showErrorMessage(`Could not perform query: ${result.error}`).then(() => console.log('finished'));
                    return;
                }
                if (this.current.value === result.query) {
                    if (result.items.length == 0) {
                        vscode_1.window.showInformationMessage("Annotation not found");
                    }
                    this.current.items = result.items.map((item) => {
                        item['label'] = item['name'];
                        item['detail'] = 'detail';
                        item['description'] = 'description';
                        item['alwaysShow'] = true;
                        return item;
                    });
                }
            }
        }
    }
    async showInputBox({ title, step, totalSteps, value, prompt, validate, buttons, shouldResume }) {
        const disposables = [];
        try {
            return await new Promise((resolve, reject) => {
                const input = vscode_1.window.createInputBox();
                input.title = title;
                input.step = step;
                input.totalSteps = totalSteps;
                input.value = value || '';
                input.prompt = prompt;
                input.buttons = [
                    ...(this.steps.length > 1 ? [vscode_1.QuickInputButtons.Back] : []),
                    ...(buttons || [])
                ];
                let validating = validate('');
                disposables.push(input.onDidTriggerButton(item => {
                    if (item === vscode_1.QuickInputButtons.Back) {
                        reject(InputFlowAction.back);
                    }
                    else {
                        resolve(item);
                    }
                }), input.onDidAccept(async () => {
                    const value = input.value;
                    input.enabled = false;
                    input.busy = true;
                    if (!(await validate(value))) {
                        resolve(value);
                    }
                    input.enabled = true;
                    input.busy = false;
                }), input.onDidChangeValue(async (text) => {
                    const current = validate(text);
                    validating = current;
                    const validationMessage = await current;
                    if (current === validating) {
                        input.validationMessage = validationMessage;
                    }
                }), input.onDidHide(() => {
                    (async () => {
                        reject(shouldResume && await shouldResume() ? InputFlowAction.resume : InputFlowAction.cancel);
                    })()
                        .catch(reject);
                }));
                if (this.current) {
                    this.current.dispose();
                }
                this.current = input;
                this.current.show();
            });
        }
        finally {
            disposables.forEach(d => d.dispose());
        }
    }
}
exports.MultiStepInput = MultiStepInput;
//# sourceMappingURL=annotationInput.js.map