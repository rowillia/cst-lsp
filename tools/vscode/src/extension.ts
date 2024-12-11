import * as path from 'path';
import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;

export async function activate(context: vscode.ExtensionContext) {
    // Register commands
    const extractMethodCommand = vscode.commands.registerCommand('cst-lsp.extractMethod', () => {
        vscode.window.showInformationMessage('Extract Method command executed');
    });

    const importSymbolCommand = vscode.commands.registerCommand('cst-lsp.importSymbol', () => {
        vscode.window.showInformationMessage('Import Symbol command executed');
    });

    context.subscriptions.push(extractMethodCommand, importSymbolCommand);

    // Server options - use CLI entry point from cst-lsp with stdio transport
    const serverOptions: ServerOptions = {
        command: 'cst_lsp',
        args: ['--stdio'],
        transport: TransportKind.stdio
    };

    // Client options
    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'python' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.py')
        },
        middleware: {
            provideCodeActions: async (document, range, context, token, next) => {
                // Only handle our specific code actions
                const actions = await next(document, range, context, token);
                if (!actions) return actions;
                return actions.filter(action =>
                    action.title === 'Extract Method' ||
                    action.title === 'Import Symbol' ||
                    action.title === 'Import All Missing'
                );
            }
        }
    };

    // Create and start client
    client = new LanguageClient(
        'cstLspServer',
        'CST LSP Server',
        serverOptions,
        clientOptions
    );

    try {
        await client.start();
        console.log('CST LSP Client started successfully');
    } catch (error) {
        console.error('Failed to start CST LSP Client:', error);
        throw error;
    }

    // Export the client for testing
    return {
        languageClient: client
    };
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
