const { connectToDatabase } = require('./_db');

module.exports = async (req, res) => {
    // 允许跨域请求
    res.setHeader('Access-Control-Allow-Credentials', true);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization');

    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }

    try {
        const { db } = await connectToDatabase();
        let categories = await db.collection('categories').find({}).toArray();

        // 初始化默认栏目
        if (categories.length === 0) {
            const defaults = [
                { name: '技术学习', icon: '📚', desc: '记录自己的一些技术栈', id: 'cat_1' },
                { name: '数据结构与算法', icon: '🧠', desc: '修炼内功，提升算法思维', id: 'cat_2' },
                { name: '随笔', icon: '📝', desc: '日常感悟与折腾记录', id: 'cat_3' }
            ];
            await db.collection('categories').insertMany(defaults);
            categories = defaults;
        }

        res.status(200).json({ success: true, data: categories });
    } catch (error) {
        console.error('获取栏目失败:', error);
        res.status(500).json({ success: false, error: 'Failed to fetch categories' });
    }
};
