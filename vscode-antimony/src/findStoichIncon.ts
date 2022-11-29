import * as vscode from 'vscode';
import * as utils from './utils/utils';
import {
	LanguageClient,
} from 'vscode-languageclient/node';

export class FindStoichInconsisProvider implements vscode.CustomTextEditorProvider {

    public static async register(context: vscode.ExtensionContext, client: LanguageClient): Promise<vscode.Disposable> {
        if (!client) {
            utils.pythonInterpreterError();
            return;
        }
        await client.onReady();
		const provider = new FindStoichInconsisProvider(context);
		const providerRegistration = vscode.window.registerCustomEditorProvider(FindStoichInconsisProvider.viewType, provider);
		return providerRegistration;
	}
    
    private static readonly viewType = 'vscode.text';

    constructor(
		private readonly context: vscode.ExtensionContext
	) { }

    /**
	 * Called when our custom editor is opened.
	 * 
	 * 
	 */
	public async resolveCustomTextEditor(
		document: vscode.TextDocument,
		webviewPanel: vscode.WebviewPanel,
		_token: vscode.CancellationToken
	): Promise<void> {
        // Setup initial content for the webview
		webviewPanel.webview.options = {
			enableScripts: true,
		};
		findStoichiometricInconsistencies(document, webviewPanel)

		const changeDocumentSubscription = vscode.workspace.onDidSaveTextDocument(e => {
			if (!webviewPanel.active && e.uri.toString() === document.uri.toString()) {
				findStoichiometricInconsistencies(document, webviewPanel)
			}
		});

        webviewPanel.onDidDispose(() => {
			changeDocumentSubscription.dispose();
		});

        webviewPanel.webview.onDidReceiveMessage(
            message => {
                switch (message.command) {
                case 'antimonyOnSave':
                    webviewPanel.webview.html = 
                    `
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Find Stoichiometric Inconsistencies</title>
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
                }
            });
    }
}

async function findStoichiometricInconsistencies(document: vscode.TextDocument, webviewPanel: vscode.WebviewPanel) {
	vscode.commands.executeCommand('antimony.findSIs', document.getText)
	.then(async (result: any) => {
		let msg = '';
		console.log(result)
		msg = result.msg;
		console.log(msg)
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
	});
}