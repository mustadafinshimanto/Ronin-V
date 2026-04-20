const { spawn } = require('child_process');
const child = spawn('node', ['dist/index.js'], { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, FORCE_COLOR: '0' } });

let output = '';
child.stdout.on('data', (d) => {
    const str = d.toString();
    output += str;
    process.stdout.write(str);
});

child.stderr.on('data', (d) => process.stderr.write(d.toString()));

// Step 1: Wait for boot and scan
setTimeout(() => {
    console.log('\n--- SENDING /vm COMMAND ---');
    child.stdin.write('/vm\n');
}, 10000);

// Step 2: Check for prefix change and exit
setTimeout(() => {
    console.log('\n--- VERIFYING OUTPUT ---');
    if (output.includes('[VM]')) {
        console.log('SUCCESS: [VM] tag detected in output!');
    } else {
        console.log('FAILURE: [VM] tag not found.');
    }
    
    if (output.includes('kali-linux')) {
        console.log('SUCCESS: VM name detected in prompt!');
    } else {
        console.log('FAILURE: VM name not found in prompt context.');
    }

    child.stdin.write('/exit\n');
}, 15000);

setTimeout(() => {
    child.kill();
    process.exit(0);
}, 18000);
