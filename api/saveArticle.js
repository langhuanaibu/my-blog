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

    if (req.method !== 'POST') {
        return res.status(405).json({ success: false, error: 'Method not allowed' });
    }

    const { article } = req.body;
    
    if (!article || !article.id) {
        return res.status(400).json({ success: false, error: 'Invalid article data' });
    }

    // 简单的安全校验：这里应该有一个你的私有 Token 验证，防止别人乱发文章
    const token = req.headers.authorization;
    if (token !== `Bearer ${process.env.ADMIN_TOKEN}`) {
        return res.status(401).json({ success: false, error: 'Unauthorized' });
    }

    try {
        const { db } = await connectToDatabase();
        
        // 使用 upsert: 如果存在则更新，不存在则插入
        await db.collection('articles').updateOne(
            { id: article.id },
            { $set: article },
            { upsert: true }
        );
        
        res.status(200).json({ success: true, message: 'Article saved successfully' });
    } catch (error) {
        console.error('Database Error:', error);
        res.status(500).json({ success: false, error: 'Failed to save article' });
    }
};