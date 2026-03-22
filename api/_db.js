const { MongoClient } = require('mongodb');
require('dotenv').config();

// 复用数据库连接池
let cachedClient = null;
let cachedDb = null;

async function connectToDatabase() {
    if (cachedClient && cachedDb) {
        return { client: cachedClient, db: cachedDb };
    }

    const uri = process.env.MONGODB_URI;
    if (!uri) {
        throw new Error('Please define the MONGODB_URI environment variable inside .env');
    }

    const client = new MongoClient(uri);
    await client.connect();
    
    // 使用你 Twikoo 同一个数据库或者新建一个，这里假设用默认的 test 数据库
    const db = client.db('my_blog_db');

    cachedClient = client;
    cachedDb = db;

    return { client, db };
}

module.exports = { connectToDatabase };