const { spawn } = require('child_process');
const child = spawn('node', ['dist/index.js'], { stdio: ['pipe', 'pipe', 'pipe'] });
child.stdout.on('data', (d) => process.stdout.write(d.toString()));
child.stderr.on('data', (d) => process.stderr.write(d.toString()));
setTimeout(() => {
    child.stdin.write('/exit\n');
}, 6000);
setTimeout(() => {
    child.kill();
    process.exit(0);
}, 9000);
