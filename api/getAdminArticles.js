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

    // 简单的安全校验：这里应该有一个你的私有 Token 验证，防止别人拉取草稿
    const token = req.headers.authorization;
    if (token !== `Bearer ${process.env.ADMIN_TOKEN}`) {
        return res.status(401).json({ success: false, error: 'Unauthorized' });
    }

    try {
        const { db } = await connectToDatabase();
        // 获取所有的文章（包括草稿）
        const articles = await db.collection('articles').find({}).sort({ date: -1 }).toArray();
        
        res.status(200).json({ success: true, data: articles });
    } catch (error) {
        console.error('Database Error:', error);
        res.status(500).json({ success: false, error: 'Failed to fetch admin articles' });
    }
};
