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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const node_1 = require("vscode-languageclient/node");
let client;
async function activate(context) {
    // Register commands
    const extractMethodCommand = vscode.commands.registerCommand('cst-lsp.extractMethod', () => {
        vscode.window.showInformationMessage('Extract Method command executed');
    });
    const importSymbolCommand = vscode.commands.registerCommand('cst-lsp.importSymbol', () => {
        vscode.window.showInformationMessage('Import Symbol command executed');
    });
    context.subscriptions.push(extractMethodCommand, importSymbolCommand);
    // Server options - use CLI entry point from cst-lsp with stdio transport
    const serverOptions = {
        command: 'cst_lsp',
        args: ['--stdio'],
        transport: node_1.TransportKind.stdio
    };
    // Client options
    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'python' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.py')
        },
        middleware: {
            provideCodeActions: async (document, range, context, token, next) => {
                // Only handle our specific code actions
                const actions = await next(document, range, context, token);
                if (!actions)
                    return actions;
                return actions.filter(action => action.title === 'Extract Method' ||
                    action.title === 'Import Symbol' ||
                    action.title === 'Import All Missing');
            }
        }
    };
    // Create and start client
    client = new node_1.LanguageClient('cstLspServer', 'CST LSP Server', serverOptions, clientOptions);
    try {
        await client.start();
        console.log('CST LSP Client started successfully');
    }
    catch (error) {
        console.error('Failed to start CST LSP Client:', error);
        throw error;
    }
    // Export the client for testing
    return {
        languageClient: client
    };
}
function deactivate() {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
//# sourceMappingURL=extension.js.map