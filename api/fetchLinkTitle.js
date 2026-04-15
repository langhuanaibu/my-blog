function decodeHtmlEntities(text) {
    return String(text || '')
        .replace(/&amp;/gi, '&')
        .replace(/&lt;/gi, '<')
        .replace(/&gt;/gi, '>')
        .replace(/&quot;/gi, '"')
        .replace(/&#39;/gi, "'")
        .replace(/&#x27;/gi, "'")
        .replace(/&nbsp;/gi, ' ');
}

function extractMetaContent(html, pattern) {
    const match = html.match(pattern);
    return match ? decodeHtmlEntities(match[1].trim()) : '';
}

module.exports = async (req, res) => {
    res.setHeader('Access-Control-Allow-Credentials', true);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }

    if (req.method !== 'GET') {
        return res.status(405).json({ success: false, error: 'Method not allowed' });
    }

    try {
        const rawUrl = req.query?.url;
        if (!rawUrl) {
            return res.status(400).json({ success: false, error: 'Missing url parameter' });
        }

        const targetUrl = new URL(rawUrl);
        if (!['http:', 'https:'].includes(targetUrl.protocol)) {
            return res.status(400).json({ success: false, error: 'Only http and https URLs are supported' });
        }

        const response = await fetch(targetUrl.toString(), {
            method: 'GET',
            redirect: 'follow',
            headers: {
                'User-Agent': 'Mozilla/5.0 (compatible; AoiblogLinkBot/1.0; +https://aoiblog.top)',
                'Accept': 'text/html,application/xhtml+xml'
            }
        });

        if (!response.ok) {
            return res.status(502).json({ success: false, error: `Failed to fetch target page: ${response.status}` });
        }

        const html = await response.text();
        const title =
            extractMetaContent(html, /<meta[^>]+property=["']og:title["'][^>]+content=["']([\s\S]*?)["'][^>]*>/i) ||
            extractMetaContent(html, /<meta[^>]+name=["']twitter:title["'][^>]+content=["']([\s\S]*?)["'][^>]*>/i) ||
            extractMetaContent(html, /<title[^>]*>([\s\S]*?)<\/title>/i);

        return res.status(200).json({
            success: true,
            url: targetUrl.toString(),
            title: title || targetUrl.hostname
        });
    } catch (error) {
        return res.status(500).json({
            success: false,
            error: 'Failed to extract page title'
        });
    }
};
