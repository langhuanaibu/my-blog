import fs from 'node:fs/promises';
import path from 'node:path';

const root = process.cwd();
const postsDir = path.join(root, 'source', '_posts');
const coversPath = path.join(root, 'source', '_data', 'category-covers.json');

function yamlString(value) {
  return JSON.stringify(String(value ?? ''));
}

function unquote(value) {
  return String(value || '')
    .trim()
    .replace(/^['"]|['"]$/g, '');
}

function firstCategory(frontMatter) {
  const match = frontMatter.match(/^categories:\n((?:\s+-\s*.+\n?)+)/m);
  if (!match) return '';

  const line = match[1].split(/\r?\n/).find((item) => item.trim().startsWith('- '));
  return line ? unquote(line.replace(/^\s+-\s*/, '')) : '';
}

function addIndexImage(source, cover) {
  source = source.replace(/^(index_img:\s*["'][^"']+["'])(old_id:)/m, '$1\n$2');

  const match = source.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match || /^index_img:/m.test(match[1])) return source;

  const frontMatter = match[1];
  const categoriesMatch = frontMatter.match(/^categories:\n(?:\s+-\s*.+\n?)+/m);
  const line = `index_img: ${yamlString(cover)}`;
  const nextFrontMatter = categoriesMatch
    ? frontMatter.replace(categoriesMatch[0], `${categoriesMatch[0].replace(/\n?$/, '\n')}${line}\n`)
    : `${frontMatter}\n${line}`;

  return source.replace(match[0], `---\n${nextFrontMatter}\n---\n`);
}

async function main() {
  const coverMap = JSON.parse(await fs.readFile(coversPath, 'utf8'));
  const files = (await fs.readdir(postsDir)).filter((file) => file.endsWith('.md'));
  let updated = 0;

  for (const file of files) {
    const filePath = path.join(postsDir, file);
    const source = await fs.readFile(filePath, 'utf8');
    const frontMatter = source.match(/^---\n([\s\S]*?)\n---/)?.[1] || '';
    const category = firstCategory(frontMatter);
    const cover = coverMap[category] || coverMap.default;
    const nextSource = addIndexImage(source, cover);

    if (nextSource !== source) {
      await fs.writeFile(filePath, nextSource, 'utf8');
      updated += 1;
    }
  }

  console.log(`Applied category covers to ${updated} posts.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
