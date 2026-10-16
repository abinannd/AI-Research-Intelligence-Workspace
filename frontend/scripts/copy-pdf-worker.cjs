const fs = require("fs");
const path = require("path");

const candidates = [
  path.join(__dirname, "..", "node_modules", "pdfjs-dist", "build", "pdf.worker.min.mjs"),
  path.join(__dirname, "..", "node_modules", "pdfjs-dist", "legacy", "build", "pdf.worker.min.mjs"),
];

const destDir = path.join(__dirname, "..", "public");
const dest = path.join(destDir, "pdf.worker.min.mjs");

const src = candidates.find((file) => fs.existsSync(file));
if (!src) {
  console.warn("pdf.worker.min.mjs not found; PDF viewer will fall back to a CDN worker.");
  process.exit(0);
}

fs.mkdirSync(destDir, { recursive: true });
fs.copyFileSync(src, dest);
console.log(`Copied PDF.js worker to ${path.relative(path.join(__dirname, ".."), dest)}`);
