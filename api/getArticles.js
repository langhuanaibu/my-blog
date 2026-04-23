const { connectToDatabase } = require('./_db');

module.exports = async (req, res) => {
    // 允许跨域请求
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
        
        // 解析可选的 limit 参数
        const limit = req.query && req.query.limit ? parseInt(req.query.limit, 10) : 0;
        
        // 获取所有的已发布文章（排除草稿）
        let query = db.collection('articles').find({ isDraft: { $ne: true } }).sort({ date: -1 });
        if (limit > 0) {
            query = query.limit(limit);
        }
        
        const articles = await query.toArray();
        
        res.status(200).json({ success: true, data: articles });
    } catch (error) {
        console.error('Database Error:', error);
        res.status(500).json({ success: false, error: 'Failed to fetch articles' });
    }
};