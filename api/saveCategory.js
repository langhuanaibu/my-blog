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

    const { category } = req.body;
    
    if (!category || !category.name) {
        return res.status(400).json({ success: false, error: 'Invalid category data' });
    }

    const token = req.headers.authorization;
    if (token !== `Bearer ${process.env.ADMIN_TOKEN}`) {
        return res.status(401).json({ success: false, error: 'Unauthorized' });
    }

    try {
        const { db } = await connectToDatabase();
        
        // 使用 upsert: 如果存在则更新，不存在则插入
        await db.collection('categories').updateOne(
            { name: category.name },
            { $set: category },
            { upsert: true }
        );
        
        res.status(200).json({ success: true, message: 'Category saved successfully' });
    } catch (error) {
        console.error('Database Error:', error);
        res.status(500).json({ success: false, error: 'Failed to save category' });
    }
};
