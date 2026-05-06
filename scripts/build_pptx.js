// build_pptx.js — html2pptx 워크플로우 (browser-as-truth)
//
// Usage:
//   node build_pptx.js --slides <DIR> --out <FILE.pptx> [--title "..."] [--author "..."]
//
// 모든 <DIR>/slide-*.html 을 LAYOUT_WIDE (13.333" × 7.5") 슬라이드로 변환.
// 각 텍스트/도형은 PowerPoint native 객체로 들어가 편집 가능.

const path = require('path');
const fs = require('fs');
const PptxGenJS = require('pptxgenjs');
const html2pptx = require('./html2pptx.js');

function parseArgs(argv) {
  const out = { title: 'Brand PPTX', author: 'design.md' };
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    const v = argv[i + 1];
    if (k === '--slides') { out.slides = v; i++; }
    else if (k === '--out') { out.out = v; i++; }
    else if (k === '--title') { out.title = v; i++; }
    else if (k === '--author') { out.author = v; i++; }
  }
  if (!out.slides || !out.out) {
    console.error('usage: node build_pptx.js --slides <DIR> --out <FILE.pptx> [--title ...] [--author ...]');
    process.exit(2);
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv);
  const slidesDir = path.resolve(args.slides);
  const outFile = path.resolve(args.out);

  if (!fs.existsSync(slidesDir)) {
    console.error(`slides dir not found: ${slidesDir}`);
    process.exit(2);
  }
  fs.mkdirSync(path.dirname(outFile), { recursive: true });

  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.title = args.title;
  pptx.author = args.author;

  const files = fs.readdirSync(slidesDir)
    .filter(f => /^slide-\d+\.html$/.test(f))
    .sort();

  if (files.length === 0) {
    console.error(`no slide-*.html files in ${slidesDir}`);
    process.exit(2);
  }

  for (const f of files) {
    const fp = path.join(slidesDir, f);
    console.log(`converting  ${f}`);
    await html2pptx(fp, pptx);
  }

  await pptx.writeFile({ fileName: outFile });
  console.log(`OK  ${outFile}`);
}

main().catch(err => {
  console.error('FAIL', err);
  process.exit(1);
});
