const { spawn } = require('child_process');
const child = spawn('node', ['dist/index.js'], { stdio: ['pipe', 'pipe', 'pipe'] });
child.stdout.on('data', (d) => process.stdout.write(d.toString()));
child.stderr.on('data', (d) => process.stderr.write(d.toString()));
setTimeout(() => {
    child.stdin.write('/exit\n');
}, 3000);
setTimeout(() => {
    child.kill();
    process.exit(0);
}, 6000);
