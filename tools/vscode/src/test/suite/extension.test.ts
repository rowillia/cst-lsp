import * as assert from "assert";
import * as vscode from "vscode";
import * as path from "path";

suite("Extension Test Suite", () => {
    vscode.window.showInformationMessage("Start all tests.");

    test("Extension should be present", () => {
        assert.ok(vscode.extensions.getExtension("devin.cst-lsp"));
    });

    test("Should activate on Python file", async () => {
        const doc = await vscode.workspace.openTextDocument({
            content: "def test(): pass",
            language: "python"
        });
        await vscode.window.showTextDocument(doc);

        const ext = vscode.extensions.getExtension("devin.cst-lsp");
        assert.ok(ext);
        await ext.activate();
        assert.strictEqual(ext.isActive, true);
    });

    test("Should register code actions", async () => {
        const commands = await vscode.commands.getCommands();
        assert.ok(commands.includes("cst-lsp.extractMethod"), "Extract Method command not registered");
        assert.ok(commands.includes("cst-lsp.importSymbol"), "Import Symbol command not registered");
    });

    test("Should connect to LSP server", async function() {
        this.timeout(10000); // Increase timeout for LSP initialization

        const doc = await vscode.workspace.openTextDocument({
            content: "import missing_module\n\ndef test():\n    x = 42\n    print(x)",
            language: "python"
        });
        await vscode.window.showTextDocument(doc);

        // Wait for LSP server to initialize
        await new Promise(resolve => setTimeout(resolve, 2000));

        const ext = vscode.extensions.getExtension("devin.cst-lsp");
        assert.ok(ext?.exports?.languageClient, "Language client not initialized");
    });
});
