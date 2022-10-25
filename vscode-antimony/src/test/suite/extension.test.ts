import * as assert from 'assert';

// You can import and use all API from the 'vscode' module
// as well as import your extension to test it
import * as vscode from 'vscode';
// import * as myExtension from '../../extension';

suite('Extension Test Suite', () => {
	vscode.window.showInformationMessage('Start all tests.');

    // Testing VSCode Configuration User Settings Visual Indication Highlight Switch Indication On
    test("Testing VSCode User Settings Visual Indication Highlight Switch Indication On", async () => {
        let settings = vscode.workspace.getConfiguration('vscode-antimony');
        await settings.update("annotatedVariableIndicatorOn", true, true);
        
        if (vscode.workspace.getConfiguration('vscode-antimony').get("annotatedVariableIndicatorOn") === true) {
            assert(true);
        } else {
            assert(false);
        }
    });
    
    // Testing VSCode Configuration User Settings Visual Indication Highlight Switch Indication Off
    test("Testing VSCode User Settings Visual Indication Highlight Switch Indication Off", async () => {
        let settings = vscode.workspace.getConfiguration('vscode-antimony');
        await settings.update("annotatedVariableIndicatorOn", false, true);
        
        if (vscode.workspace.getConfiguration('vscode-antimony').get("annotatedVariableIndicatorOn") === false) {
            assert(true);
        } else {
            assert(false);
        }
    });

    // Testing VSCode Configuration User Setting Visual Indication Highlight Color Changer Update
    test("Testing VSCode Configuration User Setting Visual Indication Highlight Color Changer", async () => {
        let settings = vscode.workspace.getConfiguration('vscode-antimony');
        await settings.update("highlightColor", "green", true);

        if (vscode.workspace.getConfiguration('vscode-antimony').get("highlightColor") === "indigo") {
            await settings.update("highlightColor", "red", true);

            if (vscode.workspace.getConfiguration('vscode-antimony').get("highlightColor") === "red") {
                assert(true);
            } else {
                assert(false);
            }
        }
    });

    // Testing VSCode Context Menu Visual Indication Highlight Switch On and Setting Syncing
    test("Testing VSCode Context Menu Visual Indication Highlight Switch On and Both Settings Syncing", async (done) => {
        if (vscode.workspace.getConfiguration('vscode-antimony').get("annotatedVariableIndicatorOn") === false) {
            vscode.commands.executeCommand('antimony.switchIndicationOn');
        }

        done();

        if (vscode.workspace.getConfiguration('vscode-antimony').get("annotatedVariableIndicatorOn") === true) {
            assert(true);
        } else {
            assert(false);
        }
    });

    // Testing VSCode Context Menu Visual Indication Highlight Switch Off and Both Settings Syncing
    test("Testing VSCode Context Menu Visual Indication Highlight Switch Off and Both Settings Syncing", async () => {
        if (vscode.workspace.getConfiguration('vscode-antimony').get("annotatedVariableIndicatorOn") === true) {
            await vscode.commands.executeCommand('antimony.switchIndicationOff');
        }
        
        if (vscode.workspace.getConfiguration('vscode-antimony').get("annotatedVariableIndicatorOn") === false) {
            assert(true);
        } else {
            assert(false);
        }
    });

});


