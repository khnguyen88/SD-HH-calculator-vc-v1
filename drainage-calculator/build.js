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

let out = dev.replace('/* SHEETJS_BUNDLE */', bundle.replace(/\$/g, '$$$$'));

// Spec 3: inline the shape reader after SheetJS so window.__xlsxShapeReader
// is available before the app's init() runs.
const shapeReaderSrc = fs.readFileSync(
  path.join(__dirname, 'lib', 'xlsx-shape-reader.js'), 'utf8'
);
out = out.replace(
  /<!--\s*XLSX_SHAPE_READER_PLACEHOLDER\s*-->[\s\S]*?<script src="lib\/xlsx-shape-reader\.js"><\/script>/,
  '<script>\n' + shapeReaderSrc.replace(/\$/g, '$$$$') + '\n</script>'
);

// Spec 3: Embed the golden template bytes as base64 so buildSimpleWorkbook
// and buildRobustWorkbook can load it as a styled base. ~335 KB increase.
const goldenBytes = fs.readFileSync(
  path.join(__dirname, "..", "docs", "template_golden.xlsx")
);
const goldenB64 = goldenBytes.toString("base64");
out = out.replace(
  /<!--\s*TEMPLATE_GOLDEN_B64_PLACEHOLDER\s*-->(\s*<script>[\s\S]*?__TEMPLATE_GOLDEN_B64[\s\S]*?<\/script>)?/,
  "<script>window.__TEMPLATE_GOLDEN_B64 = \"" + goldenB64 + "\";</script>"
);

fs.writeFileSync(outFile, out);

const inKB = Math.round(fs.statSync(devFile).size / 1024);
const outKB = Math.round(fs.statSync(outFile).size / 1024);
console.log(`Built: ${inKB} KB dev → ${outKB} KB dist`);
