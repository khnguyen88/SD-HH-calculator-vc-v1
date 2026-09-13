const fs = require('fs');
const path = require('path');

const dir = __dirname;
const devFile = path.join(dir, 'storm-drain-design-calculator-dev.html');
const bundleFile = path.join(dir, 'lib', 'sheetjs-bundle.js');
const outFile = path.join(dir, 'storm-drain-design-calculator.html');

const dev = fs.readFileSync(devFile, 'utf8');
const bundle = fs.readFileSync(bundleFile, 'utf8');

if (!dev.includes('/* SHEETJS_BUNDLE */')) {
  console.error('ERROR: placeholder not found in dev file');
  process.exit(1);
}

const built = dev.replace('/* SHEETJS_BUNDLE */', bundle.replace(/\$/g, '$$$$'));
fs.writeFileSync(outFile, built);

const inKB = Math.round(fs.statSync(devFile).size / 1024);
const outKB = Math.round(fs.statSync(outFile).size / 1024);
console.log(`Built: ${inKB} KB dev → ${outKB} KB dist`);
