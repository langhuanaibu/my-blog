const fs = require('fs');

async function migrate() {
    // 获取命令行传入的 token
    const token = process.argv[2];
    
    if (!token) {
        console.error('请提供你在 Vercel 中设置的 ADMIN_TOKEN！\n用法: node migrate.js <你的ADMIN_TOKEN>');
        process.exit(1);
    }

    try {
        console.log('开始读取本地 articles.json...');
        const data = fs.readFileSync('./articles.json', 'utf-8');
        const articles = JSON.parse(data);
        console.log(`共读取到 ${articles.length} 篇文章。`);

        let successCount = 0;
        let failCount = 0;

        for (const article of articles) {
            console.log(`正在上传文章: ${article.title}...`);
            const response = await fetch('https://my-blog-sable-omega.vercel.app/api/saveArticle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ article })
            });

            const result = await response.json();
            if (result.success) {
                console.log(`✅ 上传成功: ${article.title}`);
                successCount++;
            } else {
                console.error(`❌ 上传失败: ${article.title}, 错误: ${result.error}`);
                failCount++;
            }
        }

        console.log(`\n迁移完成！成功: ${successCount} 篇，失败: ${failCount} 篇。`);
        if (failCount === 0) {
            console.log('所有数据均已安全导入 MongoDB！你可以随时通过 Vercel API 获取了。');
        }

    } catch (err) {
        console.error('迁移过程中发生错误:', err);
    }
}

migrate();