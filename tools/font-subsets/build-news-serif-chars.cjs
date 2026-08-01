// 这份清单只决定衬线字体的首屏分片装什么，不决定字体覆盖什么。
// 子集外的字形由 tools/generate-news-font.cjs 的 subsetRemainChars 保留在尾部
// 分片里，按需加载，所以语料增长不会导致漏字，也就不需要定期重新生成。
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
const han = new Set();
for (const char of corpus) {
  if (/\p{Script=Han}/u.test(char)) han.add(char);
}

const fixed = [...new Set([
  ...Array.from({ length: 0x7f - 0x20 }, (_, index) => String.fromCodePoint(0x20 + index)),
  ..."，。！？；：、（）《》〈〉【】“”‘’—…·￥／＋＝％＃＠＆＊｜～　",
])];
// 语料里出现过的汉字全收：热区越贴合真实用字，首屏命中的尾部分片越少。
// 按码位排序而非词频，保证同一仓库状态下输出逐字节可复现。
const corpusHan = [...han].sort((a, b) => a.codePointAt(0) - b.codePointAt(0));

fs.writeFileSync(output, fixed.concat(corpusHan).join(""), "utf8");
console.log(`Wrote ${fixed.length + corpusHan.length} characters to ${path.relative(root, output)}`);
