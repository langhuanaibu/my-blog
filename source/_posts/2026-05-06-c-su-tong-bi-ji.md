---
title: "C++ 速通笔记"
date: "2026-05-06"
updated: "2026-05-06"
categories:
  - "数据结构与算法"
old_id: "article_1778042546856"
twikooPath: "article_1778042546856"
---
<h2>C++ 速通笔记</h2>
# C++ 速通学习笔记：从 C 到 C++ 语法迁移

> 适合读者：已经学完 C 语言，想快速掌握 C++ 常用语法，并能看懂、写出算法题里的 C++ 代码。
>
> 默认标准：C++17。
>
> 学习目标：不是重新学编程基础，而是回答一个核心问题：**这块 C++ 和 C 有什么不一样？我作为 C 使用者应该怎么迁移？**

## 0. 先给你一张迁移地图

如果你已经会 C，那么 C++ 里最值得优先掌握的是这些东西：

| C 语言常用写法 | C++ 常用写法 | 迁移重点 |
| --- | --- | --- |
| `printf` | `cout` | 输出类型自动匹配，不用写格式占位符 |
| `scanf` | `cin` | 输入类型自动匹配，但要注意速度优化 |
| `char s[100]` | `string s` | 字符串可动态增长，支持拼接、比较、查找 |
| `int a[100]` | `vector<int> a` | 动态数组，自动扩容，算法题最常用 |
| 手写链表/栈/队列/堆 | `list` / `stack` / `queue` / `priority_queue` | STL 提供常见数据结构 |
| 手写哈希表 | `unordered_map` / `unordered_set` | 平均 O(1) 查找 |
| `qsort` + 函数指针 | `sort` + lambda | 类型安全，可读性更强 |
| 指针传参修改变量 | 引用传参 `int&` | 写法更简洁，语义更清晰 |
| `malloc/free` | `new/delete`，更推荐 RAII 和智能指针 | 工程 C++ 尽量少裸写资源释放 |
| `struct` 只放数据 | `struct/class` 可放数据和函数 | C++ 支持面向对象 |

刷算法的优先级建议：

1. 基础语法：输入输出、`string`、`vector`、引用、`auto`。
2. STL 容器：`vector`、`string`、`unordered_map`、`unordered_set`、`queue`、`stack`、`priority_queue`。
3. 算法库：`sort`、`reverse`、`lower_bound`、`max/min`。
4. 类和模板：先能看懂，不急着深挖模板元编程。
5. 内存、异常、智能指针：刷题少用，但读工程代码必须认识。

---

## 1. C++ 与 C 的总体差异

### 这是什么

C++ 可以看作在 C 的基础上增加了更强的抽象能力：

- 命名空间：避免名字冲突。
- 引用：比指针更简洁的别名机制。
- 函数重载：同名函数可以根据参数不同自动区分。
- 类和对象：把数据和操作数据的函数组织在一起。
- 模板：写泛型代码，比如 `vector<int>`、`vector<string>`。
- 异常：用 `throw/try/catch` 处理错误。
- STL：标准模板库，提供常用容器和算法。

### C 里怎么写

C 更接近过程式编程：

```c
#include <stdio.h>

void print_int(int x) {
    printf("%d\n", x);
}

int main() {
    int x = 10;
    print_int(x);
    return 0;
}
```

### C++ 怎么写

```cpp
#include <iostream>
using namespace std;

void print(int x) {
    cout << x << '\n';
}

int main() {
    int x = 10;
    print(x);
    return 0;
}
```

### 差异与好处

C++ 保留了 C 的大部分语法，但提供了更高层的工具。你仍然可以写指针、数组、结构体，但多数时候可以用 `string`、`vector`、STL 容器替代手写底层逻辑。

### 常见坑

- C++ 不是“只有类”的语言。刷算法时，大部分代码仍然是函数 + STL。
- C++ 兼容很多 C 写法，但不代表推荐继续用 C 风格。
- `using namespace std;` 在算法题里方便，工程代码里更推荐显式写 `std::`。

### 刷题常用写法

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> nums(n);
    for (int& x : nums) cin >> x;

    sort(nums.begin(), nums.end());

    for (int x : nums) cout << x << ' ';
    cout << '\n';

    return 0;
}
```

---

## 2. 程序结构、编译与头文件

### 这是什么

C++ 程序也从 `main` 函数开始。不同点主要在头文件、命名空间和标准库使用方式。

### C 里怎么写

```c
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main() {
    printf("hello C\n");
    return 0;
}
```

### C++ 怎么写

```cpp
#include <iostream>
#include <string>
#include <vector>
using namespace std;

int main() {
    cout << "hello C++" << '\n';
    return 0;
}
```

如果不写 `using namespace std;`：

```cpp
#include <iostream>

int main() {
    std::cout << "hello C++" << '\n';
    return 0;
}
```

### 差异与好处

C++ 标准库的名字大多放在 `std` 命名空间里，比如：

- `std::cout`
- `std::cin`
- `std::string`
- `std::vector`
- `std::sort`

常见 C 头文件和 C++ 头文件对照：

| C 头文件 | C++ 头文件 | 说明 |
| --- | --- | --- |
| `stdio.h` | `<cstdio>` | C 风格输入输出 |
| `stdlib.h` | `<cstdlib>` | 常用工具函数 |
| `string.h` | `<cstring>` | C 字符串函数 |
| `math.h` | `<cmath>` | 数学函数 |
| `ctype.h` | `<cctype>` | 字符判断 |

C++ 还有自己的核心头文件：

| 头文件 | 常用内容 |
| --- | --- |
| `<iostream>` | `cin`、`cout` |
| `<string>` | `string` |
| `<vector>` | `vector` |
| `<queue>` | `queue`、`priority_queue` |
| `<stack>` | `stack` |
| `<unordered_map>` | 哈希表 |
| `<unordered_set>` | 哈希集合 |
| `<algorithm>` | `sort`、`reverse`、`max`、`min`、二分函数 |

### 常见坑

`#include <bits/stdc++.h>` 是很多算法题常用头文件，它几乎包含了所有常见标准库：

```cpp
#include <bits/stdc++.h>
using namespace std;
```

它的优点是方便，缺点是不属于正式 C++ 标准，部分编译器不支持。刷题平台一般可以用，工程项目不建议用。

### 刷题常用写法

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    return 0;
}
```

工程代码更推荐：

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int main() {
    std::vector<int> nums{3, 1, 2};
    std::sort(nums.begin(), nums.end());
    for (int x : nums) {
        std::cout << x << '\n';
    }
    return 0;
}
```

---

## 3. 输入输出：`cin/cout` vs `scanf/printf`

### 这是什么

C++ 使用流式输入输出：

- `cin >> x`：读入。
- `cout << x`：输出。
- `getline(cin, s)`：读取一整行字符串。

### C 里怎么写

```c
#include <stdio.h>

int main() {
    int age;
    double score;
    char name[100];

    scanf("%d %lf %s", &age, &score, name);
    printf("name=%s age=%d score=%.2f\n", name, age, score);

    return 0;
}
```

### C++ 怎么写

```cpp
#include <iostream>
#include <string>
using namespace std;

int main() {
    int age;
    double score;
    string name;

    cin >> age >> score >> name;
    cout << "name=" << name << " age=" << age << " score=" << score << '\n';

    return 0;
}
```

### 差异与好处

C 的 `scanf/printf` 要自己写格式占位符，比如 `%d`、`%lf`、`%s`。C++ 的 `cin/cout` 会根据变量类型自动处理。

读取一整行：

```cpp
string line;
getline(cin, line);
```

循环读到 EOF：

```cpp
int x;
while (cin >> x) {
    cout << x << '\n';
}
```

### 常见坑

`cin >>` 会留下换行符，后面直接 `getline` 可能读到空行：

```cpp
int n;
string line;

cin >> n;
getline(cin, line); // 这里可能读到上一行剩下的换行
```

正确写法：

```cpp
int n;
string line;

cin >> n;
cin.ignore();
getline(cin, line);
```

或者：

```cpp
getline(cin >> ws, line);
```

刷题时如果大量输入输出，建议加：

```cpp
ios::sync_with_stdio(false);
cin.tie(nullptr);
```

注意：加了这两行后，不建议混用 `cin/cout` 和 `scanf/printf`。

### 刷题常用写法

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<int> nums(n);
    for (int i = 0; i < n; i++) {
        cin >> nums[i];
    }

    for (int x : nums) {
        cout << x << ' ';
    }
    cout << '\n';

    return 0;
}
```

---

## 4. 类型系统与变量声明

### 这是什么

C++ 有 C 的基本类型，也增加了更好用的类型和声明方式：

- `bool`：布尔类型。
- `string`：字符串类型。
- `auto`：让编译器推导类型。
- `long long`：算法题常用大整数类型。
- `const`：常量和只读引用。

### C 里怎么写

```c
#include <stdio.h>
#include <string.h>

int main() {
    int ok = 1;
    char name[100] = "alice";

    if (ok) {
        printf("%s\n", name);
    }

    return 0;
}
```

### C++ 怎么写

```cpp
#include <iostream>
#include <string>
using namespace std;

int main() {
    bool ok = true;
    string name = "alice";

    if (ok) {
        cout << name << '\n';
    }

    return 0;
}
```

### 差异与好处

C++ 的 `string` 比 C 字符数组更安全、更方便：

```cpp
string a = "hello";
string b = "world";
string c = a + " " + b;

cout << c.size() << '\n';
cout << c[0] << '\n';
```

`auto` 可以减少冗长类型：

```cpp
vector<int> nums{1, 2, 3};

auto n = nums.size();        // n 的类型是 size_t
auto it = nums.begin();      // it 是 vector<int>::iterator
```

初始化方式：

```cpp
int a = 10;
int b(10);
int c{10};

vector<int> nums{1, 2, 3};
string s{"hello"};
```

### 常见坑

整数除法和 C 一样：

```cpp
cout << 5 / 2 << '\n';      // 2
cout << 5 / 2.0 << '\n';    // 2.5
```

`size_t` 和 `int` 比较容易出现警告：

```cpp
vector<int> nums{1, 2, 3};

for (int i = 0; i < nums.size(); i++) {
    cout << nums[i] << '\n';
}
```

更稳妥：

```cpp
for (int i = 0; i < (int)nums.size(); i++) {
    cout << nums[i] << '\n';
}
```

或者：

```cpp
for (size_t i = 0; i < nums.size(); i++) {
    cout << nums[i] << '\n';
}
```

### 刷题常用写法

```cpp
using ll = long long;

const int INF = 1e9;
const ll LINF = 4e18;

vector<int> nums{1, 2, 3};
string s = "abc";
bool found = false;
```

---

## 5. 引用、指针与函数

### 这是什么

引用是 C++ 非常核心的语法。可以把引用理解成一个变量的别名。

```cpp
int x = 10;
int& ref = x;
ref = 20;
cout << x << '\n'; // 20
```

### C 里怎么写

C 语言如果想在函数里修改外部变量，通常用指针：

```c
#include <stdio.h>

void add_one(int* p) {
    (*p)++;
}

int main() {
    int x = 10;
    add_one(&x);
    printf("%d\n", x);
    return 0;
}
```

### C++ 怎么写

C++ 可以用引用：

```cpp
#include <iostream>
using namespace std;

void add_one(int& x) {
    x++;
}

int main() {
    int x = 10;
    add_one(x);
    cout << x << '\n';
    return 0;
}
```

### 差异与好处

函数传参有三种常见方式：

```cpp
void f1(vector<int> nums) {
    // 值传递：复制一份，修改不影响原数组，成本高
}

void f2(vector<int>& nums) {
    // 引用传递：不复制，修改会影响原数组
}

void f3(const vector<int>& nums) {
    // const 引用传递：不复制，也不允许修改，最常用于只读大对象
}
```

为什么算法题里经常写 `vector<int>& nums`？

```cpp
int sum(const vector<int>& nums) {
    int ans = 0;
    for (int x : nums) {
        ans += x;
    }
    return ans;
}
```

如果写成 `vector<int> nums`，每次调用都会复制整个数组，大数据下很慢。

C++ 还支持函数重载：

```cpp
int add(int a, int b) {
    return a + b;
}

double add(double a, double b) {
    return a + b;
}
```

默认参数：

```cpp
void print(string s, char end = '\n') {
    cout << s << end;
}
```

### 常见坑

不要返回局部变量的引用：

```cpp
int& bad() {
    int x = 10;
    return x; // 错误：x 离开函数就销毁了
}
```

如果不想修改传入对象，优先用 `const` 引用：

```cpp
void print_vec(const vector<int>& nums) {
    for (int x : nums) cout << x << ' ';
    cout << '\n';
}
```

### 刷题常用写法

```cpp
class Solution {
public:
    int maxValue(const vector<int>& nums) {
        int ans = nums[0];
        for (int x : nums) {
            ans = max(ans, x);
        }
        return ans;
    }
};
```

---

## 6. 控制流与 C++ 新语法

### 这是什么

`if/else`、`for`、`while`、`switch` 和 C 基本一致。C++ 需要重点补充范围 for、`auto`、结构化绑定。

### C 里怎么写

```c
int a[3] = {1, 2, 3};

for (int i = 0; i < 3; i++) {
    printf("%d\n", a[i]);
}
```

### C++ 怎么写

```cpp
vector<int> nums{1, 2, 3};

for (int x : nums) {
    cout << x << '\n';
}
```

### 差异与好处

范围 for 更适合遍历容器：

```cpp
vector<int> nums{1, 2, 3};

for (auto x : nums) {
    x *= 2; // 修改的是副本
}

for (auto& x : nums) {
    x *= 2; // 修改原数组
}
```

遍历哈希表：

```cpp
unordered_map<string, int> cnt{{"apple", 2}, {"banana", 3}};

for (const auto& [key, value] : cnt) {
    cout << key << " " << value << '\n';
}
```

### 常见坑

`for (auto x : nums)` 会复制元素。如果元素很大，或者你想修改原容器，要用引用：

```cpp
for (auto& x : nums) {
    x++;
}
```

如果只是读，推荐：

```cpp
for (const auto& x : nums) {
    cout << x << '\n';
}
```

### 刷题常用写法

```cpp
for (int i = 0; i < (int)nums.size(); i++) {
    // 需要下标时用普通 for
}

for (int x : nums) {
    // 只需要元素值时用范围 for
}

for (auto& [key, value] : mp) {
    // 遍历 map/unordered_map
}
```

---

## 7. 数组、字符串与 STL 容器

### 这是什么

STL 是 C++ 刷算法的核心。你可以少写很多底层数据结构，把精力放在算法本身。

### 7.1 数组、`array`、`vector`

#### C 里怎么写

```c
int a[100];
int n = 0;

a[n++] = 10;
a[n++] = 20;
```

#### C++ 怎么写

```cpp
vector<int> nums;
nums.push_back(10);
nums.push_back(20);
```

#### 差异与好处

| 类型 | 大小是否固定 | 常用场景 |
| --- | --- | --- |
| C 数组 `int a[100]` | 固定 | 已知最大长度，追求极致性能 |
| `array<int, 100>` | 固定 | 固定大小，但有 STL 接口 |
| `vector<int>` | 可变 | 算法题最常用动态数组 |

`vector` 常用 API：

```cpp
vector<int> v;

v.push_back(1);
v.pop_back();
v.size();
v.empty();
v.clear();
v.front();
v.back();
v[0];
```

复杂度直觉：

- 下标访问：O(1)。
- 尾部插入：均摊 O(1)。
- 中间插入/删除：O(n)。

#### 常见坑

`v[i]` 不检查越界，越界是未定义行为。调试时可以用 `v.at(i)`，它会抛异常。

初始化二维数组：

```cpp
int m = 3, n = 4;
vector<vector<int>> grid(m, vector<int>(n, 0));
```

#### 刷题常用写法

```cpp
vector<int> nums(n);
for (int& x : nums) cin >> x;

vector<vector<int>> dp(n + 1, vector<int>(m + 1, 0));
```

### 7.2 `string`

#### C 里怎么写

```c
char s[100] = "hello";
char t[100] = "world";
strcat(s, t);
printf("%s\n", s);
```

#### C++ 怎么写

```cpp
string s = "hello";
string t = "world";
string u = s + t;
cout << u << '\n';
```

#### 差异与好处

`string` 常用 API：

```cpp
string s = "abc";

s.size();
s.empty();
s.push_back('d');
s.pop_back();
s.substr(1, 2);
s.find("bc");
s[0];
```

字符串可以直接比较：

```cpp
if (a < b) {
    cout << "a 字典序更小\n";
}
```

#### 常见坑

`s.find(x)` 找不到时返回 `string::npos`：

```cpp
if (s.find("abc") == string::npos) {
    cout << "not found\n";
}
```

#### 刷题常用写法

```cpp
string s;
cin >> s;

unordered_map<char, int> cnt;
for (char c : s) {
    cnt[c]++;
}
```

### 7.3 `list` 和 `deque`

#### C 里怎么写

C 语言一般要手写链表结构：

```c
struct Node {
    int val;
    struct Node* next;
};
```

#### C++ 怎么写

```cpp
list<int> lst;
lst.push_back(1);
lst.push_front(2);
lst.pop_back();
lst.pop_front();
```

`deque` 是双端队列：

```cpp
deque<int> dq;
dq.push_back(1);
dq.push_front(2);
dq.pop_back();
dq.pop_front();
```

#### 差异与好处

| 容器 | 特点 | 常用场景 |
| --- | --- | --- |
| `list` | 双向链表，任意位置插入删除快，但不能 O(1) 下标访问 | 较少用于算法题 |
| `deque` | 双端队列，两端插入删除快，支持下标访问 | 单调队列、滑动窗口 |

#### 常见坑

`list` 不能写 `lst[i]`，因为链表不支持随机访问。

#### 刷题常用写法

滑动窗口最大值常用 `deque<int>` 存下标：

```cpp
deque<int> q;

for (int i = 0; i < n; i++) {
    while (!q.empty() && nums[q.back()] <= nums[i]) q.pop_back();
    q.push_back(i);
    if (q.front() <= i - k) q.pop_front();
    if (i >= k - 1) ans.push_back(nums[q.front()]);
}
```

### 7.4 `map`、`unordered_map`

#### C 里怎么写

C 语言没有内置哈希表，通常需要手写，或者用数组模拟计数：

```c
int cnt[256] = {0};
cnt['a']++;
```

#### C++ 怎么写

```cpp
unordered_map<string, int> cnt;
cnt["apple"]++;
cnt["banana"] += 2;
```

#### 差异与好处

| 容器 | 底层直觉 | 查找复杂度 | 是否有序 |
| --- | --- | --- | --- |
| `map` | 红黑树 | O(log n) | 按 key 有序 |
| `unordered_map` | 哈希表 | 平均 O(1) | 无序 |

常用 API：

```cpp
unordered_map<string, int> mp;

mp["a"] = 1;
mp.count("a");
mp.find("a");
mp.erase("a");
mp.size();
mp.empty();
```

#### 常见坑

`mp[key]` 如果 key 不存在，会自动插入默认值：

```cpp
unordered_map<string, int> mp;
cout << mp["x"] << '\n'; // 插入 "x"，值为 0
```

如果只想判断是否存在：

```cpp
if (mp.count("x")) {
    cout << "exists\n";
}
```

#### 刷题常用写法

两数之和：

```cpp
vector<int> twoSum(vector<int>& nums, int target) {
    unordered_map<int, int> pos;
    for (int i = 0; i < (int)nums.size(); i++) {
        int need = target - nums[i];
        if (pos.count(need)) {
            return {pos[need], i};
        }
        pos[nums[i]] = i;
    }
    return {};
}
```

### 7.5 `set`、`unordered_set`

#### C 里怎么写

C 里通常用数组、排序、手写哈希来判断元素是否出现。

#### C++ 怎么写

```cpp
unordered_set<int> seen;
seen.insert(10);

if (seen.count(10)) {
    cout << "found\n";
}
```

#### 差异与好处

| 容器 | 查找复杂度 | 是否有序 | 是否去重 |
| --- | --- | --- | --- |
| `set` | O(log n) | 有序 | 是 |
| `unordered_set` | 平均 O(1) | 无序 | 是 |

#### 常见坑

`set` 和 `unordered_set` 只存 key，不存 value。如果你要记录次数，用 `map/unordered_map`。

#### 刷题常用写法

```cpp
bool hasDuplicate(vector<int>& nums) {
    unordered_set<int> seen;
    for (int x : nums) {
        if (seen.count(x)) return true;
        seen.insert(x);
    }
    return false;
}
```

### 7.6 `queue`、`stack`、`priority_queue`

#### C 里怎么写

C 语言一般用数组模拟栈、队列、堆。

#### C++ 怎么写

```cpp
stack<int> st;
st.push(1);
st.top();
st.pop();

queue<int> q;
q.push(1);
q.front();
q.pop();
```

堆：

```cpp
priority_queue<int> max_heap;
max_heap.push(3);
max_heap.push(1);
cout << max_heap.top() << '\n'; // 3
```

小根堆：

```cpp
priority_queue<int, vector<int>, greater<int>> min_heap;
```

#### 差异与好处

| 容器 | 语义 | 常用场景 |
| --- | --- | --- |
| `stack` | 后进先出 | 括号匹配、单调栈 |
| `queue` | 先进先出 | BFS |
| `priority_queue` | 堆 | Top K、Dijkstra |

#### 常见坑

`pop()` 不返回元素，必须先 `top()` 或 `front()`：

```cpp
int x = st.top();
st.pop();
```

`priority_queue` 默认是大根堆。

#### 刷题常用写法

BFS：

```cpp
queue<int> q;
vector<bool> visited(n, false);

q.push(start);
visited[start] = true;

while (!q.empty()) {
    int cur = q.front();
    q.pop();

    for (int next : graph[cur]) {
        if (!visited[next]) {
            visited[next] = true;
            q.push(next);
        }
    }
}
```

---

## 8. 迭代器、范围与算法库

### 这是什么

迭代器可以理解成 STL 容器里的“泛化指针”。算法库通过迭代器操作不同容器。

### C 里怎么写

C 语言排序常用 `qsort`：

```c
#include <stdlib.h>

int cmp(const void* a, const void* b) {
    return (*(int*)a) - (*(int*)b);
}

qsort(arr, n, sizeof(int), cmp);
```

### C++ 怎么写

```cpp
sort(nums.begin(), nums.end());
```

自定义排序：

```cpp
sort(nums.begin(), nums.end(), [](int a, int b) {
    return a > b;
});
```

### 差异与好处

常见算法库函数：

```cpp
sort(v.begin(), v.end());
reverse(v.begin(), v.end());

int a = max(x, y);
int b = min(x, y);

auto it = lower_bound(v.begin(), v.end(), target);
auto it2 = upper_bound(v.begin(), v.end(), target);
```

`lower_bound` 和 `upper_bound` 要求区间有序：

- `lower_bound`：第一个 `>= target` 的位置。
- `upper_bound`：第一个 `> target` 的位置。

例子：

```cpp
vector<int> v{1, 2, 2, 2, 5};

auto l = lower_bound(v.begin(), v.end(), 2);
auto r = upper_bound(v.begin(), v.end(), 2);

cout << (l - v.begin()) << '\n'; // 1
cout << (r - v.begin()) << '\n'; // 4
```

### 常见坑

迭代器不是所有容器都能相减。`vector` 支持 `it - v.begin()`，`list` 不支持。

`sort` 不能直接用于 `list`：

```cpp
list<int> lst{3, 1, 2};
lst.sort();
```

自定义排序比较器必须满足严格弱序，不能乱写：

```cpp
sort(v.begin(), v.end(), [](int a, int b) {
    return a < b; // 正确
});
```

### 刷题常用写法

按照二维数组的第二项排序：

```cpp
vector<vector<int>> intervals{{1, 3}, {2, 4}, {0, 2}};

sort(intervals.begin(), intervals.end(), [](const auto& a, const auto& b) {
    return a[1] < b[1];
});
```

对结构体排序：

```cpp
struct Node {
    int x;
    int y;
};

vector<Node> nodes{{1, 3}, {1, 2}, {0, 5}};

sort(nodes.begin(), nodes.end(), [](const Node& a, const Node& b) {
    if (a.x != b.x) return a.x < b.x;
    return a.y < b.y;
});
```

---

## 9. 结构体、类与面向对象

### 这是什么

C++ 的 `struct` 和 `class` 都可以包含成员变量和成员函数。区别主要是默认访问权限：

- `struct` 默认 `public`。
- `class` 默认 `private`。

### C 里怎么写

```c
struct Point {
    int x;
    int y;
};

void move(struct Point* p, int dx, int dy) {
    p->x += dx;
    p->y += dy;
}
```

### C++ 怎么写

```cpp
struct Point {
    int x;
    int y;

    void move(int dx, int dy) {
        x += dx;
        y += dy;
    }
};

int main() {
    Point p{1, 2};
    p.move(3, 4);
}
```

### 差异与好处

类可以封装数据和行为：

```cpp
class Counter {
private:
    int value;

public:
    Counter() : value(0) {}

    void add() {
        value++;
    }

    int get() const {
        return value;
    }
};
```

构造函数：

```cpp
struct Node {
    int val;
    Node* next;

    Node(int v) : val(v), next(nullptr) {}
};
```

继承和虚函数：

```cpp
class Animal {
public:
    virtual void speak() const = 0;
    virtual ~Animal() = default;
};

class Dog : public Animal {
public:
    void speak() const override {
        cout << "wang\n";
    }
};
```

### 常见坑

如果一个类要被继承并通过基类指针删除对象，析构函数应该是 `virtual`：

```cpp
class Base {
public:
    virtual ~Base() = default;
};
```

成员函数后面的 `const` 表示这个函数不会修改对象：

```cpp
int get() const {
    return value;
}
```

### 刷题常用写法

LeetCode 风格：

```cpp
class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        unordered_map<int, int> pos;
        for (int i = 0; i < (int)nums.size(); i++) {
            int need = target - nums[i];
            if (pos.count(need)) {
                return {pos[need], i};
            }
            pos[nums[i]] = i;
        }
        return {};
    }
};
```

二叉树节点常见定义：

```cpp
struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;

    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};
```

---

## 10. 模板与泛型

### 这是什么

模板让你写“和类型无关”的代码。STL 的 `vector<int>`、`vector<string>`、`map<string, int>` 都是模板的应用。

### C 里怎么写

C 语言如果想写通用函数，经常要用 `void*`，类型不安全：

```c
void swap_any(void* a, void* b, int size);
```

### C++ 怎么写

函数模板：

```cpp
template <typename T>
T my_max(T a, T b) {
    return a > b ? a : b;
}

int main() {
    cout << my_max(3, 5) << '\n';
    cout << my_max(2.5, 1.2) << '\n';
}
```

类模板：

```cpp
template <typename T>
class Box {
private:
    T value;

public:
    Box(T v) : value(v) {}

    T get() const {
        return value;
    }
};
```

### 差异与好处

模板是编译期生成代码，类型安全：

```cpp
vector<int> a;
vector<string> b;
unordered_map<string, int> cnt;
```

你不需要现在就深入模板元编程，但至少要能看懂：

```cpp
template <typename T>
void print_vec(const vector<T>& v) {
    for (const T& x : v) {
        cout << x << ' ';
    }
    cout << '\n';
}
```

### 常见坑

模板错误信息可能很长。初学阶段先记住：模板要求你使用的类型支持对应操作。

比如这个函数要求 `T` 支持 `>`：

```cpp
template <typename T>
T my_max(T a, T b) {
    return a > b ? a : b;
}
```

### 刷题常用写法

刷题时很少自己写复杂模板，但经常使用模板容器：

```cpp
vector<vector<int>> grid;
unordered_map<string, vector<int>> mp;
priority_queue<pair<int, int>, vector<pair<int, int>>, greater<pair<int, int>>> pq;
```

---

## 11. 异常、内存与现代 C++ 补充

### 这是什么

C++ 提供异常机制、对象生命周期管理和智能指针。刷算法不常用，但它们是工程 C++ 的核心。

### C 里怎么写

C 语言通常用返回值表示错误：

```c
int divide(int a, int b, int* result) {
    if (b == 0) return -1;
    *result = a / b;
    return 0;
}
```

动态内存：

```c
int* p = (int*)malloc(sizeof(int) * n);
free(p);
```

### C++ 怎么写

异常：

```cpp
int divide(int a, int b) {
    if (b == 0) {
        throw runtime_error("divide by zero");
    }
    return a / b;
}

int main() {
    try {
        cout << divide(10, 0) << '\n';
    } catch (const exception& e) {
        cout << e.what() << '\n';
    }
}
```

动态内存：

```cpp
int* p = new int[10];
delete[] p;
```

更现代的写法：

```cpp
auto p = make_unique<int>(10);
cout << *p << '\n';
```

### 差异与好处

C++ 更强调 RAII：资源在对象构造时获取，在对象析构时释放。

比如 `vector` 会自动管理内存：

```cpp
void f() {
    vector<int> nums(1000000);
} // 离开作用域后自动释放
```

智能指针：

```cpp
unique_ptr<int> p1 = make_unique<int>(10);
shared_ptr<int> p2 = make_shared<int>(20);
```

| 工具 | 含义 |
| --- | --- |
| `unique_ptr` | 独占所有权，不能随便复制 |
| `shared_ptr` | 共享所有权，引用计数 |
| `weak_ptr` | 弱引用，避免循环引用 |

### 常见坑

不要混用申请和释放方式：

| 申请 | 释放 |
| --- | --- |
| `malloc` | `free` |
| `new` | `delete` |
| `new[]` | `delete[]` |

刷题里通常不需要手写 `new/delete`，优先用 `vector`、`string` 和局部对象。

### 刷题常用写法

```cpp
vector<int> nums(n);
string s;
queue<int> q;
unordered_map<int, int> mp;
```

算法题中的链表、树节点通常由平台创建，你只需要操作指针：

```cpp
ListNode* reverseList(ListNode* head) {
    ListNode* pre = nullptr;
    ListNode* cur = head;

    while (cur != nullptr) {
        ListNode* nxt = cur->next;
        cur->next = pre;
        pre = cur;
        cur = nxt;
    }

    return pre;
}
```

---

## 12. C 到 C++ 迁移速查表

### 12.1 基础写法对照

| 目标 | C 写法 | C++ 写法 |
| --- | --- | --- |
| 输出整数 | `printf("%d\n", x);` | `cout << x << '\n';` |
| 输入整数 | `scanf("%d", &x);` | `cin >> x;` |
| 字符串 | `char s[100];` | `string s;` |
| 字符串长度 | `strlen(s)` | `s.size()` |
| 字符串拼接 | `strcat(a, b)` | `a + b` |
| 动态数组 | `malloc` + 手动扩容 | `vector<int>` |
| 哈希计数 | 手写哈希表 | `unordered_map<int, int>` |
| 集合判重 | 排序/手写哈希 | `unordered_set<int>` |
| 排序 | `qsort` | `sort(v.begin(), v.end())` |
| 函数修改实参 | 指针 `int* p` | 引用 `int& x` |

### 12.2 常用 STL 速查

| 容器 | 头文件 | 核心操作 | 复杂度直觉 |
| --- | --- | --- | --- |
| `vector` | `<vector>` | `push_back`、`pop_back`、`[]` | 尾插均摊 O(1)，访问 O(1) |
| `string` | `<string>` | `+`、`substr`、`find` | 类似动态字符数组 |
| `deque` | `<deque>` | `push_front`、`push_back` | 两端操作 O(1) |
| `stack` | `<stack>` | `push`、`top`、`pop` | O(1) |
| `queue` | `<queue>` | `push`、`front`、`pop` | O(1) |
| `priority_queue` | `<queue>` | `push`、`top`、`pop` | 插入删除 O(log n) |
| `map` | `<map>` | `[]`、`find`、`count` | O(log n)，key 有序 |
| `unordered_map` | `<unordered_map>` | `[]`、`find`、`count` | 平均 O(1)，key 无序 |
| `set` | `<set>` | `insert`、`erase`、`count` | O(log n)，有序去重 |
| `unordered_set` | `<unordered_set>` | `insert`、`erase`、`count` | 平均 O(1)，无序去重 |

### 12.3 算法题 C++ 模板代码

```cpp
#include <bits/stdc++.h>
using namespace std;

using ll = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<int> nums(n);
    for (int& x : nums) {
        cin >> x;
    }

    unordered_map<int, int> cnt;
    for (int x : nums) {
        cnt[x]++;
    }

    sort(nums.begin(), nums.end());

    for (int x : nums) {
        cout << x << ' ';
    }
    cout << '\n';

    return 0;
}
```

### 12.4 LeetCode 风格模板

```cpp
#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        unordered_map<int, int> pos;

        for (int i = 0; i < (int)nums.size(); i++) {
            int need = target - nums[i];
            if (pos.count(need)) {
                return {pos[need], i};
            }
            pos[nums[i]] = i;
        }

        return {};
    }
};
```

---

## 13. 建议学习路线

### 第一轮：能写出 C++ 算法题

优先学：

- `cin/cout`
- `string`
- `vector`
- 引用 `&`
- `auto`
- range-based for
- `unordered_map`、`unordered_set`
- `queue`、`stack`、`priority_queue`
- `sort` 和 lambda

目标：把以前用 C 写数组、字符串、哈希表、排序的代码迁移到 C++ STL。

### 第二轮：能看懂常见 C++ 代码

继续学：

- `class`、`struct`
- 构造函数
- `public/private`
- `const` 成员函数
- 函数重载
- 模板基础

目标：能看懂 LeetCode、labuladong 算法笔记、普通工程代码里的类和模板容器。

### 第三轮：进入现代 C++ 工程

再学：

- RAII
- 智能指针
- 移动语义
- 异常安全
- 标准库更深层用法
- CMake 和工程组织

目标：写更可靠、更工程化的 C++。

---

## 14. 最后给 C 使用者的迁移建议

不要把 C++ 当成“必须全部用类重写的 C”。对算法学习来说，最重要的是：

1. 用 `vector` 替代大部分手写动态数组。
2. 用 `string` 替代大部分 `char[]`。
3. 用 `unordered_map/unordered_set` 替代手写哈希。
4. 用引用传参避免复制大对象。
5. 用 STL 算法替代 `qsort` 和大量手写循环。
6. 能看懂 `class Solution`、模板容器、lambda，就已经能读大多数算法题 C++ 代码。

C++ 的完整体系很大，但刷算法和语法迁移不需要一口气啃完。先把 C++ 当作“C + 更强大的标准库 + 更清晰的抽象工具”，你会迁移得快很多。

---

## 15. 标准语法格式补充

这一节用来补足“查语法”的需求。前面的章节偏迁移理解，这里把常用写法集中列出来，方便以后快速回看。

### 15.1 程序结构

```cpp
#include <iostream>
using namespace std;

int main() {
    // 代码写在这里
    return 0;
}
```

刷题常用：

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    return 0;
}
```

工程更推荐：

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> nums;
    std::cout << nums.size() << '\n';
    return 0;
}
```

### 15.2 输入输出

```cpp
int x;
cin >> x;

cout << x << '\n';
```

多个变量：

```cpp
int a, b;
cin >> a >> b;
cout << a + b << '\n';
```

读取一整行：

```cpp
string line;
getline(cin, line);
```

### 15.3 函数与引用传参

普通函数：

```cpp
返回值类型 函数名(参数类型 参数名) {
    return 返回值;
}
```

引用传参：

```cpp
void update(int& x) {
    x++;
}
```

避免复制大对象：

```cpp
void print_vector(const vector<int>& nums) {
    for (int x : nums) {
        cout << x << ' ';
    }
}
```

### 15.4 vector

```cpp
vector<int> nums;
vector<int> nums(n);
vector<int> nums(n, 初始值);
```

遍历：

```cpp
for (int x : nums) {
    cout << x << ' ';
}

for (int i = 0; i < (int)nums.size(); i++) {
    cout << nums[i] << ' ';
}
```

### 15.5 string

```cpp
string s;
cin >> s;

string line;
getline(cin, line);
```

拼接与截取：

```cpp
string a = "hello";
string b = "world";
string c = a + " " + b;

string part = c.substr(0, 5);
```

### 15.6 unordered_map / unordered_set

```cpp
unordered_map<string, int> count;
count["apple"]++;

unordered_set<int> seen;
seen.insert(10);
```

查找：

```cpp
if (count.count("apple")) {
    cout << count["apple"] << '\n';
}

if (seen.find(10) != seen.end()) {
    cout << "found\n";
}
```

### 15.7 sort 和 lambda

```cpp
sort(nums.begin(), nums.end());
sort(nums.begin(), nums.end(), greater<int>());
```

自定义排序：

```cpp
sort(items.begin(), items.end(), [](const Item& a, const Item& b) {
    return a.score > b.score;
});
```

### 15.8 class / struct

```cpp
struct Point {
    int x;
    int y;
};

class User {
public:
    string name;

    User(string name) : name(name) {}

    void hello() const {
        cout << "hello " << name << '\n';
    }
};
```

---

## 16. STL 常用方法速查表

### 16.1 vector

| 方法 | 作用 | 常见用法 |
| --- | --- | --- |
| `push_back(x)` | 末尾添加元素 | `nums.push_back(10);` |
| `pop_back()` | 删除最后一个元素 | `nums.pop_back();` |
| `size()` | 元素个数 | `nums.size()` |
| `empty()` | 是否为空 | `nums.empty()` |
| `clear()` | 清空数组 | `nums.clear()` |
| `front()` | 第一个元素 | `nums.front()` |
| `back()` | 最后一个元素 | `nums.back()` |
| `begin()` / `end()` | 迭代器范围 | `sort(nums.begin(), nums.end());` |

常见坑：

- `nums[i]` 不会检查越界。
- `nums.size()` 是无符号整数，和 `int` 比较时容易出现警告，刷题可写 `(int)nums.size()`。
- 删除中间元素会移动后面的元素，频繁删除中间元素不适合用 `vector`。

### 16.2 string

| 方法 | 作用 | 常见用法 |
| --- | --- | --- |
| `size()` / `length()` | 字符串长度 | `s.size()` |
| `substr(pos, len)` | 截取子串 | `s.substr(0, 3)` |
| `find(x)` | 查找位置 | `s.find("abc")` |
| `replace(pos, len, str)` | 替换内容 | `s.replace(0, 3, "hi")` |
| `push_back(ch)` | 追加字符 | `s.push_back('a')` |
| `empty()` | 是否为空 | `s.empty()` |

常见坑：

- `find` 找不到会返回 `string::npos`，不是 `-1`。
- `substr(pos, len)` 第二个参数是长度，不是结束下标。
- `char` 用单引号，`string` 用双引号。

### 16.3 unordered_map

| 方法 | 作用 | 常见用法 |
| --- | --- | --- |
| `mp[key]` | 访问或创建键 | `mp[x]++` |
| `count(key)` | 判断键是否存在 | `if (mp.count(x))` |
| `find(key)` | 查找迭代器 | `mp.find(x)` |
| `erase(key)` | 删除键 | `mp.erase(x)` |
| `size()` | 键值对数量 | `mp.size()` |
| `clear()` | 清空 | `mp.clear()` |

常见坑：

- `mp[key]` 如果 key 不存在，会自动创建默认值。
- 只想判断是否存在时，优先用 `count` 或 `find`。
- 哈希表平均 O(1)，但不是严格永远 O(1)。

### 16.4 algorithm

| 函数 | 作用 | 常见用法 |
| --- | --- | --- |
| `sort` | 排序 | `sort(a.begin(), a.end())` |
| `reverse` | 反转 | `reverse(a.begin(), a.end())` |
| `lower_bound` | 找第一个大于等于目标的位置 | `lower_bound(a.begin(), a.end(), x)` |
| `upper_bound` | 找第一个大于目标的位置 | `upper_bound(a.begin(), a.end(), x)` |
| `unique` | 去除相邻重复，返回新末尾 | `a.erase(unique(a.begin(), a.end()), a.end())` |
| `max` / `min` | 求较大/较小值 | `max(a, b)` |

常见坑：

- `lower_bound` 要求区间已经有序。
- `unique` 只移动元素，不会真正缩短容器，通常要配合 `erase`。
- 自定义比较函数必须满足严格弱序，不能写成 `<=`。

---

## 17. 推荐写法 vs 不推荐写法

| 场景 | 推荐写法 | 不推荐写法 | 原因 |
| --- | --- | --- | --- |
| 刷题头文件 | `#include <bits/stdc++.h>` | 手动漏写头文件 | 刷题时更省事 |
| 工程头文件 | 按需 `#include <vector>` | `#include <bits/stdc++.h>` | `bits/stdc++.h` 非标准 |
| 动态数组 | `vector<int>` | 手写 `malloc` 动态数组 | 更安全，自动管理内存 |
| 字符串 | `string` | `char s[100]` | 更容易拼接、比较、截取 |
| 大对象传参 | `const vector<int>&` | `vector<int>` 值传递 | 避免不必要复制 |
| 修改参数 | `int& x` | `int* x` 加解引用 | 引用语义更清楚 |
| 工程命名空间 | `std::vector` | 全局 `using namespace std;` | 减少命名冲突 |
| 排序 | `sort + lambda` | `qsort + 函数指针` | 类型安全，可读性更好 |

补充建议：

- 刷算法时，优先掌握 STL 容器和算法库，比先深挖类和模板更划算。
- 工程代码里，越是公共头文件，越要避免 `using namespace std;`。
- 能用标准库解决的问题，不要急着手写底层结构，除非题目要求你实现它。

---

## 18. 常见编译错误速查

### 18.1 忘记 include

现象：

```txt
error: 'vector' was not declared in this scope
```

原因：没有包含对应头文件，或者没有写 `std::`。

解决：

```cpp
#include <vector>
#include <iostream>
using namespace std;
```

或：

```cpp
std::vector<int> nums;
```

### 18.2 命名空间错误

现象：

```txt
error: 'cout' was not declared in this scope
```

解决：

```cpp
std::cout << "hello\n";
```

或者在刷题代码里写：

```cpp
using namespace std;
```

### 18.3 vector 下标越界

错误写法：

```cpp
vector<int> nums;
nums[0] = 10;
```

原因：`nums` 还是空的，不能直接访问第 0 个元素。

正确写法：

```cpp
vector<int> nums;
nums.push_back(10);
```

或：

```cpp
vector<int> nums(1);
nums[0] = 10;
```

### 18.4 迭代器越界

错误写法：

```cpp
auto it = nums.end();
cout << *it << '\n';
```

原因：`end()` 指向最后一个元素的后一个位置，不能解引用。

正确理解：

```cpp
if (!nums.empty()) {
    cout << nums.back() << '\n';
}
```

### 18.5 比较函数写错

错误写法：

```cpp
sort(nums.begin(), nums.end(), [](int a, int b) {
    return a <= b;
});
```

原因：比较函数不能用 `<=`，应该表达“a 是否应该排在 b 前面”。

正确写法：

```cpp
sort(nums.begin(), nums.end(), [](int a, int b) {
    return a < b;
});
```

### 18.6 引用和指针混淆

指针写法：

```cpp
void add_one(int* x) {
    (*x)++;
}
```

调用：

```cpp
add_one(&num);
```

引用写法：

```cpp
void add_one(int& x) {
    x++;
}
```

调用：

```cpp
add_one(num);
```

迁移建议：如果只是想让函数修改传入变量，C++ 里优先用引用；如果需要表达“可能为空”或动态内存地址，再考虑指针。

---

## 19. 每章练习题补充

### 19.1 基础输入输出

1. 输入两个整数，输出它们的和、差、积。
2. 输入一个字符串，输出它的长度和第一个字符。
3. 输入一行带空格的文本，统计其中字符总数。

### 19.2 vector 和数组

1. 输入 `n` 个整数，存入 `vector<int>`，输出最大值和最小值。
2. 输入 `n` 个整数，删除所有偶数，只保留奇数。
3. 输入 `n` 个分数，计算平均分。

### 19.3 string

1. 输入一个字符串，判断是否包含 `"cpp"`。
2. 输入一个字符串，反转后输出。
3. 输入一个英文句子，把所有空格替换成 `-`。

### 19.4 unordered_map / unordered_set

1. 输入一组数字，统计每个数字出现次数。
2. 判断数组中是否存在重复元素。
3. 写一个 Two Sum：返回两个数的下标，使它们的和等于目标值。

### 19.5 algorithm

1. 输入 `n` 个数，升序排序后输出。
2. 输入 `n` 个数，去重后输出。
3. 在有序数组中查找第一个大于等于目标值的位置。

### 19.6 struct / class

1. 定义 `Student`，包含 `name` 和 `score`，按分数从高到低排序。
2. 定义 `Point`，写一个函数计算它到原点的距离。
3. 定义一个简单 `Counter` 类，支持 `add()` 和 `value()`。

### 19.7 模板

1. 写一个模板函数 `my_max(a, b)`，返回较大值。
2. 写一个模板函数 `print_vector`，能输出 `vector<int>` 和 `vector<string>`。
3. 写一个模板结构 `Pair<T>`，保存两个同类型值。

### 19.8 内存与现代 C++

1. 对比 `new/delete` 和局部对象自动释放的区别。
2. 用 `unique_ptr<int>` 保存一个整数并输出。
3. 写一个函数，说明为什么返回局部对象通常是安全的。


<section class="legacy-comments">
  <h2>评论区</h2>
  <div id="twikoo-article_1778042546856" data-twikoo-path="article_1778042546856"></div>
</section>
