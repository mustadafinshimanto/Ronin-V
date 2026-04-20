import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const srcPath = path.join(__dirname, 'src');

function walk(dir) {
    fs.readdirSync(dir).forEach(file => {
        const fullPath = path.join(dir, file);
        if (fs.statSync(fullPath).isDirectory()) {
            walk(fullPath);
        } else if (file.endsWith('.ts') || file.endsWith('.tsx')) {
            let content = fs.readFileSync(fullPath, 'utf8');
            content = content.replace(/from\s+['"](\.\.?\/[^'"]+)['"]/g, (match, p1) => {
                if (p1.endsWith('.js')) return match;
                return `from '${p1}.js'`;
            });
            fs.writeFileSync(fullPath, content);
        }
    });
}

walk(srcPath);
