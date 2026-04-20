const { spawn } = require('child_process');
const child = spawn('node', ['dist/index.js'], { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, FORCE_COLOR: '0' } });
child.stdout.on('data', (d) => process.stdout.write(d.toString()));
child.stderr.on('data', (d) => process.stderr.write(d.toString()));
setTimeout(() => {
    child.stdin.write('hi\n');
}, 5000);
setTimeout(() => {
    child.stdin.write('/exit\n');
}, 15000);
setTimeout(() => {
    child.kill();
    process.exit(0);
}, 18000);
