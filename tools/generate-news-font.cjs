const fs = require("node:fs");
const path = require("node:path");

const [input, subsetFile, outDir] = process.argv.slice(2);
if (!input || !subsetFile || !outDir) {
  console.error("Usage: node tools/generate-news-font.cjs <font.otf> <subset.txt> <out-dir>");
  process.exit(2);
}

const { fontSplit } = require("cn-font-split");
const points = [...new Set([...fs.readFileSync(subsetFile, "utf8")].map((char) => char.codePointAt(0)))];

fontSplit({
  input: path.resolve(input),
  outDir: path.resolve(outDir),
  subsets: [points],
  subsetRemainChars: false,
  autoSubset: false,
  languageAreas: false,
  chunkSize: 70000,
  testHtml: false,
  reporter: false,
  css: {
    fontFamily: "Noto Serif SC",
    fontWeight: "700",
    fontStyle: "normal",
    fontDisplay: "swap",
    fileName: "result.css",
    compress: false,
  },
}).then(() => {
  // cn-font-split 7.4.3's Windows FFI teardown can crash after successful output.
  process.exit(0);
}).catch((error) => {
  console.error(error);
  process.exit(1);
});
