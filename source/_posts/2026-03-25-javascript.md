---
title: "Javascript"
date: "2026-03-25"
updated: "2026-05-08"
categories:
  - "技术学习"
old_id: "article_1774454087284"
twikooPath: "article_1774454087284"
---
<h2>Javascript</h2>
# Javascript

2026年3月25日23:55:50
发这篇文章的时候发现让哈基米修博客的时候越修越错，前前后后在MongoDB和vercel里掰扯了半个小时，又跟哈基米掰扯了半个多小时，真的心累……
不知道是不是哈基米能力太差了，但我现在也没有很多米，也不想订claude和gpt来用他们的api
将就着用吧……
事实证明用ai的人还是一定要懂技术和会写代码，不然就是瞎用

**1.字符串**

```javascript
//一、字符串的创建方式
// 字面量方式（推荐）
let str1 = "Hello";
let str2 = 'World';
let str3 = `Template`; // 模板字符串（ES6）

// 二、字符串的基本属性与访问
// 1. .length：获取字符串长度
let text = "JavaScript";
console.log(text.length); // 10

// 2. 通过索引访问字符（只读）
let s = "ABC";
console.log(s[0]);      // "A"
console.log(s.charAt(1)); // "B"（等价于 s[1]）

// 注意：字符串是不可变的！
s[0] = "X"; // ❌ 无效，不会报错但也不会改变原字符串
console.log(s); // 仍是 "ABC"

// 三、常用字符串操作方法（重点！）
// ✅ 1. 查找类方法
// | 方法 | 说明 |
// |------|------|
// | `.indexOf(search, fromIndex)` | 返回首次出现位置，未找到返回 `-1` |
// | `.lastIndexOf(search)` | 从后往前查找 |
// | `.includes(search)` | 是否包含（返回布尔值，ES6） |
// | `.startsWith(prefix)` | 是否以某字符串开头（ES6） |
// | `.endsWith(suffix)` | 是否以某字符串结尾（ES6） |

let sentence = "The quick brown fox jumps over the lazy dog";

console.log(sentence.indexOf("fox"));        // 16
console.log(sentence.indexOf("cat"));        // -1
console.log(sentence.includes("brown"));     // true
console.log(sentence.startsWith("The"));     // true
console.log(sentence.endsWith("dog"));       // true

// ✅ 2. 截取/提取类方法
// | 方法 | 说明 |
// |------|------|
// | `.slice(start, end)` | 提取子串（不包含 end），支持负数 |
// | `.substring(start, end)` | 类似 slice，但不支持负数，且自动交换参数大小 |
// | `.substr(start, length)` | 已废弃！用 `slice` 替代 |

let str = "Hello World";

console.log(str.slice(0, 5));     // "Hello"
console.log(str.slice(-5));       // "World"（从倒数第5位到末尾）
console.log(str.substring(6, 11)); // "World"
console.log(str.substring(11, 6)); // "World"（自动调换顺序）

// 推荐始终使用 slice！

// ✅ 3. 替换类方法
// | 方法 | 说明 |
// |------|------|
// | `.replace(search, replaceValue)` | 只替换第一个匹配项 |
// | `.replaceAll(search, replaceValue)` | 替换所有匹配项（ES2021） |
// | 支持正则表达式（强大！） |

let text = "apple, banana, apple";

// 替换第一个
console.log(text.replace("apple", "orange"));
// → "orange, banana, apple"

// 替换全部（方法1：用 replaceAll）
console.log(text.replaceAll("apple", "orange"));
// → "orange, banana, orange"

// 替换全部（方法2：用正则 + g 标志）
console.log(text.replace(/apple/g, "orange"));
// → "orange, banana, orange"

// 忽略大小写替换
console.log("Hello HELLO".replace(/hello/gi, "Hi"));
// → "Hi Hi"

// ✅ 4. 大小写转换
let str = "JavaScript";

console.log(str.toUpperCase()); // "JAVASCRIPT"
console.log(str.toLowerCase()); // "javascript"

// ✅ 5. 去除空白字符
// | 方法 | 说明 |
// |------|------|
// | `.trim()` | 去除首尾空白 |
// | `.trimStart()` / `.trimLeft()` | 去除开头空白（ES2019） |
// | `.trimEnd()` / `.trimRight()` | 去除结尾空白（ES2019） |
let dirty = "   \t  Hello World!  \n  ";
console.log("[" + dirty.trim() + "]");      // "[Hello World!]"
console.log("[" + dirty.trimStart() + "]"); // "[Hello World!  \n  ]"

// ✅ 6. 分割与连接
// | 方法 | 说明 |
// |------|------|
// | `.split(separator)` | 按分隔符拆分为数组 |
// | `.join(separator)` | 数组 → 字符串（Array 的方法） |

let csv = "apple,banana,orange";
let fruits = csv.split(",");
console.log(fruits); // ["apple", "banana", "orange"]

let backToString = fruits.join(" | ");
console.log(backToString); // "apple | banana | orange"

// 拆成单个字符
console.log("ABC".split("")); // ["A", "B", "C"]

// ✅ 7. 填充与重复（ES2015+）
// | 方法 | 说明 |
// |------|------|
// | `.padStart(targetLength, padString)` | 从开头填充 |
// | `.padEnd(targetLength, padString)` | 从末尾填充 |
// | `.repeat(count)` | 重复字符串 |

// 数字补零（常用于时间、序号格式化）
console.log("5".padStart(3, "0"));   // "005"
console.log("12".padStart(5, "*"));  // "***12"

// 重复
console.log("Ha".repeat(3)); // "HaHaHa"

// 四、模板字面量（Template Literals）— ES6 重磅特性！
// 使用反引号  ... ，支持：
// 多行字符串
// 嵌入变量/表达式  $ {}

let name = "小明";
let age = 20;

// 传统拼接（繁琐易错）
let oldWay = "我叫" + name + "，今年" + age + "岁。";

// 模板字面量（简洁清晰）
let newWay = `我叫${name}，今年${age}岁。`;

// 多行
let html = `
  <div>
    <h1>欢迎，${name}！</h1>
    <p>年龄：${age}</p>
  </div>
`;

// 嵌入表达式
let price = 100;
let tax = 0.1;
console.log(`总价：${(price * (1 + tax)).toFixed(2)} 元`);
// → "总价：110.00 元"

// 五、字符串编码与转义
// 常见转义字符：
// \n：换行
// \t：制表符
// \" 或 \'：引号
// \\：反斜杠
```

2026年3月26日10:18:51
**2.数组**

```javascript
// 二、如何创建数组？
// ✅ 1. 数组字面量（推荐）
let fruits = ["苹果", "香蕉", "橙子"];
let mixed = [1, "hello", true, null, { name: "JS" }];

// 三、访问与修改数组元素
let colors = ["红", "绿", "蓝"];

console.log(colors[0]);     // "红"
console.log(colors.length); // 3

// 修改元素
colors[1] = "黄";
console.log(colors); // ["红", "黄", "蓝"]

// 添加新元素（不推荐直接用索引）
colors[3] = "紫"; // 可以，但容易出错

//数组是可变的

// 四、判断是否为数组
// 不要用 typeof（它返回 "object"）！
// ✅ 正确方式：
let arr = [1, 2, 3];
console.log(Array.isArray(arr)); // true ✅

// 五、数组的常用方法（重点！）
// 📌 1. 栈方法（LIFO：后进先出）
// | 方法 | 作用 | 返回值 |
// | `.push(item)` | 末尾添加一个/多个元素 | 新长度 |
// | `.pop()` | 删除并返回最后一个元素 | 被删元素 |
let stack = [1, 2];
stack.push(3, 4);      // [1, 2, 3, 4]
let last = stack.pop(); // last = 4, stack = [1, 2, 3]

// 📌 2. 队列方法（FIFO：先进先出）
// | 方法 | 作用 | 返回值 |
// | `.shift()` | 删除并返回第一个元素 | 被删元素 |
// | `.unshift(item)` | 开头添加一个/多个元素 | 新长度 |
let queue = [1, 2, 3];
queue.unshift(0);       // [0, 1, 2, 3]
let first = queue.shift(); // first = 0, queue = [1, 2, 3]

// 📌 3. 连接与转换
// | 方法 | 说明 |
// | `.join(separator)` | 将数组转为字符串，默认用 `,` 连接 |
// | `.toString()` | 等价于 `.join(",")` |
// | `.concat(arr2)` | 合并数组，不修改原数组，返回新数组 |
let letters = ["a", "b", "c"];
console.log(letters.join("-")); // "a-b-c"

let nums1 = [1, 2];
let nums2 = [3, 4];
let combined = nums1.concat(nums2); // [1, 2, 3, 4]
console.log(nums1); // [1, 2]（原数组不变）

// 📌 4. 截取与拼接
// | 方法 | 说明 |
// | `.slice(start, end)` | 提取子数组（不包含 end），不修改原数组 |
// | `.splice(start, deleteCount, ...items)` | 从 start 开始删除 deleteCount 个，并插入 items，会修改原数组 |
let arr = [1, 2, 3, 4, 5];

// slice：安全提取
let part = arr.slice(1, 3); // [2, 3]
console.log(arr); // [1, 2, 3, 4, 5]（不变）

// splice：强力编辑
arr.splice(2, 2, "x", "y"); // 从索引2开始删2个，插入"x","y"
console.log(arr); // [1, 2, "x", "y", 5]

// 📌 5. 查找与判断
// | 方法 | 说明 |
// | `.indexOf(item)` | 返回首次出现的索引，未找到返回 `-1` |
// | `.lastIndexOf(item)` | 从后往前找 |
// | `.includes(item)` | 是否包含（返回布尔值，ES2016） |
// | `.find(fn)` | 返回第一个满足条件的元素 |
// | `.findIndex(fn)` | 返回第一个满足条件的元素的索引 |
let scores = [85, 92, 78, 96];

console.log(scores.includes(92)); // true
console.log(scores.indexOf(78));  // 2

// 找出第一个大于90的分数
let highScore = scores.find(score => score > 90);
console.log(highScore); // 92

// 找出它的位置
let index = scores.findIndex(score => score > 90);
console.log(index); // 1

// 📌 6. 遍历数组（不修改原数组）
// | 方法 | 说明 |
// | `.forEach(fn)` | 遍历每个元素（无返回值） |
// | `.map(fn)` | 对每个元素调用函数，返回新数组 |
// | `.filter(fn)` | 筛选出满足条件的元素，返回新数组 |
// | `.reduce(fn, init)` | 累积计算，常用于求和、扁平化等 |
let numbers = [1, 2, 3, 4, 5];

// 每个数乘2
let doubled = numbers.map(n => n * 2);
console.log(doubled); // [2, 4, 6, 8, 10]

// 只保留偶数
let evens = numbers.filter(n => n % 2 === 0);
console.log(evens); // [2, 4]

let sum = numbers.reduce((total, current) => total + current, 0);
console.log(sum); // 15

// 📌 7. 排序与反转
// | 方法 | 说明 |
// | `.reverse()` | 颠倒数组顺序（修改原数组） |
// | `.sort([compareFn])` | 排序（修改原数组） |
// ⚠️ 注意：.sort() 默认按字符串 Unicode 编码排序！

let nums = [10, 5, 40, 25];

// 错误排序（按字符串排）
console.log(nums.sort()); // [10, 25, 40, 5] ❌

// 正确排序（传入比较函数）
nums.sort((a, b) => a - b); // 升序
console.log(nums); // [5, 10, 25, 40] ✅

// 降序
nums.sort((a, b) => b - a);

// 七、实战小例子
// 1. 去重（使用 Set）

let dup = [1, 2, 2, 3, 3, 3];
let unique = [...new Set(dup)];
console.log(unique); // [1, 2, 3]
```

**3.函数**

```javascript
二、函数的定义方式
✅ 1. 函数声明（Function Declaration）

function greet(name) {
  return "你好，" + name + "！";
}

console.log(greet("小明")); // "你好，小明！"

✅ 特点：函数提升（Hoisting） —— 可以在声明前调用。

sayHello(); // ✅ 正常执行（因为函数声明被提升了）
function sayHello() {
  console.log("Hello!");
}

✅ 2. 函数表达式（Function Expression）

const add = function(a, b) {
  return a + b;
};

console.log(add(3, 5)); // 8

⚠️ 注意：不会被提升！不能在声明前调用

// subtract(); // ❌ ReferenceError
const subtract = function(x, y) {
  return x - y;
};

✅ 3. 箭头函数（Arrow Function，ES6）
语法更简洁，没有自己的 this、arguments、super 或 new.target

1. 基本形式
(参数1, 参数2, ...) => { 函数体 }
箭头表示返回，若函数体为表达式，则自动作为返回值

2. 简化规则
| 情况 | 写法 | 示例 |
| 单个参数 | 可省略括号 | `x => x * 2` |
| 多个参数 | 必须加括号 | `(a, b) => a + b` |
| 函数体只有一行 return | 可省略 `{}` 和 `return` | `(a, b) => a + b` |
| 函数体有多行 | 必须用 `{}`，显式写 `return` | `(a, b) => { console.log(a); return a + b; }` |

(total, current) => total + current 等价于：
function(total, current) {
  return total + current;
}

// 基本形式
const multiply = (a, b) => a * b;

// 单参数可省略括号
const square = x => x * x;

// 多行语句需用 {}
const greet = name => {
  const msg = "欢迎，" + name;
  return msg;
};

console.log(multiply(4, 5)); // 20
console.log(square(3));      // 9
console.log(greet("小红"));   // "欢迎，小红"

📌 适用场景：简短的回调函数（如 map, filter）。

三、函数的参数（Parameters & Arguments）
1. 默认参数（ES6）

function power(base, exponent = 2) {
  return base ** exponent;
}

console.log(power(3));    // 9（exponent 默认为 2）
console.log(power(3, 3)); // 27

2. 剩余参数（Rest Parameters，ES6）
用 ... 收集多余参数为数组。

function sum(...numbers) {
  return numbers.reduce((total, n) => total + n, 0);
}

console.log(sum(1, 2, 3, 4)); // 10

四、返回值（Return）
使用 return 语句返回结果。
如果没有 return，函数默认返回 undefined。

五、作用域（Scope）与闭包（Closure）
1. 作用域
全局作用域：在函数外定义的变量。
函数作用域：在函数内定义的变量（var）。
块级作用域：在 {} 内用 let/const 定义的变量。

let globalVar = "全局";

function outer() {
  let localVar = "局部";
  if (true) {
    let blockVar = "块级";
    console.log(blockVar); // ✅
  }
  // console.log(blockVar); // ❌ 无法访问
}

2. 闭包（Closure）
内部函数可以访问外部函数的变量，即使外部函数已执行完毕。

function createCounter() {
  let count = 0;
  return function() {
    count++;
    return count;
  };
}

const counter = createCounter();
console.log(counter()); // 1
console.log(counter()); // 2
// count 变量被“封闭”在返回的函数中！

✅ 应用：模块模式、私有变量、防抖节流等。

六、高阶函数（Higher-Order Functions）
函数可以：
接收函数作为参数
返回一个函数
这是函数式编程的基础！
示例 1：接收函数作为参数

function operate(a, b, fn) {
  return fn(a, b);
}

const result = operate(4, 2, (x, y) => x / y);
console.log(result); // 2

示例 2：返回函数（柯里化）

function multiply(a) {
  return function(b) {
    return a * b;
  };
}

const double = multiply(2);
console.log(double(5)); // 10

🔥 数组方法如 .map(), .filter(), .reduce() 都是高阶函数！

[1, 2, 3].map(x => x * 2); // [2, 4, 6]

七、this 关键字（重要！）
普通函数中的 this 取决于调用方式。
箭头函数中的 this 继承自外层作用域。

const obj = {
  name: "小明",
  greetNormal: function() {
    console.log("普通函数:", this.name); // "小明"
  },
  greetArrow: () => {
    console.log("箭头函数:", this.name); // undefined（this 指向全局）
  }
};

obj.greetNormal(); // ✅
obj.greetArrow();  // ❌

✅ 规则：
方法用普通函数
回调用箭头函数（避免 this 丢失）

八、立即执行函数表达式（IIFE）
定义后立即调用，常用于创建私有作用域。

(function() {
  var privateVar = "我是私有的";
  console.log(privateVar);
})(); // "我是私有的"

// 外部无法访问 privateVar

ES6 后多用块级作用域替代，但 IIFE 在模块化中仍有价值。

九、实战小例子
1. 防抖函数（Debounce）

function debounce(fn, delay) {
  let timer;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

const handleInput = debounce(value => {
  console.log("搜索:", value);
}, 300);

2. 记忆化函数（缓存计算结果）
function memoize(fn) {
  const cache = new Map();
  return function(...args) {
    const key = JSON.stringify(args);
    if (cache.has(key)) {
      return cache.get(key);
    }
    const result = fn(...args);
    cache.set(key, result);
    return result;
  };
}

const fib = memoize(n => n <= 1 ? n : fib(n - 1) + fib(n - 2));
console.log(fib(10)); // 快速计算

✅ 推荐实践
在现代 JavaScript（ES6+）中，优先使用以下方式定义函数：

// 纯计算、工具函数 → 用箭头函数 + const
const add = (a, b) => a + b;
const isEven = n => n % 2 === 0;

// 需要函数名用于调试或递归 → 用命名函数表达式
const factorial = function calc(n) {
  return n <= 1 ? 1 : n * calc(n - 1);
};

// 对象方法、需要 this 的场景 → 用普通函数（或方法简写）
const obj = {
  name: "JS",
  greet() { // 等价于 greet: function() { ... }
    return `Hello, ${this.name}!`;
  }
};
```

**4.Date对象**

```javascript
一、创建 Date 对象
✅ 1. 当前时间（最常用）
const now = new Date();
console.log(now); // 如：2026-03-27T10:30:45.123Z（本地时区显示）

✅ 2. 指定日期时间（多种方式）
方式 B：传入数字参数（推荐！明确无歧义）

// new Date(year, monthIndex, day, hours, minutes, seconds, milliseconds)
// 注意：monthIndex 从 0 开始（0=January, 11=December）

const date1 = new Date(2026, 2, 27);        // 2026年3月27日（month=2 → 3月）
const date2 = new Date(2026, 2, 27, 14, 30); // 2026-03-27 14:30:00

方式 C：传入时间戳（毫秒）
const timestamp = 1711536645123;
const date3 = new Date(timestamp);

💡 获取当前时间戳：
Date.now(); // 返回毫秒数（推荐）
new Date().getTime(); // 等价

二、获取日期/时间信息（Getter 方法）
所有 getter 方法都基于本地时区（除非用 UTC 方法）。

.getFullYear()	年份（4位）	2026
.getMonth()	月份（0~11）	2（表示3月）⚠️
.getDate()	日期（1~31）	27
.getDay()	星期（0~6，0=周日）	4（周四）
.getHours()	小时（0~23）	14
.getMinutes()	分钟（0~59）	30
.getSeconds()	秒（0~59）	45
.getMilliseconds()	毫秒（0~999）	123
.getTime()	时间戳（毫秒）	1711536645123

🔁 UTC 版本（加 UTC 前缀）
date.getUTCFullYear(); // 获取 UTC 年份
date.getUTCHours();    // 获取 UTC 小时

三、设置日期/时间（Setter 方法）
.setFullYear(year, month?, day?)	设置年、月、日
.setMonth(month, day?)	设置月（0~11）、日
.setDate(day)	设置日期
.setHours(hours, min?, sec?, ms?)	设置时、分、秒、毫秒
.setTime(timestamp)	通过时间戳设置

const d = new Date(2026, 2, 27);
d.setFullYear(2027);        // 改为 2027-03-27
d.setMonth(3);              // 改为 2027-04-27（month=3 → 4月）
d.setDate(1);               // 改为 2027-04-01

⚠️ 注意：如果设置的值超出范围，会自动进位！

d.setDate(32); // 如果当前月只有31天，会变成下个月1号

四、日期计算与比较
✅ 1. 时间差（毫秒）
const start = new Date("2026-01-01");
const end = new Date("2026-03-27");
const diffMs = end - start; // 直接相减得到毫秒差

// 转换为天数
const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
console.log(diffDays); // 86 天

✅ 2. 比较日期

const d1 = new Date("2026-03-27");
const d2 = new Date("2026-04-01");

console.log(d1 < d2);  // true
console.log(d1 > d2);  // false

💡 日期对象可以直接用 <, >, == 比较（内部转为时间戳）。

五、日期格式化（重点！）

✅ 推荐方法 1：手动拼接（简单场景）

function formatDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0'); // 月份+1并补零
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

console.log(formatDate(new Date())); // "2026-03-27"

✅ 推荐方法 2：toLocaleDateString()（本地化）

const date = new Date("2026-03-27");

// 中文格式
console.log(date.toLocaleDateString('zh-CN'));
// "2026/3/27"

// 自定义选项
console.log(date.toLocaleDateString('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit'
})); // "2026/03/27"

✅ 推荐方法 3：toISOString()（ISO 8601 标准，常用于 API）

new Date().toISOString();
// "2026-03-27T02:30:45.123Z"（UTC 时间）

✅ 推荐方法 4：第三方库（复杂需求）
date-fns（轻量、函数式）
Day.js（轻量、Moment.js 替代）
Luxon（强大、时区支持好）
🌟 现代项目建议：不要自己造轮子，用 date-fns 或 Day.js！

六、常见陷阱与注意事项

⚠️ 1. 月份从 0 开始
new Date(2026, 3, 1); // 是 2026年**4月1日**，不是3月！

⚠️ 2. 日期字符串解析不一致
// 安全写法（ISO 8601）
new Date("2026-03-27");      // ✅ 一致
new Date("2026/03/27");      // ❌ Safari 可能报错
new Date("03/27/2026");      // ❌ 格式混乱

⚠️ 3. 时区问题
Date 对象内部存储的是 UTC 时间戳。
所有 getter/setter 默认使用本地时区。
跨时区应用务必明确使用 UTC 方法或第三方库。

⚠️ 4. 夏令时（DST）影响
在夏令时切换日，某些小时可能不存在或重复，导致计算偏差。

七、实战小例子
1. 判断是否是闰年

function isLeapYear(year) {
  return new Date(year, 1, 29).getDate() === 29;
}
console.log(isLeapYear(2024)); // true
console.log(isLeapYear(2025)); // false

2. 获取本月最后一天
function getLastDayOfMonth(year, month) {
  // 下个月的第0天就是本月最后一天
  return new Date(year, month, 0).getDate();
}
console.log(getLastDayOfMonth(2026, 2)); // 28（2026年2月）

3. 计算年龄
function getAge(birthDate) {
  const today = new Date();
  const birth = new Date(birthDate);
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
}
console.log(getAge("1990-05-15")); // 如：35
```

**5.this**
（1）this到底是什么？

```javascript
// 定义一个“修车”函数
function changeTire() {
  console.log("正在给 " + this.brand + " 换轮胎");
}

// 张三的车
const zhangsanCar = { brand: "BMW", fix: changeTire };

// 李四的车
const lisiCar = { brand: "Toyota", fix: changeTire };

// 谁调用，this 就是谁！
zhangsanCar.fix(); // 输出：正在给 BMW 换轮胎 → this = zhangsanCar
lisiCar.fix();     // 输出：正在给 Toyota 换轮胎 → this = lisiCar
```

✅ 看懂了吗？this 的值不是写函数时定的，而是调用函数那一刻才确定的！

❓ 那如果没人“拥有”这个函数呢？
changeTire(); // 没有通过对象调用
这时候：
非严格模式：this 会变成 全局对象（浏览器里就是 window）。
相当于“没人派活，你自己瞎修，修的是整个地球（window）”。
严格模式 ('use strict')：this 是 undefined。
相当于“没人派活，你不能乱修，报错！”
✅ 现代开发建议：永远不要依赖这种“裸调用”的 this，很容易出错！

🔧 this 到底有什么用？
它的核心作用就一个：让同一个函数能为不同的对象服务！
如果没有 this，你得为每辆车写一个专属修车函数：
function fixBMW() { ... }
function fixToyota() { ... }
function fixBenz() { ... }
// 太蠢了！
有了 this，一个函数搞定所有车！这就是代码复用，是面向对象编程的精髓。

⚠️ 常见坑：箭头函数没有自己的 this

```javascript
const car = {
  brand: "Tesla",
  report: function() {
    // 普通函数：this = car
    setTimeout(function() {
      // 普通回调函数：this = window (或 undefined)
      console.log(this.brand); // undefined!
    }, 1000);
  }
};
```

解决方案：用箭头函数（它会“继承”外层的 this）

```javascript
const car = {
  brand: "Tesla",
  report: function() {
    setTimeout(() => {
      // 箭头函数：this 继承自 report 函数 → this = car
      console.log(this.brand); // "Tesla" ✓
    }, 1000);
  }
};
```

✅ 记住：对象方法用普通函数，回调/工具函数用箭头函数。

📌 终极总结

![图片](https://www.aoiblog.top/images/img_1774665975804.png)

**6.事件**

![图片](https://www.aoiblog.top/images/img_1774684139264.png)

![图片](https://www.aoiblog.top/images/img_1774684152843.png)

![图片](https://www.aoiblog.top/images/img_1774684164022.png)

![图片](https://www.aoiblog.top/images/img_1774684171207.png)

![图片](https://www.aoiblog.top/images/img_1774684178801.png)

![图片](https://www.aoiblog.top/images/img_1774684185041.png)

![图片](https://www.aoiblog.top/images/img_1774684191234.png)

![图片](https://www.aoiblog.top/images/img_1774684197384.png)

![图片](https://www.aoiblog.top/images/img_1774684205144.png)

![图片](https://www.aoiblog.top/images/img_1774684211778.png)

![图片](https://www.aoiblog.top/images/img_1774684216949.png)

![图片](https://www.aoiblog.top/images/img_1774684225265.png)

![图片](https://www.aoiblog.top/images/img_1774684231865.png)

![图片](https://www.aoiblog.top/images/img_1774684236842.png)

![图片](https://www.aoiblog.top/images/img_1774684242181.png)

![图片](https://www.aoiblog.top/images/img_1774684246762.png)

**6.定时器**
🎯 一、定时器是什么？
简单说，定时器就是让 JavaScript “等一会儿再做某事” 或 “每隔一段时间就做某事” 的机制。
因为 JavaScript 是单线程的，它不能真正“暂停”，所以定时器是一种异步操作：你告诉浏览器“X 毫秒后帮我做 Y”，然后 JS 继续执行后面的代码，等时间到了，浏览器再把 Y 任务塞回执行队列。

⏱️ 二、两种核心定时器
JavaScript 提供了两个全局函数（其实是 window 对象的方法）：
1. setTimeout：延迟一次执行
作用：在指定的毫秒数后，执行一次某个函数。
语法：

```javascript
const timerId = setTimeout(callback, delay, arg1, arg2, ...);
```

callback：要执行的函数。
delay：延迟时间（毫秒）。注意：这是最小延迟，不是精确时间！
arg1, arg2...：可选，传递给 callback 的参数。
返回值：一个定时器 ID（数字），用于后续取消。
✅ 基础示例

```javascript
console.log('开始');

// 2秒后执行
const id = setTimeout(() => {
  console.log('2秒过去了！');
}, 2000);

console.log('结束'); // 这行会立刻打印
```

🛑 取消定时器：clearTimeout
如果你在定时器触发前改变了主意，可以用 clearTimeout 取消它。

```javascript
const id = setTimeout(() => {
  console.log('这条消息不会出现');
}, 5000);

// 在5秒内取消
clearTimeout(id);
```

2. setInterval：周期性重复执行
作用：每隔指定的毫秒数，重复执行某个函数。
语法：

```javascript
const timerId = setInterval(callback, interval, arg1, arg2, ...);
```

参数含义同 setTimeout。
返回值：定时器 ID，用于取消。

✅ 基础示例：每秒打印时间

```javascript
const id = setInterval(() => {
  console.log(new Date().toLocaleTimeString());
}, 1000);

// 5秒后停止
setTimeout(() => {
  clearInterval(id);
  console.log('定时器已停止');
}, 5000);
```

🛑 取消定时器：clearInterval
必须手动取消，否则它会一直执行下去（可能导致内存泄漏或性能问题）！

```javascript
const id = setInterval(() => { /* ... */ }, 1000);
clearInterval(id); // 停止
```

⚠️ 三、关键注意事项（非常重要！）
1. 定时器不是精确的！
浏览器的定时器受系统负载、标签页是否激活、浏览器节流策略影响。
最小延迟：
HTML5 规范规定，嵌套定时器（如 setTimeout 内部再调用 setTimeout）的最小延迟为 4ms。
未激活的标签页中，setTimeout/setInterval 的最小间隔可能被限制为 1000ms。
不要用定时器做高精度计时器（比如游戏帧同步），应该用 requestAnimationFrame。
2. this 的指向问题
在定时器的回调函数中，this 默认指向 全局对象（浏览器中是 window），而不是你期望的对象。

✅ 解决方案
使用箭头函数（推荐）：箭头函数没有自己的 this，会继承外层作用域。

```javascript
greet() {
  setTimeout(() => {
    console.log(this.name); // "MyObject" ✓
  }, 1000);
}
```

缓存 this：

```javascript
greet() {
  const self = this;
  setTimeout(function() {
    console.log(self.name); // "MyObject"
  }, 1000);
}
```

3. 不要忘记清理！
页面卸载（如跳转、刷新）时，未清理的定时器可能会导致内存泄漏或错误。
最佳实践：在组件销毁、页面离开时，主动调用 clearTimeout / clearInterval。

🛠️ 四、高级技巧与应用场景
1. 防抖（Debounce）
场景：用户在搜索框输入，你不想每按一个键就发一次请求，而是等他“停手”后再查。
原理：每次触发事件时，都重置定时器。只有在指定时间内不再触发，才执行函数。

```javascript
function debounce(func, delay) {
  let timerId;
  return function(...args) {
    // 清除上一个定时器
    clearTimeout(timerId);
    // 设置新的定时器
    timerId = setTimeout(() => func.apply(this, args), delay);
  };
}

// 使用
const searchInput = document.getElementById('search');
searchInput.addEventListener('input', debounce((e) => {
  console.log('搜索:', e.target.value);
}, 300)); // 用户停止输入300ms后才触发
```

2. 节流（Throttle）
场景：监听页面滚动 (scroll) 或窗口缩放 (resize)，这些事件触发频率极高，需要限制执行频率。
原理：保证函数在 delay 时间内最多只执行一次。

```javascript
function throttle(func, delay) {
  let lastExecTime = 0;
  return function(...args) {
    const now = Date.now();
    if (now - lastExecTime >= delay) {
      func.apply(this, args);
      lastExecTime = now;
    }
  };
}

// 使用
window.addEventListener('scroll', throttle(() => {
  console.log('页面滚动了');
}, 100)); // 每100ms最多执行一次
```

3. 倒计时器

```javascript
function countdown(seconds, onTick, onComplete) {
  let remaining = seconds;

  const timerId = setInterval(() => {
    onTick(remaining); // 每秒调用
    remaining--;

    if (remaining < 0) {
      clearInterval(timerId);
      onComplete(); // 倒计时结束
    }
  }, 1000);
}

// 使用
countdown(5,
  (sec) => console.log(`剩余: ${sec} 秒`),
  () => console.log('时间到！')
);
```

记住：
定时器是异步的，不会阻塞代码执行。
永远考虑清理，避免内存泄漏。
复杂场景优先用 防抖/节流 优化性能。
高精度动画请用 requestAnimationFrame。

**7.onload与onerror**

一句话总结，onload就是等资源加载成功之后，执行这个函数，onerror同理

```javascript
function loadImage(src, successCallback, errorCallback) {
  const img = new Image();

  img.onload = () => successCallback(img);
  img.onerror = () => errorCallback(src); // 把失败的地址传出去

  img.src = src; // 最后赋值！
}

// 使用
loadImage(
  'user-avatar.jpg',
  (img) => document.body.appendChild(img),
  (failedUrl) => {
    console.warn(`图片加载失败: ${failedUrl}`);
    // 显示默认头像
    const defaultImg = new Image();
    defaultImg.src = 'default-avatar.jpg';
    document.body.appendChild(defaultImg);
  }
);
```

应该使用onload和onerror的典型场景：
场景 1：动态加载图片（尤其是用户头像、商品图等）
为什么需要：
用户上传的图片可能被删除；
CDN 可能暂时不可用；
网络不稳定导致加载失败。

```javascript
const img = new Image();
img.onload = () => {
  // ✅ 成功：显示图片
  container.appendChild(img);
};
img.onerror = () => {
  // ❌ 失败：显示默认占位图
  img.src = '/assets/default-avatar.png';
};
img.src = user.avatarUrl; // 最后赋值！
```

场景 2：动态加载外部脚本（如第三方 SDK、A/B 测试、广告）
为什么需要：
第三方服务可能宕机；
你需要确保脚本加载成功后再调用其 API；
避免因脚本未加载导致功能报错。

```javascript
const script = document.createElement('script');
script.src = 'https://cdn.example.com/analytics.js';

script.onload = () => {
  // ✅ 脚本加载成功，初始化
  initAnalytics();
};

script.onerror = () => {
  // ❌ 加载失败，记录日志或降级
  console.error('Analytics SDK failed to load');
  // 可选：尝试备用 CDN
  // loadBackupScript();
};

document.head.appendChild(script);
```

场景 3：懒加载（Lazy Loading）或预加载（Preloading）资源
为什么需要：
图片进入视口才加载，需在加载完成后替换占位符；
预加载关键资源（如游戏素材），需知道何时可用。

```javascript
// 懒加载示例
const placeholder = document.querySelector('.lazy-img');
const realImg = new Image();

realImg.onload = () => {
  placeholder.src = realImg.src; // 替换为真实图
  placeholder.classList.remove('loading');
};

realImg.onerror = () => {
  placeholder.classList.add('load-failed');
};

realImg.src = placeholder.dataset.src; // 从 data-src 读取真实 URL
```

场景 4：处理 iframe 内容加载（较少见但有用）
为什么需要：
嵌入第三方页面（如支付页、地图）；
需要知道 iframe 是否加载完成以进行交互。

```javascript
const iframe = document.createElement('iframe');
iframe.src = 'https://payment.example.com';

iframe.onload = () => {
  console.log('支付页面已加载');
  // 注意：跨域 iframe 无法访问其内容
};

// iframe 通常没有 onerror（规范不统一），慎用
```

![图片](https://www.aoiblog.top/images/img_1774838308678.png)

**8.try...catch**

一、基本语法

```javascript
try {
  // 可能会出错的代码（“危险区”）
} catch (error) {
  // 如果 try 块中抛出错误，这里会执行
  // error 是错误对象（通常包含 message、stack 等信息）
} finally {
  // （可选）无论是否出错，都会执行
}
```

二、核心作用：捕获“抛出”的错误
JavaScript 中的错误分为两类：
语法错误（SyntaxError） → 无法用 try...catch 捕获（因为代码根本无法运行）
运行时错误（Runtime Error） → 可以被 try...catch 捕获
✅ 能捕获的情况：
手动 throw 错误
调用函数时发生异常（如访问 null 属性、JSON 解析失败等）
❌ 不能捕获的情况：
语法错误（如 console.log( 缺少括号）
异步回调中的错误（除非在回调内部用 try...catch）

三、基本示例
示例 1：手动抛出并捕获错误

```javascript
try {
  throw new Error("这是一个自定义错误！");
} catch (err) {
  console.log("捕获到错误:", err.message); // "捕获到错误: 这是一个自定义错误！"
}
```

示例 2：处理可能失败的操作

```javascript
function divide(a, b) {
  try {
    if (b === 0) {
      throw new Error("除数不能为零");
    }
    return a / b;
  } catch (err) {
    console.error("计算失败:", err.message);
    return null;
  }
}

console.log(divide(10, 2)); // 5
console.log(divide(10, 0)); // 计算失败: 除数不能为零 → 返回 null
```

四、与异步代码结合（重点！）
❌ 错误示范：try...catch 无法捕获异步回调中的错误
✅ 正确做法 1：在异步函数内部使用 try...catch

```javascript
setTimeout(() => {
  try {
    throw new Error("异步错误");
  } catch (err) {
    console.log("在回调内部捕获:", err.message);
  }
}, 100);
```

✅ 正确做法 2：使用 async/await（推荐！）

```javascript
async function fetchData() {
  try {
    const res = await fetch('/api/data');
    const data = await res.json(); // 如果 JSON 无效，会抛出错误
    return data;
  } catch (err) {
    console.error("请求或解析失败:", err.message);
    return null;
  }
}

// 调用
fetchData();
```

五、finally 块：无论成功失败都执行
常用于清理资源，比如关闭连接、隐藏加载动画等。

```javascript
let loading = true;

try {
  console.log("开始加载...");
  const data = await apiCall();
  console.log("数据:", data);
} catch (err) {
  console.error("失败:", err.message);
} finally {
  loading = false; // 无论成功失败，都结束 loading
  console.log("加载状态已重置");
}
```

六、错误对象（error）详解
catch 中的参数（通常叫 error 或 err）是一个 Error 对象，包含：
属性	说明
error.message	错误描述（字符串）
error.name	错误类型（如 "Error", "TypeError", "SyntaxError"）
error.stack	错误堆栈（调试用，显示错误发生的位置）

```javascript
try {
  null.toString();
} catch (err) {
  console.log(err.name);    // "TypeError"
  console.log(err.message); // "Cannot read properties of null (reading 'toString')"
  console.log(err.stack);   // 包含文件名、行号等
}
```

八、常见应用场景
场景	用法
API 请求	捕获网络错误、JSON 解析失败
用户输入验证	捕获格式错误（如日期解析）
文件操作	捕获读取失败
第三方库调用	防止库抛出未处理异常导致页面崩溃
降级处理	出错时返回默认值或备用方案
🎯 记住一句话：
“把可能出错的代码放进 try，把容错逻辑放进 catch。”

**9.promise**
✅ 1. 什么是 Promise？
Promise 是一个对象，代表一个尚未完成但未来会完成的操作。
它有三种状态：
pending（进行中）
fulfilled（成功，也叫 resolved）
rejected（失败）
⚠️ 状态一旦改变（pending → fulfilled/rejected），就不可逆。
✅ 2. 如何创建 Promise？
使用构造函数 new Promise(executor)：

```javascript
const myPromise = new Promise((resolve, reject) => {
  // 异步操作（比如 setTimeout、fetch、fs.readFile）
  if (/* 成功 */) {
    resolve(value);     // 改变状态为 fulfilled，传递 value
  } else {
    reject(error);      // 改变状态为 rejected，传递 error
  }
});
```

resolve 和 reject 是 JS 引擎自动传入的函数。
你决定何时调用它们。
注：resolve(value) 和 reject(reason) 的作用是：
将 Promise 的状态从 pending（等待中）变为 fulfilled（成功）或 rejected（失败）；
将传入的 value 或 reason（通常是一个 Error 对象）作为“结果数据”保存在 Promise 内部；
当状态确定后，JavaScript 引擎会自动调用 .then(onFulfilled, onRejected) 中对应的回调函数，并将 value 或 reason 作为参数传递给它们。

✅ 3. 如何使用 Promise？—— .then() 和 .catch()

```javascript
myPromise
  .then(
    (value) => { /* 处理成功 */ },
    (error) => { /* 处理失败（不常用）*/ }
  )
  .catch((error) => { /* 统一处理链中任意错误 */ });
```

关键特性：
.then() 返回新 Promise → 支持链式调用
值穿透：如果 .then() 不返回值，默认返回 undefined
异常穿透：链中任意 .then() 抛出错误，会跳到最近的 .catch()

✅ 4. 静态方法（非常有用！）
方法	作用
Promise.resolve(value)	创建一个已 fulfilled 的 Promise
Promise.reject(reason)	创建一个已 rejected 的 Promise
Promise.all([p1, p2, ...])	并行执行，全部成功才成功；任一失败则失败
Promise.race([p1, p2, ...])	谁先完成（无论成功失败），就用谁的结果
Promise.allSettled([...])	等所有 Promise 结束（不管成功失败），返回结果数组

示例：

```javascript
// 你自己创建 Promise
function delay(ms) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (ms > 0) {
        resolve(`等待了 ${ms} 毫秒`); // ← 你决定成功
      } else {
        reject(new Error('时间不能为负数')); // ← 你决定失败
      }
    }, 100);
  });
}

// 你自己写 onFulfilled 和 onRejected
delay(500).then(
  (message) => {
    // 👈 这个函数是你写的！处理成功
    alert(message);
  },
  (err) => {
    // 👈 这个函数也是你写的！处理失败
    console.error(err.message);
  }
);
```

三、async / await：Promise 的语法糖
✅ 1. async 函数是什么？
在函数前加 async，该函数自动返回一个 Promise
允许在函数内部使用 await

```javascript
async function foo() {
  return 42;
}
// 等价于：
function foo() {
  return Promise.resolve(42);
}
```

✅ 2. await 是什么？
只能在 async 函数内部使用
等待一个 Promise 完成，并自动“解包”其结果

```javascript
async function getUser() {
  const response = await fetch('/api/user'); // 暂停，等 fetch 完成
  const user = await response.json();        // 暂停，等 json() 完成
  return user; // 自动包装为 Promise
}
```

✅ await 后面可以是：
Promise（最常见）
普通值（如 await 42 → 直接返回 42）
表达式

✅ 3. 错误处理：用 try...catch
这是 async/await 最大的优势之一：用同步风格处理异步错误！

```javascript
async function safeFetch() {
  try {
    const res = await fetch('/api/data');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data;
  } catch (error) {
    console.error('请求失败:', error.message);
    // 可以返回默认值、重试、或重新抛出
    throw error;
  }
}
```

✅ 4. 并行 vs 串行
❌ 串行（低效）：

```javascript
async function loadSlowly() {
  const user = await fetchUser();     // 等 1 秒
  const posts = await fetchPosts();   // 再等 1 秒 → 总共 2 秒
  return { user, posts };
}
```

✅ 并行（高效）：

```javascript
async function loadQuickly() {
  const [user, posts] = await Promise.all([
    fetchUser(),
    fetchPosts()
  ]); // 同时发起，总耗时 ≈ 1 秒
  return { user, posts };
}
```

五、常见误区与注意事项
❌ 误区 1：await 会阻塞整个程序
不会！
它只暂停当前 async 函数的执行，不影响其他代码。
❌ 误区 2：async 函数能直接返回值
不能！ 它总是返回 Promise：
❌ 误区 3：忘记处理错误

```javascript
// 危险！未捕获的 reject 会导致 unhandledrejection
const data = await badApi();

// 安全做法：
try {
  const data = await badApi();
} catch (err) {
  // 处理错误
}
```

❌ 误区 4：在循环中滥用 await

```javascript
// 串行（慢）
for (const url of urls) {
  const data = await fetch(url);
  results.push(data);
}

// 并行（快）
const promises = urls.map(url => fetch(url));
const results = await Promise.all(promises);
```

六、最佳实践
优先使用 async/await 而不是 .then() 链
总是用 try...catch 包裹 await
并行任务用 Promise.all
避免在顶层代码直接用 await（除非你的环境支持 top-level await，如现代浏览器模块或 Node.js ES 模块）
不要忽略 Promise 的 reject（会导致警告或崩溃）

七、完整示例：用户登录流程

```javascript
// 模拟 API
function login(credentials) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (credentials.password === 'secret') {
        resolve({ token: 'abc123', user: { id: 1, name: 'Alice' } });
      } else {
        reject(new Error('Invalid password'));
      }
    }, 500);
  });
}

// 使用 async/await
async function handleLogin(username, password) {
  try {
    const { token, user } = await login({ username, password });
    localStorage.setItem('token', token);
    showWelcome(user.name);
  } catch (error) {
    showError(error.message);
  }
}

// 调用
handleLogin('alice', 'wrong'); // 显示 "Invalid password"
```


<section class="legacy-comments">
  <h2>评论区</h2>
  <div id="twikoo-article_1774454087284" data-twikoo-path="article_1774454087284"></div>
</section>
