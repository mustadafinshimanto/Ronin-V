import { VBoxExecutor } from './dist/executors/Executors.js';
(async () => {
    const vbox = new VBoxExecutor();
    console.log('[*] Testing VM Command Execution...');
    const result = await vbox.execute('kali-linux-2026.1-virtualbox-amd64', 'kali', 'kali', 'whoami');
    console.log('Result:', JSON.stringify(result, null, 2));
})();
