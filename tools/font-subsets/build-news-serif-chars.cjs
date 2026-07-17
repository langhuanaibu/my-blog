const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "../..");
const output = path.join(__dirname, "news-serif-sc.txt");
const corpusRoots = [
  path.join(root, "source/news/index.html"),
  path.join(root, "source/news/js"),
  path.join(root, "source/news/data/daily"),
  path.join(root, "source/news/data/weekly"),
];

function filesUnder(target) {
  if (!fs.existsSync(target)) return [];
  if (fs.statSync(target).isFile()) return [target];
  return fs.readdirSync(target, { withFileTypes: true })
    .sort((a, b) => a.name.localeCompare(b.name, "en"))
    .flatMap((entry) => filesUnder(path.join(target, entry.name)));
}

const corpus = corpusRoots.flatMap(filesUnder)
  .filter((file) => /\.(?:html|js|json)$/i.test(file))
  .map((file) => fs.readFileSync(file, "utf8"))
  .join("\n");
const counts = new Map();
for (const char of corpus) {
  if (!/\p{Script=Han}/u.test(char)) continue;
  counts.set(char, (counts.get(char) || 0) + 1);
}

const fixed = [...new Set([
  ...Array.from({ length: 0x7f - 0x20 }, (_, index) => String.fromCodePoint(0x20 + index)),
  ..."，。！？；：、（）《》〈〉【】“”‘’—…·￥／＋＝％＃＠＆＊｜～　",
])];
const commonHan = [...counts]
  .sort((a, b) => b[1] - a[1] || a[0].codePointAt(0) - b[0].codePointAt(0))
  .slice(0, 600)
  .map(([char]) => char);

fs.writeFileSync(output, fixed.concat(commonHan).join(""), "utf8");
console.log(`Wrote ${fixed.length + commonHan.length} characters to ${path.relative(root, output)}`);
