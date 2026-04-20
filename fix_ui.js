const fs = require('fs');
const path = 'C:/Storage/Workspace/Antigravity/Ronin-V/src/ui/SentinelUI.ts';
let code = fs.readFileSync(path, 'utf8');

const regex = /const ctx = \(this\.agent\.targetEnv === 'vm' && this\.agent\.linkedVm\) \? this\.agent\.linkedVm\.name : "sentinel";\s*const roleTag = this\.agent\.currentRole !== "DEFAULT" \? `\(\${this\.agent\.currentRole\.split\(' '\)\[0\]}\)` : "";\s*const prefix = `\${chalk\.hex\('#ff003c'\)\.bold\(`ronin\${roleTag}`\)}\/\${chalk\.hex\('#880000'\)\(ctx\)} \${chalk\.hex\('#ff003c'\)\.bold\('>'\)}`;/;

const replacement = `const envTag = this.agent.targetEnv === 'vm' ? '[VM] ' : '';
                const ctx = (this.agent.targetEnv === 'vm') ? (this.agent.linkedVm ? this.agent.linkedVm.name : 'UNLINKED_VM') : 'sentinel';
                const roleTag = this.agent.currentRole !== 'DEFAULT' ? \\\`(\\${this.agent.currentRole.split(' ')[0]})\\\` : '';
                const prefix = \\\`\\${chalk.hex('#ff003c').bold(envTag + 'ronin' + roleTag)}/\\${chalk.hex('#880000')(ctx)} \\${chalk.hex('#ff003c').bold('>')}\\\`;`;

if (regex.test(code)) {
    code = code.replace(regex, replacement);
    fs.writeFileSync(path, code);
    console.log('Successfully updated UI prefix logic.');
} else {
    console.log('Target string not found. Please review SentinelUI.ts.');
    const start = code.indexOf('const ctx =');
    console.log(code.substring(start, start + 300));
}
