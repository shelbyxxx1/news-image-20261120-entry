const { readFileSync, mkdirSync, readdirSync, rmSync, writeFileSync } = require('node:fs');
const { join } = require('node:path');

const outputDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const image = readFileSync(join(__dirname, 'entry.png'));

mkdirSync(outputDir, { recursive: true });
for (const name of readdirSync(outputDir)) {
    rmSync(join(outputDir, name), { recursive: true, force: true });
}
writeFileSync(join(outputDir, 'entry.png'), image);
