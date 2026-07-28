const {
  setCors,
  sendJson,
  requireAdmin,
  readJsonBody,
  putBase64File,
  slugify,
  timestamp
} = require('./_github');

const ALLOWED_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'webp', 'gif']);
const MAX_BYTES = 8 * 1024 * 1024;

function matchesImageSignature(buffer, extension) {
  if (extension === 'png') {
    return buffer.subarray(0, 8).equals(Buffer.from([
      0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a
    ]));
  }
  if (extension === 'jpg' || extension === 'jpeg') {
    return buffer.length >= 3
      && buffer[0] === 0xff
      && buffer[1] === 0xd8
      && buffer[2] === 0xff;
  }
  if (extension === 'gif') {
    const signature = buffer.subarray(0, 6).toString('ascii');
    return signature === 'GIF87a' || signature === 'GIF89a';
  }
  if (extension === 'webp') {
    return buffer.subarray(0, 4).toString('ascii') === 'RIFF'
      && buffer.subarray(8, 12).toString('ascii') === 'WEBP';
  }
  return false;
}

function parseUpload(body) {
  const dataUrl = String(body.dataUrl || '');
  const contentBase64 = String(body.contentBase64 || '');
  const fileName = String(body.fileName || 'image').trim();
  const purpose = body.purpose === 'cover' ? 'cover' : 'content';
  let base64 = contentBase64;
  let extension = fileName.split('.').pop()?.toLowerCase() || '';

  if (dataUrl) {
    const match = dataUrl.match(/^data:image\/([a-z0-9.+-]+);base64,(.+)$/i);
    if (!match) throw new Error('Invalid image data');
    extension = match[1].replace('jpeg', 'jpg').replace('svg+xml', 'svg');
    base64 = match[2];
  }

  if (!ALLOWED_EXTENSIONS.has(extension)) {
    throw new Error('Unsupported image type');
  }

  const buffer = Buffer.from(base64, 'base64');
  if (!buffer.length || buffer.length > MAX_BYTES) {
    throw new Error('Image is empty or too large');
  }
  if (!matchesImageSignature(buffer, extension)) {
    throw new Error('Image content does not match its file type');
  }

  return {
    base64: buffer.toString('base64'),
    extension,
    purpose,
    originalName: fileName
  };
}

function destination(upload) {
  const stamp = timestamp();
  const baseName = upload.originalName.replace(/\.[^.]+$/, '');
  const safeName = slugify(baseName, 'image');

  if (upload.purpose === 'cover') {
    return `source/images/covers/custom/${stamp}-${safeName}.${upload.extension}`;
  }

  const year = stamp.slice(0, 4);
  const month = stamp.slice(4, 6);
  return `source/images/uploads/${year}/${month}/${stamp}-${safeName}.${upload.extension}`;
}

module.exports = async (req, res) => {
  setCors(res);

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return sendJson(res, 405, { success: false, error: 'Method not allowed' });
  }

  try {
    requireAdmin(req);
    const body = await readJsonBody(req);
    const upload = parseUpload(body);
    const filePath = destination(upload);
    await putBase64File(filePath, upload.base64, `upload image: ${filePath.split('/').pop()}`);

    return sendJson(res, 200, {
      success: true,
      data: {
        path: filePath,
        url: `/${filePath.replace(/^source\//, '')}`
      }
    });
  } catch (error) {
    return sendJson(res, error.status || 400, {
      success: false,
      error: error.message || 'Upload failed'
    });
  }
};
