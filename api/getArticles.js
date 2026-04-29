const { connectToDatabase } = require('./_db');

const PUBLIC_CACHE = 'public, s-maxage=60, stale-while-revalidate=300';

function stripContent(content = '') {
    return String(content)
        .replace(/<script[\s\S]*?<\/script>/gi, '')
        .replace(/<style[\s\S]*?<\/style>/gi, '')
        .replace(/<[^>]+>/g, ' ')
        .replace(/!\[[^\]]*]\([^)]*\)/g, ' ')
        .replace(/\[[^\]]+]\([^)]*\)/g, ' ')
        .replace(/[`*_#>\-]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function toArticleSummary(article) {
    const contentText = stripContent(article.content || '');
    const excerpt = contentText.length > 120 ? `${contentText.slice(0, 120)}...` : contentText;

    return {
        id: article.id,
        title: article.title,
        date: article.date,
        category: article.category,
        modifyDate: article.modifyDate,
        excerpt,
        readTime: Math.ceil(contentText.length / 300) || 1
    };
}

module.exports = async (req, res) => {
    res.setHeader('Access-Control-Allow-Credentials', true);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
    res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization');

    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }

    try {
        const { db } = await connectToDatabase();
        res.setHeader('Cache-Control', PUBLIC_CACHE);

        const view = req.query && req.query.view ? String(req.query.view) : 'full';

        if (view === 'detail') {
            const id = req.query && req.query.id ? String(req.query.id) : '';
            if (!id) {
                return res.status(400).json({ success: false, error: 'Missing article id' });
            }

            const article = await db.collection('articles').findOne({ id, isDraft: { $ne: true } });
            if (!article) {
                return res.status(404).json({ success: false, error: 'Article not found' });
            }

            return res.status(200).json({ success: true, data: article });
        }

        const limit = req.query && req.query.limit ? parseInt(req.query.limit, 10) : 0;

        let query = db.collection('articles').find({ isDraft: { $ne: true } }).sort({ date: -1 });
        if (limit > 0) {
            query = query.limit(limit);
        }

        const articles = await query.toArray();
        if (view === 'list') {
            return res.status(200).json({ success: true, data: articles.map(toArticleSummary) });
        }

        res.status(200).json({ success: true, data: articles });
    } catch (error) {
        console.error('Database Error:', error);
        res.status(500).json({ success: false, error: 'Failed to fetch articles' });
    }
};
