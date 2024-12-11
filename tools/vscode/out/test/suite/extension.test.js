"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const assert = __importStar(require("assert"));
const vscode = __importStar(require("vscode"));
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
    test("Should connect to LSP server", async function () {
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
//# sourceMappingURL=extension.test.js.map