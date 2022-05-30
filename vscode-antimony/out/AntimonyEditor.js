"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AntimonyEditorProvider = void 0;
const vscode = require("vscode");
const utils = require("./utils/utils");
class AntimonyEditorProvider {
    constructor(context) {
        this.context = context;
    }
    static async register(context, client) {
        if (!client) {
            utils.pythonInterpreterError();
            return;
        }
        await client.onReady();
        const provider = new AntimonyEditorProvider(context);
        const providerRegistration = vscode.window.registerCustomEditorProvider(AntimonyEditorProvider.viewType, provider);
        return providerRegistration;
    }
    /**
     * Called when our custom editor is opened.
     *
     *
     */
    async resolveCustomTextEditor(document, webviewPanel, _token) {
        // Setup initial content for the webview
        webviewPanel.webview.options = {
            enableScripts: true,
        };
        getAntimonyString(document, webviewPanel);
        const changeDocumentSubscription = vscode.workspace.onDidSaveTextDocument(e => {
            if (!webviewPanel.active && e.uri.toString() === document.uri.toString()) {
                getAntimonyString(document, webviewPanel);
            }
        });
        webviewPanel.onDidDispose(() => {
            changeDocumentSubscription.dispose();
        });
        webviewPanel.webview.onDidReceiveMessage(message => {
            switch (message.command) {
                case 'antimonyOnSave':
                    webviewPanel.webview.html =
                        `
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Antimony</title>
                    </head>
                    <body>
                        <div contenteditable="true" id="antimony">
                            <pre id="antimony-text">
                                ${message.antimony}
                            </pre>
                            <script>
                                let size = getComputedStyle(document.body).getPropertyValue('--vscode-editor-font-size')
                                document.getElementById("antimony").style="font-size: " + size;
        
                                (function() {
                                    const vscode = acquireVsCodeApi();
                                    document.addEventListener('keydown', e => {
                                        if (e.ctrlKey && e.key === 's') {
                                            const node = document.getElementById('antimony-text');
                                            vscode.postMessage({
                                                command: 'antimonyOnSave',
                                                antimony: node.innerHTML
                                            })
                                        }
                                    });
                                }())
                            </script>
                        </div>
                        
                    </html>
                    `;
                    let msg = message.antimony;
                    msg = String(msg).replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/"/g, '"');
                    vscode.commands.executeCommand('antimony.antStrToSBMLStr', msg)
                        .then(async (result) => {
                        if (result.error) {
                            vscode.window.showErrorMessage(`Error while converting: ${result.error}`);
                        }
                        else {
                            const edit = new vscode.WorkspaceEdit();
                            edit.replace(document.uri, new vscode.Range(0, 0, document.lineCount, 0), result.sbml_str);
                            return vscode.workspace.applyEdit(edit);
                        }
                    });
            }
        });
    }
}
exports.AntimonyEditorProvider = AntimonyEditorProvider;
AntimonyEditorProvider.viewType = 'antimony.antimonyEditor';
function getAntimonyString(document, webviewPanel) {
    vscode.commands.executeCommand('antimony.sbmlFileToAntStr', document)
        .then(async (result) => {
        let msg = '';
        if (result.error) {
            msg = result.error;
            webviewPanel.webview.html =
                `
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Antimony</title>
                </head>
                <body>
                    <div id="antimony">
                        <p id="antimony-text">
                            ${msg}
                        </p>
                        <script>
                            let size = getComputedStyle(document.body).getPropertyValue('--vscode-editor-font-size')
                            document.getElementById("antimony").style="font-size: " + size;
                        </script>
                    </div>
                    
                </html>
                `;
        }
        else {
            msg = result.ant_str;
            webviewPanel.webview.html =
                `
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Antimony</title>
                </head>
                <body>
                    <div contenteditable="true" id="antimony">
                        <pre id="antimony-text">
                            ${msg}
                        </pre>
                        <script>
                            let size = getComputedStyle(document.body).getPropertyValue('--vscode-editor-font-size')
                            document.getElementById("antimony").style="font-size: " + size;
    
                            (function() {
                                const vscode = acquireVsCodeApi();
                                document.addEventListener('keydown', e => {
                                    if (e.ctrlKey && e.key === 's') {
                                        const node = document.getElementById('antimony-text');
                                        vscode.postMessage({
                                            command: 'antimonyOnSave',
                                            antimony: node.innerHTML
                                        })
                                    }
                                });
                            }())
                        </script>
                    </div>
                    
                </html>
                `;
        }
    });
}
//# sourceMappingURL=AntimonyEditor.js.map