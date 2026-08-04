---
title: "py学习笔记（更新中）"
date: "2026-07-23"
updated: "2026-08-04"
categories:
  - "技术学习"
index_img: "/images/covers/custom/20260723014916-qq-jie-tu-20260723014829.webp"
---
## 一、可变参数

### 1.可变位置参数*args

*args将传入的位置参数打包为一个元组

```py
def sum_all(*args):
    print(f"args的类型: {type(args)}")  # <class 'tuple'>
    print(f"args的内容: {args}")        # (1, 2, 3, 4)
    return sum(args)

print(sum_all(1, 2, 3, 4))  # 输出: 10
```

```py
def print_names(*args):
    for i, name in enumerate(args, 1):  
        print(f"{i}. {name}")

print_names("小明", "小红", "小华")
# 输出:
# 1. 小明
# 2. 小红
# 3. 小华
```
注：enumerate() 是 Python 内置函数，用于在遍历可迭代对象时同时获取索引和值。

### 2.可变关键字参数 **kwargs

**kwargs 将传入的关键字参数打包成一个字典

```py
def show_info(**kwargs):
    print(f"kwargs的类型: {type(kwargs)}")  # <class 'dict'>
    print(f"kwargs的内容: {kwargs}")        # {'name': '张三', 'age': 25, 'city': '北京'}
    
    for key, value in kwargs.items():
        print(f"{key}: {value}")

show_info(name="张三", age=25, city="北京")
# 输出:
# name: 张三
# age: 25
# city: 北京
```

### 3.混合使用

顺序必须是：普通参数 → *args → **kwargs

```py
def mixed(param1, param2, *args, default="默认值", **kwargs):
    print(f"普通参数: {param1}, {param2}")
    print(f"*args: {args}")
    print(f"默认参数: {default}")
    print(f"**kwargs: {kwargs}")

mixed(1, 2, 3, 4, 5, default="自定义", name="李四", age=30)
# 输出:
# 普通参数: 1, 2
# *args: (3, 4, 5)
# 默认参数: 自定义
# **kwargs: {'name': '李四', 'age': 30}
```

## 二、lambda表达式/匿名函数

lambda真正适合的场景是：

>某个地方需要传入一个简单函数，而这个函数只用一次。

### 1.语法

```py
lambda 接收参数列表: 返回值表达式
```

冒号后面的表达式计算出什么，函数就自动返回什么。

注：函数调用也属于表达式，所以你也可以在返回值表达式里调用一个函数，那么lambda就会返回这个函数的返回值。

因为py中函数也是对象，所以lambda还可以返回一个函数，就像下面这样：

```py
create_multiplier = lambda number: lambda value: value * number
```

这个写法等价于闭包：

```py
def create_multiplier(number):
    def multiply(value):
        return value * number

    return multiply
```

### 2.调用lambda函数的方式

#### 先保存，再调用

```py
double = lambda x: x * 2
#这里lambda表达式会创建一个函数对象，然后变量double指向这个函数
result = double(10)

print(result)
```
#### 创建后立即调用

```py
result = (lambda x: x * 2)(10)

print(result)
```

### 3.参数形式

#### 单个参数

```py
# 基本运算
square = lambda x: x ** 2
print(square(5))  # 输出: 25

# 字符串处理
to_upper = lambda s: s.upper()
print(to_upper("hello"))  # 输出: HELLO

# 类型转换
to_int = lambda s: int(s) if s.isdigit() else 0
print(to_int("123"))  # 输出: 123
print(to_int("abc"))  # 输出: 0
```

#### 多个参数

```py
# 两个参数
add = lambda x, y: x + y
print(add(10, 20))  # 输出: 30

# 三个参数
multiply_three = lambda x, y, z: x * y * z
print(multiply_three(2, 3, 4))  # 输出: 24

# 多个参数做复杂操作
distance = lambda x1, y1, x2, y2: ((x2 - x1)**2 + (y2 - y1)**2)**0.5
print(distance(0, 0, 3, 4))  # 输出: 5.0

# 计算 BMI
bmi = lambda weight, height: weight / (height ** 2)
print(bmi(70, 1.75))  # 输出: 22.86
```

#### 默认参数
```py
# 带默认参数的 lambda
greet = lambda name, greeting="Hello": f"{greeting}, {name}!"
print(greet("Alice"))           # 输出: Hello, Alice!
print(greet("Bob", "Hi"))       # 输出: Hi, Bob!

# 默认参数做计算
power = lambda x, exp=2: x ** exp
print(power(5))     # 输出: 25
print(power(2, 3))  # 输出: 8

# 默认参数为可变对象（注意陷阱）
add_item = lambda lst=[], item=0: lst.append(item) or lst
print(add_item([1, 2], 3))  # 输出: [1, 2, 3]
print(add_item(item=5))     # 输出: [5]
print(add_item(item=10))    # 输出: [5, 10]  # 注意：此处默认参数的列表每次调用后都会更新
```

#### 无参数

```py
# 无参数
get_five = lambda: 5
print(get_five())  # 输出: 5

# 无参数但执行复杂操作
get_current_time = lambda: __import__('time').time()
print(get_current_time())

# 立即执行的无参数 lambda
result = (lambda: 3.14159)()
print(result)  # 输出: 3.14159
```

## 三、迭代器

### 1.迭代器只能依次消费

>迭代器内部会记录“当前走到哪里了”。每取出一个元素，位置就向后移动一步；已经取出的元素通常不能回退，全部取完后，迭代器就耗尽了。

即迭代器已经把这个元素取出来了，并把当前位置向后移动了。

“消费”指的是消耗迭代器中的遍历进度，原对象中的原始数据并没有被改变。

#### for循环也在消费迭代器

for循环的底层逻辑大概是：

```py
iterator = iter(z)

while True:
    try:
        item = next(iterator)
        print(item)
    except StopIteration:
        break
```
也就是说，for 循环也会不断调用 next()。

#### list()，map(),filter()也在消费迭代器
比如：

list(z)不是查看一下z，而是不断调用`next(z)`，直到取完为止，近似相当于：

```py
result = []

while True:
    try:
        item = next(z)
        result.append(item)
    except StopIteration:
        break
```

因此这会造成，两次`print(list(z))`之后，第二次打印出来的是空列表

#### 为什么zip()不直接返回可迭代对象？

因为返回迭代器有一个很大的优点：不需要一开始就把所有结果全部存进内存，而是需要一个时才生成一个。

这种方法也叫**惰性计算**，也就是用到时再计算。优点是节省内存，适合大量数据，代价是它一般只能向前走，不能随意回退。



### 2.生成器

生成器是py中一种按需产生数据的迭代器，每次需要一个值时，才计算并返回一个值；下次继续从上次暂停的位置运行。即**惰性计算**。

#### 生成器主要创建方法

1. 生成器表达式
2. 带有yield的生成器函数

## 四、列表推导式

### 1.基础语法
```py
[表达式 for 变量 in 可迭代对象]
```
可以理解为：

>从“可迭代对象”中依次取出每个元素，交给“变量”，计算“表达式”，然后把每次计算的结果放进新列表。

若变量在前面的表达式中未使用到，那么表达式后面的部分可以理解为是将`表达式`重复了`变量`次

### 2.带筛选条件语法
带筛选条件：

- if放在后面：筛选元素
```py
[表达式 for 变量 in 可迭代对象 if 条件]
```
- if-else放在前面：将符合条件的元素转换为相应结果
```py
[结果1 if 条件 else 结果2 for 变量 in 可迭代对象]
```

### 3.列表推导式中调用函数
可以在表达式部分调用函数，例如：

```py
def square(x):
    return x * x

result = [square(i) for i in range(5)]
```

### 4.一个坑
创建二维列表千万不能用 `[[0]*4]*3`。因为 `*3` 复制的是引用，三行指向的是同一个列表对象，修改一行其他行也会跟着变。用列表推导式 `[[0]*cols for _ in range(rows)]` 才是正确做法，每行都是独立的列表对象。

例如：

```py
grid = [[0] * 4] * 3

grid[0][1] = 5

print(grid)
```
输出：

`[[0, 5, 0, 0],

 [0, 5, 0, 0],

 [0, 5, 0, 0]]`

## 五、常用函数

### 1.range()
生成一个整数范围，常用于for循环，包含范围为**前闭后开**

```py
range(stop)
range(start, stop)
range(start, stop, step)
```
- 返回值：返回一个range对象
- 步长step不能为0

### 2.enumerate()

同时获得下标和元素

#### 基本语法

```py
enumerate(iterable, start=0)
```
参数：

- iterable：需要遍历的可迭代对象
- start：编号从哪个数字开始，默认从 0 开始

返回值：

- 一个enumerate对象(可迭代对象)
- 遍历时，每次产生一个`(编号，元素)`元组



### 3.zip()

#### 基本用法

`zip()` 是 Python 中用来把多个可迭代对象中相同位置的元素配对组合的函数。

最常见的场景是：同时遍历两个或多个列表。可以把它理解成把两个列表“拉上拉链”。


```py
["小明", "小红", "小刚"]
   ↓       ↓       ↓
[  90,     85,      92 ]

组合后：

[("小明", 90), ("小红", 85), ("小刚", 92)]
```
**注：**

- `zip()`返回的是一个**迭代器对象**
- 可以组合不同类型的可迭代对象



#### 配合for循环使用

```py
names = ["小明", "小红", "小刚"]
scores = [90, 85, 92]

for name, score in zip(names, scores):
    print(name, score)
```

#### 可同时组合三个或更多对象

```py
names = ["小明", "小红", "小刚"]
scores = [90, 85, 92]
ages = [18, 19, 18]

result = list(zip(names, scores, ages))

print(result)
```

#### 可迭代对象长度不同时

`zip()`会以最短的可迭代对象为准

#### 解压操作

例如：

```py
students = [
    ("小明", 90),
    ("小红", 85),
    ("小刚", 92)
]

names, scores = zip(*students)

print(names)
print(scores)

得到：
("小明", "小红", "小刚")
(90, 85, 92)
```

通过这一解压操作还能用于实现**矩阵转置**：

```py
matrix = [
    [1, 2, 3],
    [4, 5, 6]
]

result = list(zip(*matrix))

print(result)

得到：
[(1, 4), (2, 5), (3, 6)]
```
若想让结果仍为二维列表：

```py
result = [list(row) for row in zip(*matrix)]

print(result)

得到：
[
    [1, 4],
    [2, 5],
    [3, 6]
]
```

### 4.map()

将指定函数依次应用于可迭代对象中的每一个元素

#### 基本语法

```py
map(function, iterable)
```
返回值：一个map迭代器对象

#### 可处理多个可迭代对象

```py
map(function, iterable1, iterable2, ...)
```

例如：

```py
numbers1 = [1, 2, 3]
numbers2 = [10, 20, 30]

result = map(lambda x, y: x + y, numbers1, numbers2)

print(list(result))
```

若多个可迭代对象长度不同，map()会在最短的可迭代对象结束时停止。

#### 例子

`map(int, str(n))`会依次把字符串中的每个字符转换为整数。

```py
n = 124

str(n)                    # "124"
map(int, str(n))          # 依次产生 1、2、4
sorted(..., reverse=True) # [4, 2, 1]
```


### 5.filter()

对每个元素进行条件判断，只保留判断结果为真的元素。

#### 基本语法

```py
filter(function, iterable)
```
判断函数function应该接受一个元素，并返回一个布尔值，但判断函数返回的也不一定非得是布尔值，因为py会根据一个值的“真假”判断是否保留元素，常见假值包括：

```py
False
None
0
0.0
""
[]
{}
set()
```
其他大多数值都是真值。

**注：**`filter()`的第一个参数还可以直接写成None，此时会自动删除所有假值。


### 6.sorted()

对可迭代对象进行排序，返回一个新的列表

```py
sorted(iterable, key=None, reverse=False)
```
- 参数：key为指定排序依据，reverse为是否降序，默认`False`表示升序
- 返回值：返回一个新的**列表**

注：`sorted()`与列表的`.sort()`不同，后者会修改原列表，且返回`None`。



### 7.reversed()

反向遍历一个序列，不会修改原序列

```py
reversed(sequence)
```

- 参数：sequence为列表、元组、字符串、range等可逆序对象
- 返回值：返回一个反向迭代器


### 8.round()

对数字进行舍入

```py
round(number, ndigits=None)
```

- 参数：number为需要舍入的数字，ndigits为保留的小数位数，省略时取整
- 返回值：返回舍入后的数字

### 9.divmod()

同时计算整除的商和余数

```py
divmod(a, b)
```

- 参数：a为被除数，b为除数
- 返回值：返回一个二元组`(商，余数)`

### 10.ord()
把单个字符转换为ASCII码

### 11.chr()
把ASCII码转换为字符

```py
# 经典用法：用数组统计字母频率
text = "abracadabra"
freq = [0] * 26
for ch in text:
    freq[ord(ch) - ord('a')] += 1

# 输出每个出现过的字母及其频率
for i in range(26):
    if freq[i] > 0:
        print(f"{chr(i + ord('a'))}: {freq[i]}", end="  ")
# 输出：a: 5  b: 2  c: 1  d: 1  r: 2
print()
```
`ord(ch) - ord('a')` 这个技巧把小写字母映射到 0~25，非常适合用数组代替哈希表来统计字母频率。刷题时很常用。


### 12.max(),min()

返回可迭代对象中的最值，或多个位置参数中的最值

#### 基本语法

```py
max(iterable, *, key=None, default=...)

或者：

max(arg1, arg2, *args, key=None)
```

参数：

- iterable：需要查找最大值的可迭代对象，例如列表、元组、集合等
- arg1, arg2, ...：也可以直接传入多个值进行比较
- key：指定比较规则，默认直接比较元素本身
- default：当 iterable 为空时返回的默认值

返回值：

- 返回最大的那个**原元素**
- 如果使用 key，根据 key(element) 的结果进行比较，但返回的仍然是**原元素**，例如：
    ```py
    max([-10, 3, 5], key=abs) #返回-10
    ```

min()同理

### 13.pow()

进行幂运算

#### 基本语法

```py
普通幂：
pow(base, exp)

带模运算：
pow(base, exp, mod)
```

返回值：

- 带模运算：`base`^`exp` mod `mod`

#### 快速幂取模

```py
# pow(a, b, mod) 快速幂取模：计算 a^b % mod
# 这比先算 a**b 再取模快得多，不会产生超大中间值
# 刷题中经常遇到"答案对 10^9+7 取模"
MOD = 10**9 + 7
result = pow(2, 100, MOD)
print(f"2^100 mod (10^9+7) = {result}")

# 对比：直接用 ** 也能算，但数字太大时效率低
```

### 14.math模块

```py
import math

# 开平方
print(f"sqrt(9) = {math.sqrt(9)}")
print(f"sqrt(2) = {math.sqrt(2):.4f}")

# 向上取整、向下取整
print(f"ceil(3.2) = {math.ceil(3.2)}")    # 4
print(f"floor(3.8) = {math.floor(3.8)}")  # 3

# 最大公约数
print(f"gcd(12, 8) = {math.gcd(12, 8)}")  # 4
# Python 3.9+ 支持多个参数
print(f"gcd(12, 8, 6) = {math.gcd(12, 8, 6)}")  # 2

# 对数
print(f"log2(8) = {math.log2(8)}")     # 3.0
print(f"log(e) = {math.log(math.e)}")  # 1.0
print(f"log10(1000) = {math.log10(1000)}")  # 3.0

# 无穷大常量
print(f"math.inf = {math.inf}")
print(f"5 < math.inf ? {5 < math.inf}")
```
**注：**

- python中表示无穷大还有另一种方式`float('inf')`，表示负无穷时改为`-inf`即可
- python中的整除`//`是向下取整


### 15.进制转换

#### bin()

将整数转换为二进制**字符串**，不改变原数字

```py
bin(x)
```

例如：

```py
x = bin(42)

print(x)
print(type(x))

#输出：
# 0b101010
# <class 'str'>
```

注：

1. `0b`是二进制前缀
2. 负数也可以，只不过返回的是带负号的字符串，不是计算机内部补码表示
3. 

#### oct()

将整数转换为八进制字符串

注：

1. `0o`表示八进制


#### hex()

将整数转换为十六进制字符串

注：

1. `0x`表示十六进制
2. 显示时默认显示小写字母


#### int()

创建或转换成整数

```py
int(x)

int(string, base)
```

参数：

- base：字符串当前使用的是几进制
  **注**：若`base=0`，则py会根据前缀自动判断进制

返回值：

- int整数



## 六、常用方法

### 1.str.strip()
删除字符串开头和结尾的空白字符或指定字符，即只删除两端，不删除中间。

```py
string.strip(chars=None)
```

- 参数：chars为要删除的字符集合，默认删除空格、换行、制表符等
- 返回值：返回处理后的新字符串
- 相关方法：
  ```py
    text.lstrip()  # 只删除左侧
    text.rstrip()  # 只删除右侧
  ```

### 2.str.split()
按照指定分隔符拆分字符串

```py
string.split(sep=None, maxsplit=-1)
```

- 参数：sep为分隔符，默认按照任意空白字符拆分；maxsplit为最多拆分多少次，默认全部拆分
- 返回值：返回一个字符串**列表**

### 3.str.replace()
将字符串中的指定内容替换成新内容

```py
string.replace(old, new, count=-1)
```

- 参数：old为要被替换的内容，new为替换后的内容，count为最多替换多少次，默认全部替换

### 4.str.join()
使用指定字符串，将多个字符串连接起来

```py
separator.join(iterable)
```
- 参数：separator为元素之间使用的连接符；iterable为包含字符串的可迭代对象
- 返回值：返回连接后的新字符串

### 5. .sort()

#### 使用元组进行多级排序

元组在比较时会先比第一个元素，相等再比第二个，以此类推，想要**降序**就取负号

例如：

```py
students = [("Alice", 88), ("Bob", 95), ("Charlie", 88), ("Diana", 95)]
students.sort(key=lambda x: (-x[1], x[0]))
# 输出：[('Bob', 95), ('Diana', 95), ('Alice', 88), ('Charlie', 88)]
print(students)
```

### 6.dict.get()

根据键获取字典中的值；如果键不存在，不会报错，而是返回一个默认值。

```py
dict.get(key, default)
```

- 参数：key为要查找的键，必填；default为键不存在时返回的默认值，可选，默认是`None`
- 返回值：default或None

#### 频率统计的经典写法

```py
freq[ch] = freq.get(ch, 0) + 1
```

## 七、异常处理语法

### 1.完整语法结构

```python
try:
    # 尝试执行的代码
    result = 10 / 0
    
except ZeroDivisionError:
    # 捕获特定异常
    print("除数不能为零")
    
except (TypeError, ValueError) as e:
    # 捕获多种异常
    print(f"发生错误: {e}")
    
except Exception as e:
    # 捕获所有其他异常
    print(f"未知错误: {e}")
    
else:
    # 没有异常时执行
    print("计算成功!")
    
finally:
    # 无论是否异常都会执行
    print("这是最后执行的代码")
```

### 2.常见异常类型

|异常类型|说明|示例|
|---|--|---|
|ZeroDivisionError	|除零错误	|1/0|
|TypeError	|类型错误	|'1' + 1|
|ValueError	|值错误	|int('abc')|
|IndexError|	索引错误|	[1][10]|
|KeyError|	键错误	|{}['key']|
|FileNotFoundError|	文件不存在|	open('nofile.txt')|


```py
BaseException
├── SystemExit
├── KeyboardInterrupt  
├── GeneratorExit
└── Exception  # ← 我们通常处理的异常
    ├── TypeError      # 类型错误
    ├── ValueError     # 值错误
    ├── KeyError       # 键错误
    ├── FileNotFoundError
    └── ... (其他所有异常)
```

### 3.自定义异常
```py
# 定义自定义异常
class AgeError(Exception):
    """年龄异常类"""
    pass

class UnderAgeError(AgeError):
    """年龄太小异常"""
    pass

class OverAgeError(AgeError):
    """年龄太大异常"""
    pass

def check_age(age):
    if age < 0:
        raise AgeError("年龄不能为负数")
    elif age < 18:
        raise UnderAgeError("年龄太小，需要满18岁")
    elif age > 120:
        raise OverAgeError("年龄太大，超出范围")
    else:
        print(f"年龄 {age} 验证通过")

# 使用自定义异常
try:
    check_age(15)
except UnderAgeError as e:
    print(f"未成年: {e}")
except OverAgeError as e:
    print(f"超龄: {e}")
except AgeError as e:
    print(f"年龄错误: {e}")
```

## 八、算法题常用技巧

### 1.ACM模式IO模版

#### 处理输入

最基础的套路：`input()` 读一行，`split()` 按空格切分，`map(int, ...)` 批量转整数：

```py
# 读取一个整数
n = int(input())

for i in range(n):
    # 读取一行中的两个整数
    a, b = map(int, input().split())
    print(a + b)
# 输出：
# 3
# 7
# 11
```
如果一行有很多数字需要存到列表里：

```py
nums = list(map(int, input().split()))
```

#### sys.stdin快读(大数据量)
当输入数据量很大（比如几十万行），input() 可能会超时。这时候需要用 sys.stdin 来加速读取。方法很简单，只需要在代码开头加一行：

```py
import sys
# 用 sys.stdin.readline 替换内置的 input
input = sys.stdin.readline

# 后面的代码跟之前完全一样
n = int(input())
for i in range(n):
    a, b = map(int, input().split())
    print(a + b)
```

**注意：** `sys.stdin.readline` 读取的字符串末尾会带一个换行符 \n，但 split() 和 int() 会自动处理掉，所以大部分情况不需要额外操心。只有在直接拿字符串比较的时候要注意用 strip() 去掉末尾的换行。

#### 处理多组输入/EOF
有些题目不告诉你有多少组输入，而是读到文件末尾（EOF）为止。这时候用 try-except 捕获异常。try 块中的代码如果出错，程序不会崩溃，而是跳到 except 块继续执行。这里利用这个机制检测输入结束：没有更多输入时读取会出错，被 except 捕获后执行 break 退出循环：

```py
import sys
input = sys.stdin.readline

while True:
    try:
        a, b = map(int, input().split())
        print(a + b)
    except:
        break
# 输出：
# 3
# 7
# 11
```

当 input() 读到 EOF 时，会返回空字符串，split() 得到空列表，map(int, ...) 拆包就会抛异常，被 except 捕获后 break 跳出循环。

还有一种更简洁的写法，直接用 sys.stdin 遍历每一行：

```py
import sys
for line in sys.stdin:
    a, b = map(int, line.split())
    print(a + b)
```

sys.stdin 本身就是一个可迭代对象，读完所有行自动结束，连 try-except 都不用写。

### 2.排序

#### cmp_to_key

##### 必须两两比较才能定义顺序时使用
python中的排序通常使用key参数，大部分排序用 key 就够了，但有些场景需要两两比较才能定义顺序，比如经典的"最大数拼接"问题。这时候需要 cmp_to_key。

cmp_to_key函数就是把自定义的比较函数转化为key函数，便于排序。

一个标准的比较函数通常写成：

```py
def cmp(a, b):
    if a < b:
        return 负数
    elif a > b:
        return 正数
    else:
        return 0
```
返回值：

- 负数：a在前
- 0：两者相等
- 正数：a在后

##### 例子：最大数拼接

```py
from functools import cmp_to_key

# 例子：把数字拼接成最大的数
# 比如 [3, 30, 34] 应该拼成 "34330"
nums = [3, 30, 34, 5, 9]

# 自定义比较函数：比较 a+b 和 b+a 拼接后谁更大
# 返回负数表示 a 排前面，正数表示 b 排前面
def compare(a, b):
    if a + b > b + a:
        return -1  # a 排前面
    elif a + b < b + a:
        return 1   # b 排前面
    else:
        return 0

str_nums = [str(x) for x in nums]
str_nums.sort(key=cmp_to_key(compare))
result = "".join(str_nums)
print(f"最大拼接数：{result}")
# 输出：最大拼接数：953430
```

## 九、面向对象基础

面向对象的思路是：

>把一组相关的数据以及操作这些数据的函数，封装为一个整体

这个整体称为`对象`，对象所属的类型称为`类`

### 1.类的定义

用`class`关键字定义一个类，类就是一个模版，定义了这类对象有什么`属性`(数据)和什么`方法`(操作)

```py
class Student:
    # __init__ 初始化已经创建好的对象，创建对象时自动调用
    # self 指向当前正在操作的那个对象本身，类似其他语言的 this
    def __init__(self, name, age):
        # 给对象绑定属性
        self.name = name
        self.age = age
        self.scores = []#Python 不要求你提前声明对象有哪些属性，所以 scores 可以直接在赋值时创建。

    # 定义方法：添加成绩
    def add_score(self, score):
        self.scores.append(score)

    # 定义方法：计算平均分
    def average(self):
        if not self.scores:
            return 0
        return sum(self.scores) / len(self.scores)

# 创建对象（实例化）
alice = Student("Alice", 20)
bob = Student("Bob", 21)

# 调用方法
alice.add_score(90)
alice.add_score(85)
alice.add_score(92)

bob.add_score(78)
bob.add_score(88)

# 访问属性和调用方法
# 输出：Alice 的平均分：89.0
print(f"{alice.name} 的平均分：{alice.average()}")
# 输出：Bob 的平均分：83.0
print(f"{bob.name} 的平均分：{bob.average()}")
```

py的对象属性是完全开放的，可以随时读取和修改，也可以动态添加新属性


#### 实例属性与类属性

##### a.两个属性的区别

- 实例属性：通过`self.xxx`设置，每个实例都有独立的数据
- 类属性：通常用于所有实例共享的数据
```py
class Student:
    school = "BUPT" #类属性
    def __init__(self, name):
        self.name = name  #实例属性
        self.scores = []
alice = Student("Alice")
bob = Student("Bob")

alice.scores.append(100)

print(alice.scores)  # [100]
print(bob.scores)    # []
print(Student.school)  # BUPT
print(alice.school)    # BUPT
print(bob.school)      # BUPT
```
实例变量通常用于保存每个对象各自独有的数据

##### b.通过实例赋值不会直接修改类属性
```py
alice.school = "Alice 的学校"

print(alice.school)    # Alice 的学校
print(bob.school)      # BUPT
print(Student.school)  # BUPT
```
此处**并未修改**`Student.school`，而是给 alice 新增了一个同名实例属性。

属性查找大致是：

>先找 alice 自己的实例属性
        ↓
找不到再找 Student 类属性
        ↓
再找父类中的属性

**当实例属性与类属性同名时，实例属性优先**

##### c.一个坑：不能把可变对象写成类属性

类属性如果是列表、字典、集合等可变对象，会被实例共享，这是官方教程中特别强调的常见错误。

```py
class Student:
    def __init__(self, name):
        self.name = name
        self.scores = []
    #不能写成
    #scores = []
```

#### 属性访问与“封装”

1. 单下划线`_name`：
   表示这是内部属性，外部代码最好不要直接操作，但实际上仍可以访问。仅为约定，不是强制限制。
   ```py
    self._age = age
   ```
2. 双下划线`__name` ：
   双下划线主要是为了避免子类属性重名，不是安全机制，也不等于真正私有。

### 2.py中的三种方法

#### 实例方法

第一个参数是`self`，用于操作某个具体对象

适用场景：方法需要读取或修改实例属性

#### 类方法
使用`@classmethod`，第一个参数通常写成`cls`，表示当前类

```py
class Student:
    school = "BUPT"

    def __init__(self, name, age):
        self.name = name
        self.age = age

    @classmethod
    def from_text(cls, text):
        name, age = text.split(",")
        return cls(name, int(age))#此处就相当于通过给类名加括号来创建对象
```
调用：

```py
alice = Student.from_text("Alice,20")

print(alice.name)  # Alice
print(alice.age)   # 20
```

整个过程详细解释：

1. 因为 from_text 被 @classmethod 修饰，Python 会自动把 Student 类传给第一个参数 cls。所以这里的cls本质上就是Student，即
   ```py
    cls = Student 
    text = "Alice, 20"
   ```
2. 然后拆分字符串，转换年龄类型
3. 接着创建对象，`return cls(name, int(age))`等价于`return Student("Alice", 20)`，这会自动调用`Student.__init__(新对象, "Alice", 20)`
4. 最终得到：
   ```py
   student.name   # "Alice"
    student.age    # 20
    ```

##### 为什么不直接写` return Student(name, int(age))`

使用cls的核心优势是：

>谁调用这个类方法，就创建谁的对象

#### 静态方法

使用`@staticmethod`，不会自动接收 self 或 cls。

```py
class Student:
    @staticmethod
    def is_valid_score(score):
        return 0 <= score <= 100
```
调用：

```py
print(Student.is_valid_score(90))   # True
print(Student.is_valid_score(120))  # False
```
它本质上更像一个普通函数，只是逻辑上和Student类关系密切，所以放在类里面。


### 3.继承

#### 基础语法

继承就是在已有类的基础上扩展。子类自动拥有弗雷德所有属性和方法，还可以添加新的或者重写已有的。

```py
# 父类
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return "..."

# 子类：括号里写父类名
class Cat(Animal):
    def speak(self):
        return "喵~"

class Dog(Animal):
    def speak(self):
        return "汪！"

# 子类自动拥有父类的 __init__，所以可以传 name
cat = Cat("小花")
dog = Dog("旺财")

# 输出：小花 说：喵~
print(f"{cat.name} 说：{cat.speak()}")
# 输出：旺财 说：汪！
print(f"{dog.name} 说：{dog.speak()}")
```

1. Cat(Animal) 表示 Cat 继承自 Animal。Cat 没有定义 `__init__`，所以自动用 Animal 的。
2. Cat 重写了 speak() 方法，调用时会用 Cat 自己的版本。

#### 扩展`__init__`

如果子类需要在父类的基础上扩展 `__init__`，可以用 super() 调用父类的方法：

```py
class Animal:
    def __init__(self, name):
        self.name = name

    def info(self):
        return f"名字：{self.name}"

class Pet(Animal):
    def __init__(self, name, owner):
        # 先调用父类的 __init__，设置 name
        super().__init__(name)
        # 再设置子类特有的属性
        self.owner = owner

    # 重写 info 方法，在父类基础上扩展
    def info(self):
        # 调用父类的 info 方法
        base_info = super().info()
        return f"{base_info}，主人：{self.owner}"

pet = Pet("小白", "张三")
# 输出：名字：小白，主人：张三
print(pet.info())
```

super() 返回一个代理对象，通过它可以调用父类的方法。`super().__init__(name)` 就是调用父类 Animal 的 `__init__`，确保 name 属性被正确设置，然后子类再添加自己的 owner 属性。

### 4.魔术方法

以双下划线开头和结尾的特殊方法，由py在特定场景下自动调用

### 5.装饰器与with语句

#### 函数也是对象
在py中，函数是一个真正的对象，只要是后面可以加()的，都是可调用对象。

所以函数可以直接返回值，也可以作为值赋给变量，也可以作为参数传递，也可以作为返回值。

装饰器能够成立，其根本原因为：

>函数可以接收另一个函数，也可以返回一个新函数

#### 闭包

闭包就是：

>内部函数引用了外部函数的变量，即使外部函数已经执行完毕，内部函数仍然保留着这些变量所处的环境。

从更准确的角度说，闭包是：

**内部函数，加上它所记住的外部变量。**

例如：

```py
def outer():
    message = "你好"

    def inner():
        print(message)

    return inner
#调用：
func = outer()
func()
#输出：你好
```

执行过程：

1. 调用外层函数：
    ```py
    func = outer()
    ```

    py此时进入`outer()`：
    ```py

    message = "你好"
    ```

    然后创建内部函数：
    ```py
    def inner():
        print(message)
    ```

    最后：
    ```py
    return inner
    ```

    注意到不是`return inner()`，`inner()`表示立即调用函数，而`inner`表示函数对象本身

    故`func = outer()`实际上可以理解为`func = inner`
2. 调用内部函数：
    `func()`相当于调用`inner()` ，而`inner()`中需要使用`message`，但是`inner`自己内部没有定义`message`，于是它会去外层寻找，然后找到`message = "你好"`。
    虽然`outer()`已经运行结束，但是`inner`仍然保存着对这个变量的引用，因此可以继续使用它。

##### a.什么情况下才叫闭包

一般需要同时满足下面三个条件：

1. 存在一个外层函数
2. 外层函数里面定义了一个内层函数
3. 内层函数使用了外层函数的变量，并被返回或传递出去


##### b.`nonlocal`是干什么的

```py
def create_counter():
    count = 0

    def counter():
        count += 1
        return count

    return counter

#运行后会报错：UnboundLocalError
```

原因是只要函数内部出现：`count = ···`，py就会默认认为`count`是这个函数自己的局部变量，但执行右边的`count+1`时，这个局部变量还没有值，所以报错。

这个时候加上`nonlocal count`，就是告诉py，这里的`count`不是内层函数自己的变量，而是外层函数里的那个`count`。

```py
def create_counter():
    count = 0

    def counter():
        nonlocal count
        count += 1
        return count

    return counter
```

##### c.为什么每个闭包能保存自己的数据

仍然以上面的例子举例：

```py
def create_counter():
    count = 0

    def counter():
        nonlocal count
        count += 1
        return count

    return counter
```
假如此时分别创建两个计数器：

```py
counter1 = create_counter()
counter2 = create_counter()

print(counter1())
print(counter1())
print(counter2())
print(counter1())
print(counter2())
# 输出：
# 1
# 2
# 1
# 3
# 2
```

因为每调用一次`create_counter()`都会创建一套新的环境，和使用类创建多个对象有点类似，每个对象拥有自己的属性，而闭包则是每个函数拥有自己记住的外层变量。

##### d.闭包的延迟绑定陷阱

```py
functions = []

for i in range(3):
    functions.append(lambda: i)

print(functions[0]())
print(functions[1]())
print(functions[2]())
```

输出不是012，而是222。

因为这些lambda记住的不是创建函数那一刻i当前的具体值，而是变量i本身，是对变量i的引用。

延迟绑定可以理解为：

>函数不是在创建时马上把i的值抄下来，而是在真正执行时再去查i现在是多少。

解决方法：利用默认参数：

```py
functions = []

for i in range(3):
    functions.append(lambda i=i: i)
```
使用默认参数来保存每次创建函数时变量i的值。

#### 装饰器

装饰器适合用来处理当多个函数都需要添加某个公共功能的情况，这样就不用在每个函数里重复写相同代码。

##### 基础语法
创建一个装饰器：

```py
def decorator(func):
    def wrapper(*args, **kwargs):
        # 调用前逻辑
        ·····
        result = func(*args, **kwargs)

        # 调用后逻辑
        ·····
        return result

    return wrapper
```
注意到最后返回的是`wrapper`而不是`wrapper()`，也就是只让`func`指向了`wrapper`。

装饰器的核心公式：

```py
原函数 = 装饰器(原函数)
```

比如说下面这个timer函数，就是一个装饰器。

```py
import time

def timer(func):
    """一个计时装饰器，测量函数的执行时间"""
    # wrapper 用 *args, **kwargs 接收所有参数
    # 再原样传给原函数，这样不管原函数有几个参数都能通用
    def wrapper(*args, **kwargs):
        start = time.time()#获取当前时间
        # 调用原函数
        result = func(*args, **kwargs)
        end = time.time()#获取当前时间，也就是原函数执行完之后的当前时间
        # 每个函数都有 __name__ 属性，记录了函数的名字
        print(f"{func.__name__} 执行耗时：{end - start:.4f} 秒")
        return result
    return wrapper

# 手动使用装饰器：用 timer 包装 slow_add
def slow_add(a, b):
    # time.sleep(0.1) 暂停 0.1 秒，模拟耗时操作
    time.sleep(0.1)
    return a + b

# 把 slow_add 传给 timer，得到包装后的版本
slow_add = timer(slow_add)

# 调用的是 wrapper，它会先计时，再调用原函数，再打印耗时
result = slow_add(1, 2)
# 输出类似：slow_add 执行耗时：0.10xx 秒
# 输出：结果：3
print(f"结果：{result}")
```

timer接收一个函数func，返回一个新函数wrapper，wrapper在调用func前后加了计时逻辑，最后slow_add = timer(slow_add)把原函数替换成包装后的版本。

##### a.@语法糖

```py
import time

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} 执行耗时：{end - start:.4f} 秒")
        return result
    return wrapper

# 用 @ 语法糖，等价于 slow_add = timer(slow_add)
@timer
def slow_add(a, b):
    time.sleep(0.1)
    return a + b

@timer
def slow_multiply(a, b):
    time.sleep(0.2)
    return a * b

# 输出类似：slow_add 执行耗时：0.10xx 秒
r1 = slow_add(1, 2)
# 输出：3
print(r1)

# 输出类似：slow_multiply 执行耗时：0.20xx 秒
r2 = slow_multiply(3, 4)
# 输出：12
print(r2)
```

@timer写在函数定义上方，py在定义函数后自动执行`slow_add = timer(slow_add)`

##### b.为什么装饰器需要嵌套函数

如果直接写：

```py
def timer(func):
    start = time.time()
    result = func()
    end = time.time()
    print(end - start)
    return result
```
的话，这样在执行`timer(slow_add)`的时候，就会立即调用原函数。

我们真正需要的是，`timer(slow_add)`先生成一个新函数，等以后调用这个新函数时，再执行计时逻辑。所以需要分成两个阶段：

```py
装饰阶段：
slow_add = timer(slow_add)
生成 wrapper，但不执行原函数

调用阶段：
slow_add(1, 2)
执行 wrapper，再由 wrapper 调用原函数
```
装饰器实际上运用了闭包，此处的闭包为：`闭包 = wrapper函数 + 它记住的原函数func`，而此处的func指向原来的slow_add。

##### c.functoools.wraps

装饰器有个小问题：包装之后，原函数的名字和文档字符串会丢失。

```py
def my_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def hello():
    """这是 hello 函数的文档"""
    print("Hello!")

# 原函数的名字和文档丢失了
# 输出：wrapper（应该是 hello）
print(hello.__name__)
# 输出：None（应该是文档字符串）
print(hello.__doc__)
```

因为hello实际上已经被替换成了wrapper，所以__name__和__doc__都是wrapper的，这在调试的时候会造成误解。

解决方法是用functools.wraps装饰wrapper：

```py
import functools

def my_decorator(func):
    #加上这一行就够了
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def hello():
    """这是hello函数的文档"""
    print("Hello!")

print(hello.__name__)
print(hello.__doc__)
#输出：hello
#输出：这是hello函数的文档
```
