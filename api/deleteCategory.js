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

    const { name } = req.body;
    
    if (!name) {
        return res.status(400).json({ success: false, error: 'Invalid category name' });
    }

    const token = req.headers.authorization;
    if (token !== `Bearer ${process.env.ADMIN_TOKEN}`) {
        return res.status(401).json({ success: false, error: 'Unauthorized' });
    }

    try {
        const { db } = await connectToDatabase();
        
        // 删除栏目
        await db.collection('categories').deleteOne({ name: name });
        
        // 更新该栏目下的所有文章，将分类改为“未分类”
        await db.collection('articles').updateMany(
            { category: name },
            { $set: { category: '未分类' } }
        );
        
        res.status(200).json({ success: true, message: 'Category deleted and articles updated' });
    } catch (error) {
        console.error('Database Error:', error);
        res.status(500).json({ success: false, error: 'Failed to delete category' });
    }
};
