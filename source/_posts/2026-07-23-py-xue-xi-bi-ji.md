---
title: "py学习笔记（更新中）"
date: "2026-07-23"
updated: "2026-07-23"
categories:
  - "技术学习"
index_img: "/images/covers/custom/20260723014916-qq-jie-tu-20260723014829.webp"
---
这几个月因为种种原因没能更新博客，这篇是我博客里少有的亲自自己手搓的笔记，最近尽量多更新点技术博客和自己的随笔吧。

## 一、异常处理语法

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

## 二、lambda表达式

### 1.语法

```py
lambda 参数: 表达式
```

### 2.参数形式

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

## 三、可变参数

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

### 1.numerate()

### 2.zip()

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

## 六、迭代器

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

#### list()也在消费迭代器
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

#### 为什么迭代器不直接返回可迭代对象？

因为返回迭代器有一个很大的优点：不需要一开始就把所有结果全部存进内存，而是需要一个时才生成一个。
