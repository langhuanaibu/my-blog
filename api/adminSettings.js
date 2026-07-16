const {
  setCors,
  sendJson,
  createHttpError,
  requireAdmin,
  readJsonBody,
  readTextFile,
  putTextFilesAtomic
} = require('./_github');

const SITE_CONFIG = '_config.yml';
const FLUID_CONFIG = '_config.fluid.yml';
const NAV_KEYS = ['home', 'archive', 'category', 'about', 'links', 'guestbook'];

function yamlString(value) {
  return JSON.stringify(String(value ?? ''));
}

function yamlInlineHtml(value) {
  return yamlString(`<span>${String(value ?? '').trim()}</span>`);
}

function unquote(value) {
  return String(value || '').trim().replace(/^['"]|['"]$/g, '');
}

function readTopLevelBlock(source, blockName) {
  const startMatch = new RegExp(`^${blockName}:\\n`, 'm').exec(source);
  if (!startMatch) return '';

  const start = startMatch.index + startMatch[0].length;
  const rest = source.slice(start);
  const nextBlock = rest.search(/^\S/m);
  return nextBlock === -1 ? rest : rest.slice(0, nextBlock);
}

function readScalar(source, key) {
  const match = source.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
  return match ? unquote(match[1]) : '';
}

function readNestedScalar(source, blockName, key) {
  const block = readTopLevelBlock(source, blockName);
  const match = block.match(new RegExp(`^\\s+${key}:\\s*(.+)$`, 'm'));
  return match ? unquote(match[1]) : '';
}

function readSlogan(source) {
  const match = source.match(/^index:\n[\s\S]*?^\s{2}slogan:\n[\s\S]*?^\s{4}text:\s*(.+)$/m);
  return match ? unquote(match[1]) : '';
}

function readFooter(source) {
  const raw = readNestedScalar(source, 'footer', 'content');
  const htmlMatch = raw.match(/^<span>([\s\S]*)<\/span>$/);
  return htmlMatch ? htmlMatch[1] : raw;
}

function readNav(source) {
  const nav = {};
  for (const key of NAV_KEYS) {
    const pattern = new RegExp(`\\{ key: "${key}", name: "([^"]*)"`);
    nav[key] = source.match(pattern)?.[1] || '';
  }
  return nav;
}

function setRootScalar(source, key, value) {
  const line = `${key}: ${yamlString(value)}`;
  const pattern = new RegExp(`^${key}:\\s*.*$`, 'm');
  if (!pattern.test(source)) {
    throw createHttpError(400, `Missing config key: ${key}`);
  }
  return source.replace(pattern, () => line);
}

function setAboutScalar(source, key, value) {
  const pattern = new RegExp(`^(\\s{2}${key}:\\s*).*$`, 'm');
  if (!pattern.test(source)) {
    throw createHttpError(400, `Missing about key: ${key}`);
  }
  return source.replace(pattern, (_, prefix) => prefix + yamlString(value));
}

function setSlogan(source, value) {
  const pattern = /^(index:\n[\s\S]*?^\s{2}slogan:\n[\s\S]*?^\s{4}text:\s*).*$/m;
  if (!pattern.test(source)) {
    throw createHttpError(400, 'Missing index slogan text');
  }
  return source.replace(pattern, (_, prefix) => prefix + yamlString(value));
}

function setFooter(source, value) {
  const pattern = /^(\s{2}content:\s*).*$/m;
  if (!pattern.test(source)) {
    throw createHttpError(400, 'Missing footer content');
  }
  return source.replace(pattern, (_, prefix) => prefix + yamlInlineHtml(value));
}

function setNav(source, nav) {
  let next = source;
  for (const key of NAV_KEYS) {
    if (!Object.prototype.hasOwnProperty.call(nav || {}, key)) continue;
    const pattern = new RegExp(`(- \\{ key: "${key}", name: )"[^"]*"`);
    if (!pattern.test(next)) {
      throw createHttpError(400, `Missing nav item: ${key}`);
    }
    next = next.replace(pattern, (_, prefix) => prefix + yamlString(nav[key]));
  }
  return next;
}

function extractSettings(siteConfig, fluidConfig) {
  return {
    title: readScalar(siteConfig, 'title'),
    subtitle: readScalar(siteConfig, 'subtitle'),
    slogan: readSlogan(fluidConfig),
    footerText: readFooter(fluidConfig),
    aboutName: readNestedScalar(fluidConfig, 'about', 'name'),
    aboutIntro: readNestedScalar(fluidConfig, 'about', 'intro'),
    nav: readNav(fluidConfig)
  };
}

function applySettings(siteConfig, fluidConfig, settings) {
  const safe = settings || {};
  let nextSite = siteConfig;
  let nextFluid = fluidConfig;

  if (Object.prototype.hasOwnProperty.call(safe, 'title')) {
    nextSite = setRootScalar(nextSite, 'title', safe.title);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'subtitle')) {
    nextSite = setRootScalar(nextSite, 'subtitle', safe.subtitle);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'slogan')) {
    nextFluid = setSlogan(nextFluid, safe.slogan);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'footerText')) {
    nextFluid = setFooter(nextFluid, safe.footerText);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'aboutName')) {
    nextFluid = setAboutScalar(nextFluid, 'name', safe.aboutName);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'aboutIntro')) {
    nextFluid = setAboutScalar(nextFluid, 'intro', safe.aboutIntro);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'nav')) {
    nextFluid = setNav(nextFluid, safe.nav);
  }

  return { siteConfig: nextSite, fluidConfig: nextFluid };
}

async function handler(req, res) {
  setCors(res);

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    requireAdmin(req);

    const siteFile = await readTextFile(SITE_CONFIG);
    const fluidFile = await readTextFile(FLUID_CONFIG);

    if (req.method === 'GET') {
      return sendJson(res, 200, {
        success: true,
        data: extractSettings(siteFile.content, fluidFile.content)
      });
    }

    if (req.method === 'POST') {
      const body = await readJsonBody(req);
      const next = applySettings(siteFile.content, fluidFile.content, body.settings || {});

      const files = [];
      if (next.siteConfig !== siteFile.content) files.push({ path: SITE_CONFIG, content: next.siteConfig });
      if (next.fluidConfig !== fluidFile.content) files.push({ path: FLUID_CONFIG, content: next.fluidConfig });
      await putTextFilesAtomic(files, 'update site settings', {
        expectedFiles: [
          { path: SITE_CONFIG, sha: siteFile.sha },
          { path: FLUID_CONFIG, sha: fluidFile.sha }
        ]
      });

      return sendJson(res, 200, {
        success: true,
        data: extractSettings(next.siteConfig, next.fluidConfig)
      });
    }

    return sendJson(res, 405, { success: false, error: 'Method not allowed' });
  } catch (error) {
    return sendJson(res, error.status || 500, {
      success: false,
      error: error.message || 'Request failed'
    });
  }
}

handler._test = {
  extractSettings,
  applySettings,
  NAV_KEYS
};

module.exports = handler;
