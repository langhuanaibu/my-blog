---
title: "TypeScript 语法"
date: "2026-05-07"
updated: "2026-05-07"
categories:
  - "技术学习"
old_id: "article_1778150721669"
twikooPath: "article_1778150721669"
---
<h2>TypeScript 语法</h2>
> 适合读者：已经学过 HTML、CSS、JavaScript，想系统掌握 TypeScript 常用语法，并能把它用到前端开发里。
>
> 学习目标：不是重新学习 JavaScript，而是掌握 TypeScript 如何通过“类型”帮你提前发现错误、写清楚数据结构、提升代码提示和维护性。

## 0. 学习前先建立一个认识

TypeScript 可以理解为 JavaScript 的“带类型版本”。

你写的 TypeScript 最后还是会被编译成 JavaScript，然后再交给浏览器或 Node.js 运行。TypeScript 本身主要做两件事：

- 在代码运行前检查类型错误。
- 让编辑器更清楚变量、函数、对象、接口数据到底长什么样。

例如 JavaScript 里这段代码只有运行时才可能发现问题：

```js
function getUserName(user) {
  return user.name.toUpperCase();
}

getUserName(null);
```

TypeScript 会更早提醒你：`user` 可能不是一个合法对象。

---

## 1. TypeScript 是什么

### 1. 标准语法格式

TypeScript 的基本写法是在 JavaScript 语法基础上增加类型标注：

```ts
let 变量名: 类型 = 值;

function 函数名(参数名: 参数类型): 返回值类型 {
  return 返回值;
}

type 类型名 = 类型结构;

interface 接口名 {
  属性名: 属性类型;
}
```

### 2. 基础例子

```ts
let username: string = "Alice";

function sayHello(name: string): string {
  return "Hello, " + name;
}

type User = {
  id: number;
  name: string;
};
```

### 3. 实际开发例子

```ts
type Product = {
  id: number;
  title: string;
  price: number;
};

function renderProduct(product: Product): string {
  return `${product.title}: ￥${product.price}`;
}

const product: Product = {
  id: 1,
  title: "键盘",
  price: 199,
};

console.log(renderProduct(product));
```

### 4. 语法理解

TypeScript 的核心不是让代码变复杂，而是让数据的形状更明确。你告诉 TS 一个变量、参数或对象应该是什么类型，TS 就能帮你检查错误。

比如 `Product` 规定商品必须有 `id`、`title`、`price`。如果你少写一个属性，或者把 `price` 写成字符串，编辑器就会提前报错。

### 5. 常见错误

- 以为 TypeScript 会改变 JavaScript 的运行逻辑。实际上 TS 编译后还是 JS。
- 以为所有地方都必须手写类型。很多简单变量可以交给 TS 自动推断。
- 以为加了类型就不会有运行时错误。类型检查主要发生在开发阶段，真实数据仍然需要校验。

### 6. 本节练习

定义一个 `Book` 类型，包含：

- `id: number`
- `title: string`
- `author: string`
- `isPublished: boolean`

然后写一个 `getBookTitle(book: Book): string` 函数，返回书名。

### 7. 和 JavaScript 的关系

这一节对应 JavaScript 里的变量、函数、对象写法。TypeScript 没有发明一套新运行机制，而是在 JS 语法旁边补充类型信息，让编辑器和编译器提前知道数据长什么样。

---

## 1.5 开发环境与编译流程

### 1. 标准语法格式

安装 TypeScript：

```powershell
npm i -g typescript
```

编译单个文件：

```powershell
tsc 文件名.ts
```

监听单个文件变化：

```powershell
tsc 文件名.ts -w
```

编译整个项目：

```powershell
tsc
```

项目配置文件：

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "strict": true,
    "rootDir": "src",
    "outDir": "dist"
  },
  "include": ["src/**/*.ts"]
}
```

### 2. 基础例子

创建一个 `hello.ts`：

```ts
const message: string = "Hello TypeScript";
console.log(message);
```

编译：

```powershell
tsc hello.ts
```

编译后会得到 `hello.js`：

```js
var message = "Hello TypeScript";
console.log(message);
```

### 3. 实际开发例子

一个简单项目可以这样组织：

```txt
project
├─ src
│  └─ main.ts
├─ dist
└─ tsconfig.json
```

`src/main.ts`：

```ts
function greet(name: string): string {
  return `Hello, ${name}`;
}

console.log(greet("Alice"));
```

执行：

```powershell
tsc -w
```

这样 TS 编译器会持续监听 `src` 里的文件变化，并把结果输出到 `dist`。

### 4. 语法理解

TypeScript 文件不能直接被普通浏览器当作最终代码执行。开发时你写 `.ts`，编译器检查类型并输出 `.js`，真正运行的是 JavaScript。

常见流程是：

1. 写 TypeScript 源码。
2. 使用 `tsc` 或构建工具编译。
3. 得到 JavaScript。
4. 浏览器或 Node.js 运行 JavaScript。

### 5. 常见错误

- 以为安装 TypeScript 后浏览器就能直接运行 `.ts` 文件。
- 忘记创建 `tsconfig.json`，导致直接执行 `tsc` 时不知道项目配置。
- `tsc -w` 只是监听并编译，不会自动刷新浏览器页面。
- 真实项目里通常还会配合 Vite、Webpack、Babel 等工具，但初学阶段先理解 `tsc` 即可。

### 6. 本节练习

创建一个 `src/main.ts`，写一个带类型的 `add(a: number, b: number): number` 函数。再创建 `tsconfig.json`，让编译结果输出到 `dist`。

### 7. 和 JavaScript 的关系

JavaScript 可以直接运行，TypeScript 需要先编译成 JavaScript。TS 的类型标注会在编译后消失，最终 JS 代码里不会保留 `: string`、`: number` 这些类型信息。

---

## 2. 变量类型

### 1. 标准语法格式

```ts
let 变量名: 类型 = 值;
const 常量名: 类型 = 值;

let 字符串: string = "文本";
let 数字: number = 123;
let 布尔值: boolean = true;
let 空值: null = null;
let 未定义: undefined = undefined;
let 大整数: bigint = 100n;
```

如果 TS 能自动判断类型，可以省略类型标注：

```ts
let 变量名 = 值;
```

其他常见基础类型：

```ts
let 任意值: any = 值;
let 未知值: unknown = 值;

function 没有返回值(): void {}

function 永远不会正常结束(): never {
  throw new Error("错误");
}

let 对象值: object = {};

enum 枚举名 {
  成员1,
  成员2,
}
```

### 2. 基础例子

```ts
let name: string = "Tom";
let age: number = 18;
let isLogin: boolean = false;
let largeId: bigint = 9007199254740993n;

let city = "Shanghai";
let count = 10;

let value: unknown = "hello";

if (typeof value === "string") {
  console.log(value.toUpperCase());
}

function showMessage(message: string): void {
  console.log(message);
}

function fail(message: string): never {
  throw new Error(message);
}

enum Direction {
  Up,
  Down,
  Left,
  Right,
}
```

这里 `city` 会被自动推断为 `string`，`count` 会被自动推断为 `number`。

### 3. 实际开发例子

```ts
const input = document.querySelector("#username") as HTMLInputElement;

let username: string = input.value;
let usernameLength: number = username.length;
let isValid: boolean = usernameLength >= 3;

if (isValid) {
  console.log("用户名合法");
} else {
  console.log("用户名至少需要 3 个字符");
}
```

不确定接口返回值时，可以先用 `unknown`：

```ts
const rawData: unknown = JSON.parse('{"name":"Alice"}');

if (
  typeof rawData === "object" &&
  rawData !== null &&
  "name" in rawData
) {
  console.log("这是一个带 name 的对象");
}
```

状态值更推荐字面量联合类型，而不是默认使用 `enum`：

```ts
type Theme = "light" | "dark";

let theme: Theme = "light";
```

### 4. 语法理解

变量类型用来限制变量后续能存什么值。

```ts
let age: number = 18;
age = 20;
// age = "20"; // 错误：不能把 string 赋值给 number
```

TypeScript 的类型推断很有用。像下面这种代码没必要重复写类型：

```ts
let message = "提交成功";
```

TS 已经知道 `message` 是字符串。

几个容易混淆的类型：

- `any`：关闭类型检查，什么都能做，初学时要少用。
- `unknown`：不知道是什么类型，但使用前必须判断，比 `any` 安全。
- `void`：函数没有返回值。
- `never`：函数永远不会正常返回，比如一定会抛错或死循环。
- `object`：只能表示“非原始类型对象”，通常不如具体对象类型实用。
- `bigint`：表示非常大的整数，字面量后面要加 `n`。
- `enum`：枚举，能给一组常量命名，但前端业务状态很多时候用字面量联合类型更轻量。

### 5. 常见错误

- `number` 同时表示整数和小数，没有单独的 `int` 或 `float`。
- 类型名要小写：`string`、`number`、`boolean`，不是 `String`、`Number`、`Boolean`。
- 给变量标注过窄类型后，后续不能随便赋其他类型的值。
- 不要为了省事到处写 `any`，它会让 TS 失去检查意义。
- `unknown` 不能直接调用方法，要先做类型判断。
- `enum` 可以认识，但不是所有状态都必须用枚举。

### 6. 本节练习

定义下面几个变量，并写上合适类型：

- 商品名称
- 商品价格
- 是否有库存
- 用户积分

再定义一个 `parseValue(value: unknown): string` 函数，如果传入字符串就返回原字符串，否则返回 `"无法处理"`。

### 7. 和 JavaScript 的关系

JavaScript 变量可以在运行过程中放入不同类型的值；TypeScript 会把这种自由收窄成更明确的约束。`any` 接近 JS 的自由写法，`unknown` 则是在 JS 动态数据外面加了一层安全检查。

---

## 3. 数组和元组

### 1. 标准语法格式

数组有两种常见写法：

```ts
let 数组名: 元素类型[] = [元素1, 元素2];
let 数组名: Array<元素类型> = [元素1, 元素2];
```

元组用于表示固定长度、固定顺序、每一位类型明确的数组：

```ts
let 元组名: [类型1, 类型2] = [值1, 值2];
```

### 2. 基础例子

```ts
let scores: number[] = [90, 85, 100];
let names: Array<string> = ["Alice", "Bob"];

let userInfo: [string, number] = ["Tom", 18];
```

### 3. 实际开发例子

```ts
type Todo = {
  id: number;
  title: string;
  done: boolean;
};

const todos: Todo[] = [
  { id: 1, title: "学习 TypeScript", done: false },
  { id: 2, title: "完成练习", done: true },
];

const unfinishedTodos = todos.filter((todo) => !todo.done);
```

### 4. 语法理解

数组类型规定了数组里每个元素的类型。

```ts
let nums: number[] = [1, 2, 3];
// nums.push("4"); // 错误：不能把 string 放进 number[]
```

元组适合表达“位置有含义”的数据。

```ts
let point: [number, number] = [100, 200];
```

这里第一位可以表示 x 坐标，第二位表示 y 坐标。

### 5. 常见错误

- `string[]` 表示字符串数组，不是字符串本身。
- 元组的顺序不能乱：`[string, number]` 和 `[number, string]` 不是一回事。
- 普通列表优先用数组，对固定结构才用元组。

### 6. 本节练习

定义一个 `students` 数组，每个学生包含：

- `id: number`
- `name: string`
- `score: number`

然后筛选出分数大于等于 60 的学生。

### 7. 和 JavaScript 的关系

数组方法仍然是 JavaScript 的 `map`、`filter`、`find`、`reduce`。TypeScript 的增强点是：数组元素类型确定后，回调函数里的参数类型会自动推断出来。

---

## 4. 函数类型

### 1. 标准语法格式

普通函数：

```ts
function 函数名(参数名: 参数类型): 返回值类型 {
  return 返回值;
}
```

可选参数：

```ts
function 函数名(参数名?: 参数类型): 返回值类型 {
  return 返回值;
}
```

默认参数：

```ts
function 函数名(参数名: 参数类型 = 默认值): 返回值类型 {
  return 返回值;
}
```

箭头函数：

```ts
const 函数名 = (参数名: 参数类型): 返回值类型 => {
  return 返回值;
};
```

### 2. 基础例子

```ts
function add(a: number, b: number): number {
  return a + b;
}

function greet(name: string = "Guest"): string {
  return `Hello, ${name}`;
}

const double = (num: number): number => {
  return num * 2;
};
```

### 3. 实际开发例子

```ts
function getInputValue(input: HTMLInputElement): string {
  return input.value.trim();
}

function validateUsername(username: string): boolean {
  return username.length >= 3 && username.length <= 12;
}

const usernameInput = document.querySelector("#username") as HTMLInputElement;
const username = getInputValue(usernameInput);

if (validateUsername(username)) {
  console.log("用户名格式正确");
}
```

### 4. 语法理解

函数类型主要管两件事：

- 参数传进来的值必须符合类型。
- 函数返回出去的值必须符合类型。

```ts
function formatPrice(price: number): string {
  return `￥${price.toFixed(2)}`;
}
```

这个函数要求传入数字，并保证返回字符串。

### 5. 常见错误

- 可选参数必须处理 `undefined` 的情况。
- 返回值写了 `number`，就不能返回字符串。
- 函数没有返回值时，返回值类型通常写 `void`。

```ts
function logMessage(message: string): void {
  console.log(message);
}
```

### 6. 本节练习

写一个 `calculateTotal(price: number, count: number): number` 函数，返回商品总价。

再写一个 `formatTotal(total: number): string` 函数，把总价格式化为 `总价：￥xxx`。

### 7. 和 JavaScript 的关系

函数声明、函数表达式、箭头函数都来自 JavaScript。TypeScript 只是给参数、返回值和函数变量补上类型，尤其适合约束回调函数、工具函数和事件处理函数。

---

## 5. 对象类型

### 1. 标准语法格式

```ts
let 对象名: {
  属性名: 属性类型;
  可选属性名?: 属性类型;
  readonly 只读属性名: 属性类型;
} = {
  属性名: 值,
  只读属性名: 值,
};
```

嵌套对象：

```ts
let 对象名: {
  属性1: 类型;
  子对象: {
    属性2: 类型;
  };
};
```

### 2. 基础例子

```ts
let user: {
  readonly id: number;
  name: string;
  age?: number;
} = {
  id: 1,
  name: "Alice",
};

user.name = "Tom";
// user.id = 2; // 错误：id 是只读属性
```

### 3. 实际开发例子

```ts
let article: {
  id: number;
  title: string;
  author: {
    id: number;
    name: string;
  };
  tags?: string[];
} = {
  id: 1001,
  title: "TypeScript 入门",
  author: {
    id: 1,
    name: "小明",
  },
  tags: ["前端", "TypeScript"],
};

console.log(article.author.name);
```

### 4. 语法理解

对象类型描述的是对象应该有哪些属性，以及每个属性是什么类型。

可选属性用 `?` 表示：

```ts
age?: number;
```

它的意思是：这个属性可以不存在；如果存在，必须是 `number`。

`readonly` 表示属性创建后不能被重新赋值，适合用于 ID 这类不应该被改动的数据。

### 5. 常见错误

- 对象少了必填属性会报错。
- 对象属性类型不匹配会报错。
- 可选属性使用前要考虑它可能是 `undefined`。

```ts
if (article.tags) {
  console.log(article.tags.join(","));
}
```

### 6. 本节练习

定义一个 `course` 对象类型，包含：

- 只读 `id`
- `title`
- `teacher`
- 可选 `description`
- `chapters` 字符串数组

### 7. 和 JavaScript 的关系

对象仍然是 JavaScript 对象。TypeScript 的对象类型相当于给对象写一份“结构说明书”，提前规定哪些属性必须存在、哪些属性可选、哪些属性不能被修改。

---

## 5.5 类与面向对象

### 1. 标准语法格式

定义类：

```ts
class 类名 {
  readonly 只读属性: 类型;
  public 公共属性: 类型;
  protected 受保护属性: 类型;
  private 私有属性: 类型;

  constructor(参数: 类型) {
    this.属性 = 参数;
  }

  方法名(): 返回值类型 {
    return 返回值;
  }
}
```

继承：

```ts
class 子类 extends 父类 {
  constructor(参数: 类型) {
    super(父类参数);
  }

  重写方法(): 返回值类型 {
    return 返回值;
  }
}
```

实现接口：

```ts
class 类名 implements 接口名 {
  // 必须实现接口要求的属性和方法
}
```

抽象类：

```ts
abstract class 抽象类名 {
  abstract 方法名(): 返回值类型;
}
```

### 2. 基础例子

```ts
class Person {
  readonly id: number;
  public name: string;
  private age: number;

  constructor(id: number, name: string, age: number) {
    this.id = id;
    this.name = name;
    this.age = age;
  }

  sayHello(): void {
    console.log(`你好，我是 ${this.name}`);
  }

  getAge(): number {
    return this.age;
  }
}

const person = new Person(1, "Alice", 18);
person.sayHello();
```

### 3. 实际开发例子

```ts
interface StorageService {
  get(key: string): string | null;
  set(key: string, value: string): void;
}

class LocalStorageService implements StorageService {
  static prefix = "app:";

  get(key: string): string | null {
    return localStorage.getItem(LocalStorageService.prefix + key);
  }

  set(key: string, value: string): void {
    localStorage.setItem(LocalStorageService.prefix + key, value);
  }
}

const storage = new LocalStorageService();
storage.set("token", "abc123");
console.log(storage.get("token"));
```

继承和重写：

```ts
abstract class Animal {
  constructor(protected name: string) {}

  abstract speak(): void;
}

class Dog extends Animal {
  speak(): void {
    console.log(`${this.name} 在叫`);
  }
}

const dog = new Dog("旺财");
dog.speak();
```

getter / setter：

```ts
class Counter {
  private _value = 0;

  get value(): number {
    return this._value;
  }

  set value(value: number) {
    if (value >= 0) {
      this._value = value;
    }
  }
}
```

### 4. 语法理解

类是创建对象的模板。属性表示对象的数据，方法表示对象能做什么。

访问修饰符控制属性或方法能在哪里被访问：

- `public`：默认值，类内部、子类、实例对象都能访问。
- `protected`：类内部和子类能访问，实例对象不能直接访问。
- `private`：只有当前类内部能访问。
- `readonly`：只能在声明或构造函数中赋值，之后不能修改。
- `static`：属于类本身，不属于实例。

`implements` 用来约束一个类必须具备某些能力。`abstract` 用来定义不能直接实例化的抽象父类，让子类实现具体逻辑。

### 5. 常见错误

- 忘记在构造函数里初始化类属性。
- 在类外访问 `private` 或 `protected` 属性。
- 子类构造函数里使用 `this` 前没有先调用 `super()`。
- 抽象类不能 `new`，只能被继承。
- `static` 属性要用类名访问，不是实例访问。

### 6. 本节练习

定义一个 `User` 类：

- `readonly id: number`
- `public name: string`
- `private password: string`
- `checkPassword(password: string): boolean`

再定义一个 `AdminUser extends User`，增加 `role: "admin"` 属性。

### 7. 和 JavaScript 的关系

JavaScript 本身也有 `class`、`constructor`、`extends`、`super`。TypeScript 在此基础上增加属性类型、访问修饰符、抽象类和接口实现检查，让面向对象代码的结构更明确。

---

## 6. 类型别名 type

### 1. 标准语法格式

```ts
type 类型名 = 类型;

type 对象类型名 = {
  属性名: 属性类型;
};

type 联合类型名 = 类型1 | 类型2;
```

### 2. 基础例子

```ts
type UserId = number;
type Status = "pending" | "success" | "error";

type User = {
  id: UserId;
  name: string;
  status: Status;
};
```

### 3. 实际开发例子

```ts
type ButtonType = "button" | "submit" | "reset";

type ButtonConfig = {
  text: string;
  type: ButtonType;
  disabled: boolean;
};

const submitButton: ButtonConfig = {
  text: "提交",
  type: "submit",
  disabled: false,
};
```

### 4. 语法理解

`type` 用来给复杂类型起名字。

如果一个对象结构、联合类型、函数类型会被多次使用，就可以用 `type` 抽出来。

```ts
type Point = {
  x: number;
  y: number;
};

function getDistance(point: Point): number {
  return Math.sqrt(point.x ** 2 + point.y ** 2);
}
```

### 5. 常见错误

- `type` 只是类型，不是运行时变量。
- 类型名一般用大驼峰命名，比如 `UserInfo`。
- 不要把所有简单变量都抽成 `type`，会增加阅读成本。

### 6. 本节练习

定义一个 `LoginStatus` 类型，只允许：

- `"idle"`
- `"loading"`
- `"success"`
- `"error"`

再定义一个 `LoginState` 类型，包含：

- `status: LoginStatus`
- `message: string`

### 7. 和 JavaScript 的关系

`type` 只存在于 TypeScript 类型系统里，编译成 JavaScript 后会消失。它不会创建真实变量，只是帮助你复用复杂类型。

---

## 7. 接口 interface

### 1. 标准语法格式

```ts
interface 接口名 {
  属性名: 属性类型;
  可选属性名?: 属性类型;
}

interface 子接口名 extends 父接口名 {
  新属性名: 新属性类型;
}

class 类名 implements 接口名 {
  // 实现接口要求的属性和方法
}
```

### 2. 基础例子

```ts
interface User {
  id: number;
  name: string;
  email?: string;
}

const user: User = {
  id: 1,
  name: "Alice",
};

interface Logger {
  log(message: string): void;
}

class ConsoleLogger implements Logger {
  log(message: string): void {
    console.log(message);
  }
}
```

### 3. 实际开发例子

```ts
interface BaseResponse {
  code: number;
  message: string;
}

interface UserResponse extends BaseResponse {
  data: {
    id: number;
    name: string;
  };
}

const response: UserResponse = {
  code: 200,
  message: "ok",
  data: {
    id: 1,
    name: "Tom",
  },
};
```

接口约束类必须实现的能力：

```ts
interface Flyable {
  fly(): void;
}

class Bird implements Flyable {
  fly(): void {
    console.log("鸟在飞");
  }
}

function startFly(target: Flyable): void {
  target.fly();
}

startFly(new Bird());
```

### 4. 语法理解

`interface` 常用于描述对象结构，尤其适合描述接口返回数据、组件属性、类的结构。

`interface` 可以通过 `extends` 继承另一个接口。

```ts
interface AdminUser extends User {
  role: "admin";
}
```

`implements` 表示类要实现接口。它不负责生成代码，只负责检查类有没有按接口要求写属性和方法。

### 5. 常见错误

- `interface` 更适合对象结构，不适合直接写联合类型。
- 如果需要写 `"success" | "error"` 这种联合类型，通常用 `type` 更自然。
- `type` 和 `interface` 很多时候都能描述对象，不必过度纠结。初学时可以记住：对象结构优先 `interface`，联合类型优先 `type`。
- `implements` 只能检查类的实例侧成员，不能用来强制检查静态属性。
- 类实现接口时，接口要求的方法参数和返回值类型必须匹配。

### 6. 本节练习

定义一个 `Article` 接口，包含：

- `id`
- `title`
- `content`
- `author`

再定义一个 `ArticleDetail` 接口，继承 `Article`，额外包含 `comments` 字符串数组。

再定义一个 `Renderable` 接口，要求有 `render(): string` 方法，然后写一个 `Card implements Renderable`。

### 7. 和 JavaScript 的关系

`interface` 也是 TypeScript 的类型描述工具，编译后不会变成 JavaScript 代码。它适合描述 JS 对象、接口响应、组件参数这类“对象结构”。

---

## 8. 联合类型和字面量类型

### 1. 标准语法格式

联合类型：

```ts
let 变量名: 类型1 | 类型2;
```

字面量类型：

```ts
let 变量名: "固定值1" | "固定值2";
```

常见组合：

```ts
type 状态类型 = "状态1" | "状态2" | "状态3";
```

### 2. 基础例子

```ts
let id: string | number;

id = 1001;
id = "user-1001";

type RequestStatus = "idle" | "loading" | "success" | "error";

let status: RequestStatus = "loading";
```

### 3. 实际开发例子

```ts
type ToastType = "success" | "error" | "warning";

function showToast(message: string, type: ToastType): void {
  console.log(`[${type}] ${message}`);
}

showToast("保存成功", "success");
showToast("保存失败", "error");
// showToast("未知状态", "danger"); // 错误：danger 不在 ToastType 中
```

### 4. 语法理解

联合类型表示一个值可以是多种类型之一。

字面量类型表示一个值只能是某几个固定值之一。

前端开发里，字面量联合类型特别适合描述状态：

```ts
type TabKey = "home" | "profile" | "settings";
type Theme = "light" | "dark";
```

这样比直接写 `string` 更安全，因为 TS 会限制你只能传入合法状态。

### 5. 常见错误

- 联合类型不是“同时满足多个类型”，而是“可以是其中一种类型”。
- 使用联合类型时，不能直接调用某个类型独有的方法，需要先做类型判断。
- 状态值不建议随便写成 `string`，否则 TS 无法帮你检查拼写错误。

### 6. 本节练习

定义一个 `OrderStatus` 类型，只允许：

- `"unpaid"`
- `"paid"`
- `"shipped"`
- `"finished"`
- `"cancelled"`

写一个 `getOrderStatusText(status: OrderStatus): string` 函数，根据状态返回中文文案。

### 7. 和 JavaScript 的关系

JavaScript 通常用字符串表示状态，比如 `"loading"`、`"success"`。TypeScript 的字面量联合类型可以把这些状态限制在固定范围内，减少拼写错误。

---

## 9. 类型收窄

### 1. 标准语法格式

使用 `typeof`：

```ts
if (typeof 变量 === "string") {
  // 这里变量会被收窄为 string
}
```

使用 `in`：

```ts
if ("属性名" in 对象) {
  // 这里可以确认对象中存在某个属性
}
```

判空：

```ts
if (变量 !== null) {
  // 这里变量不是 null
}
```

判断数组：

```ts
if (Array.isArray(变量)) {
  // 这里变量是数组
}
```

### 2. 基础例子

```ts
function printId(id: string | number): void {
  if (typeof id === "string") {
    console.log(id.toUpperCase());
  } else {
    console.log(id.toFixed(0));
  }
}
```

### 3. 实际开发例子

```ts
type TextMessage = {
  type: "text";
  content: string;
};

type ImageMessage = {
  type: "image";
  url: string;
};

type Message = TextMessage | ImageMessage;

function renderMessage(message: Message): string {
  if (message.type === "text") {
    return message.content;
  }

  return `<img src="${message.url}" alt="图片消息">`;
}
```

### 4. 语法理解

类型收窄就是通过判断条件，让 TypeScript 知道某个变量在当前代码块里更具体是什么类型。

```ts
function getLength(value: string | string[]): number {
  if (Array.isArray(value)) {
    return value.length;
  }

  return value.length;
}
```

虽然字符串和数组都有 `length`，但很多方法是各自独有的。类型收窄能避免误用。

### 5. 常见错误

- 对联合类型直接调用某个类型独有的方法。
- 只判断了 `null`，忘记判断 `undefined`。
- 复杂对象联合类型中，没有设计清晰的区分字段，比如 `type`。

### 6. 本节练习

定义一个 `Result` 类型：

- 成功：`{ status: "success"; data: string[] }`
- 失败：`{ status: "error"; message: string }`

写一个 `handleResult(result: Result): string` 函数，成功时返回数据数量，失败时返回错误信息。

### 7. 和 JavaScript 的关系

类型收窄依赖的判断方式大多来自 JavaScript，比如 `typeof`、`in`、`Array.isArray`。TypeScript 会根据这些运行时判断，推断当前分支里的更具体类型。

---

## 10. 类型断言

### 1. 标准语法格式

```ts
值 as 类型
```

常见 DOM 写法：

```ts
const 元素 = document.querySelector("选择器") as 具体元素类型;
```

也可以先判空：

```ts
const 元素 = document.querySelector("选择器");

if (元素) {
  // 这里可以安全使用元素
}
```

### 2. 基础例子

```ts
const value: unknown = "hello";
const text = value as string;

console.log(text.toUpperCase());
```

### 3. 实际开发例子

```ts
const input = document.querySelector("#email") as HTMLInputElement;
const button = document.querySelector("#submit") as HTMLButtonElement;

button.addEventListener("click", () => {
  console.log(input.value);
});
```

更稳妥的写法：

```ts
const input = document.querySelector("#email");

if (input instanceof HTMLInputElement) {
  console.log(input.value);
}
```

### 4. 语法理解

类型断言的意思是：你告诉 TypeScript，“我比你更清楚这个值的类型”。

它不会改变运行时数据，只会影响 TypeScript 的类型检查。

```ts
const num = "123" as unknown as number;
```

这种写法不会真的把字符串变成数字，只是骗过了类型检查。

### 5. 常见错误

- 把类型断言当成类型转换。
- 明明不确定 DOM 元素是否存在，却直接断言。
- 过度使用 `as`，导致 TypeScript 失去检查意义。

### 6. 本节练习

获取页面中的 `#search` 输入框，分别写出：

- 使用 `as HTMLInputElement` 的版本
- 使用 `instanceof HTMLInputElement` 判定的版本

### 7. 和 JavaScript 的关系

类型断言只影响 TypeScript 检查，不会改变 JavaScript 运行时的值。`as number` 不会把字符串转成数字，真正的转换仍然要用 `Number()`、`parseInt()` 等 JS API。

---

## 11. 泛型

### 1. 标准语法格式

泛型函数：

```ts
function 函数名<T>(参数: T): T {
  return 参数;
}
```

泛型接口：

```ts
interface 接口名<T> {
  属性名: T;
}
```

Promise 泛型：

```ts
Promise<数据类型>
```

泛型约束：

```ts
function 函数名<T extends 约束类型>(参数: T): 返回值类型 {
  return 返回值;
}
```

泛型类：

```ts
class 类名<T> {
  属性名: T;
}
```

### 2. 基础例子

```ts
function identity<T>(value: T): T {
  return value;
}

const num = identity<number>(100);
const text = identity<string>("hello");
```

多数时候可以让 TS 自动推断泛型：

```ts
const result = identity("TypeScript");
```

泛型约束例子：

```ts
function getLength<T extends { length: number }>(value: T): number {
  return value.length;
}

getLength("hello");
getLength([1, 2, 3]);
```

### 3. 实际开发例子

```ts
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

type User = {
  id: number;
  name: string;
};

const userResponse: ApiResponse<User> = {
  code: 200,
  message: "ok",
  data: {
    id: 1,
    name: "Alice",
  },
};
```

泛型类实际例子：

```ts
class DataStore<T> {
  private data: T[] = [];

  add(item: T): void {
    this.data.push(item);
  }

  getAll(): T[] {
    return this.data;
  }
}

const userStore = new DataStore<User>();
userStore.add({ id: 1, name: "Alice" });
```

### 4. 语法理解

泛型可以理解为“类型参数”。

有些结构是固定的，但里面装的数据类型不固定：

```ts
ApiResponse<User>
ApiResponse<Product>
ApiResponse<string[]>
```

它们都有 `code`、`message`、`data`，但 `data` 的类型不同。泛型可以避免重复定义一堆相似类型。

泛型约束用来告诉 TS：虽然具体类型还不确定，但它至少要满足某个结构。比如 `T extends { length: number }` 表示传进来的值必须有 `length`。

### 5. 常见错误

- 泛型不是为了炫技，而是为了解决类型复用。
- 如果一个类型不会复用，没必要强行写泛型。
- `T` 只是常见命名，也可以写成 `Data`、`Item` 等更语义化的名字。
- 泛型不是 `any`。泛型会保留输入和输出之间的类型关系，`any` 会放弃检查。
- 使用泛型约束时，约束只表示“至少拥有这些属性”，不代表只能有这些属性。

### 6. 本节练习

定义一个泛型接口 `ListResponse<T>`，包含：

- `total: number`
- `list: T[]`

然后用它定义一个文章列表响应类型。

再写一个泛型类 `Cache<T>`，支持 `set(value: T)` 和 `get(): T | undefined`。

### 7. 和 JavaScript 的关系

泛型是 TypeScript 的类型复用机制，编译后不会保留。它常用来描述 JavaScript 中“外层结构固定、内部数据变化”的模式，比如接口响应、列表、Promise。

---

## 12. DOM 和事件类型

### 1. 标准语法格式

获取 DOM：

```ts
const 元素 = document.querySelector("选择器") as HTMLElement;
```

输入框：

```ts
const 输入框 = document.querySelector("选择器") as HTMLInputElement;
```

事件：

```ts
元素.addEventListener("click", (event: MouseEvent) => {
  // 事件处理
});
```

表单事件：

```ts
表单.addEventListener("submit", (event: SubmitEvent) => {
  event.preventDefault();
});
```

### 2. 基础例子

```ts
const button = document.querySelector("#btn") as HTMLButtonElement;

button.addEventListener("click", (event: MouseEvent) => {
  console.log(event.clientX, event.clientY);
});
```

### 3. 实际开发例子

```ts
const form = document.querySelector("#login-form") as HTMLFormElement;
const usernameInput = document.querySelector("#username") as HTMLInputElement;
const passwordInput = document.querySelector("#password") as HTMLInputElement;

form.addEventListener("submit", (event: SubmitEvent) => {
  event.preventDefault();

  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  if (!username || !password) {
    console.log("请填写用户名和密码");
    return;
  }

  console.log("提交登录", username, password);
});
```

### 4. 语法理解

不同 DOM 元素有不同属性。

`HTMLElement` 是比较通用的元素类型，但它没有 `value`。

如果你要读取输入框内容，需要使用 `HTMLInputElement`：

```ts
const input = document.querySelector("#keyword") as HTMLInputElement;
console.log(input.value);
```

事件类型能让你获得准确的事件属性提示，比如鼠标位置、键盘按键、表单提交行为。

### 5. 常见错误

- `querySelector` 可能返回 `null`。
- 不是所有元素都有 `value` 属性。
- `event.target` 的类型比较宽泛，不能随便当成输入框使用。

```ts
input.addEventListener("input", (event: Event) => {
  const target = event.target;

  if (target instanceof HTMLInputElement) {
    console.log(target.value);
  }
});
```

### 6. 本节练习

写一个搜索框逻辑：

- 获取 `#keyword` 输入框
- 获取 `#search-btn` 按钮
- 点击按钮后打印输入框内容
- 输入内容为空时提示“请输入关键词”

### 7. 和 JavaScript 的关系

DOM API 全部来自浏览器 JavaScript。TypeScript 的作用是把 `querySelector`、事件对象、输入框元素这些浏览器对象标成更准确的类型。

---

## 13. 异步请求和接口数据类型

### 1. 标准语法格式

Promise 返回值：

```ts
async function 函数名(): Promise<返回数据类型> {
  return 数据;
}
```

接口响应结构：

```ts
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}
```

fetch 基础写法：

```ts
const response = await fetch("接口地址");
const data = await response.json();
```

### 2. 基础例子

```ts
async function getNumber(): Promise<number> {
  return 100;
}

async function getMessage(): Promise<string> {
  return "请求成功";
}
```

### 3. 实际开发例子

```ts
interface User {
  id: number;
  name: string;
  email: string;
}

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

async function fetchUser(id: number): Promise<ApiResponse<User>> {
  const response = await fetch(`/api/users/${id}`);
  const data = (await response.json()) as ApiResponse<User>;
  return data;
}

async function renderUser(): Promise<void> {
  const result = await fetchUser(1);
  console.log(result.data.name);
}
```

### 4. 语法理解

异步函数一定返回 Promise。

```ts
async function fn(): Promise<string> {
  return "hello";
}
```

即使你 `return "hello"`，函数真实返回的也是 `Promise<string>`。

接口数据类型的重点是描述后端返回的数据结构。这样你访问 `result.data.name` 时，编辑器能知道 `data` 里有什么。

### 5. 常见错误

- `response.json()` 的结果默认是 `any`，不能完全依赖它。
- 类型断言不能保证后端数据真实正确。
- 前端类型和后端真实返回结构不一致时，运行时仍然会出错。

更严格的项目会对接口数据做运行时校验，但初学阶段先掌握类型描述即可。

### 6. 本节练习

定义一个商品接口 `Product`，包含：

- `id`
- `title`
- `price`

再写一个 `fetchProducts(): Promise<ApiResponse<Product[]>>` 函数。

### 7. 和 JavaScript 的关系

`fetch`、Promise、`async/await` 都是 JavaScript 异步能力。TypeScript 主要给 Promise 结果、接口响应和错误处理补类型，让你更清楚异步代码最终会得到什么数据。

---

## 14. 模块化和类型导入导出

### 1. 标准语法格式

导出变量或函数：

```ts
export const 变量名 = 值;

export function 函数名() {
  // 函数内容
}
```

导出类型：

```ts
export type 类型名 = 类型结构;

export interface 接口名 {
  属性名: 属性类型;
}
```

导入：

```ts
import { 名称 } from "./文件路径";
```

只导入类型：

```ts
import type { 类型名 } from "./文件路径";
```

### 2. 基础例子

```ts
// user.ts
export type User = {
  id: number;
  name: string;
};

export function getUserName(user: User): string {
  return user.name;
}
```

```ts
// main.ts
import { getUserName } from "./user";
import type { User } from "./user";

const user: User = {
  id: 1,
  name: "Alice",
};

console.log(getUserName(user));
```

### 3. 实际开发例子

```ts
// types.ts
export interface Todo {
  id: number;
  title: string;
  done: boolean;
}
```

```ts
// todo.ts
import type { Todo } from "./types";

export function createTodo(title: string): Todo {
  return {
    id: Date.now(),
    title,
    done: false,
  };
}
```

```ts
// main.ts
import { createTodo } from "./todo";

const todo = createTodo("学习 TS 模块化");
console.log(todo);
```

### 4. 语法理解

模块化能把类型、函数、业务逻辑拆到不同文件里。

`import type` 表示只导入类型，不导入运行时代码。它能让代码意图更清晰，也能减少一些构建工具的歧义。

```ts
import type { User } from "./user";
```

如果你只在类型标注里用 `User`，推荐使用 `import type`。

### 5. 常见错误

- 忘记写相对路径的 `./`。
- 把只用于类型的内容当成普通值使用。
- 循环导入会让模块关系变复杂，初学时尽量保持文件依赖简单。

### 6. 本节练习

创建两个文件的设计：

- `types.ts`：导出 `Product` 类型
- `product.ts`：导入 `Product` 类型，并导出 `formatProduct(product: Product): string`

### 7. 和 JavaScript 的关系

模块化的 `import/export` 来自现代 JavaScript。TypeScript 额外提供 `import type`、`export type`，专门表达“这里只使用类型，不需要运行时代码”。

---

## 15. tsconfig 基础配置

### 1. 标准语法格式

`tsconfig.json` 是 TypeScript 项目的配置文件。

常见结构：

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "strict": true,
    "rootDir": "src",
    "outDir": "dist",
    "noEmitOnError": true,
    "removeComments": true,
    "noImplicitAny": true
  },
  "include": ["src"],
  "exclude": ["node_modules"]
}
```

如果项目很小，也可以用 `files` 精确指定文件：

```json
{
  "files": ["src/main.ts", "src/utils.ts"]
}
```

### 2. 基础例子

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "strict": true,
    "noEmitOnError": true
  }
}
```

### 3. 实际开发例子

一个简单前端项目可以这样组织：

```txt
project
├─ src
│  ├─ main.ts
│  └─ types.ts
├─ dist
└─ tsconfig.json
```

对应配置：

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "strict": true,
    "rootDir": "src",
    "outDir": "dist",
    "noEmitOnError": true,
    "removeComments": true
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
```

### 4. 语法理解

几个常用配置的含义：

- `target`：编译出来的 JavaScript 版本。
- `module`：模块化规范。
- `strict`：是否开启严格类型检查。
- `rootDir`：源码目录。
- `outDir`：编译输出目录。
- `include`：哪些文件参与编译。
- `exclude`：哪些文件或目录不参与编译。
- `files`：明确指定要编译的文件列表，适合很小的项目。
- `noEmitOnError`：有类型错误时不输出 JS。
- `removeComments`：编译输出时移除注释。
- `noImplicitAny`：不允许隐式 `any`，参数类型不明确时会报错。

初学 TypeScript 时，建议开启：

```json
{
  "strict": true,
  "noEmitOnError": true
}
```

这样能尽早养成正确的类型习惯。

### 5. 常见错误

- 以为 `tsconfig.json` 会自动运行代码。它只是编译配置。
- `rootDir` 和 `outDir` 混在一起，导致源码和编译结果不好区分。
- 关闭 `strict` 后，很多本该暴露的问题会被隐藏。
- `include` 和 `exclude` 写错后，可能导致文件没有参与编译。
- `noImplicitAny` 关闭后，很多没写类型的参数会悄悄变成 `any`。
- `files` 和 `include` 不要混乱使用。初学项目一般用 `include` 就够了。

### 6. 本节练习

写一个 `tsconfig.json`，要求：

- 源码目录是 `src`
- 输出目录是 `dist`
- 开启严格模式
- 编译目标是 `ES2020`
- 有类型错误时不输出 JS

### 7. 和 JavaScript 的关系

`tsconfig.json` 决定 TypeScript 如何检查代码、输出什么版本的 JavaScript。最终浏览器或 Node.js 运行的仍然是编译后的 JS 文件。

---

## 16. 字符串方法的 TypeScript 写法

### 1. 标准语法格式

```ts
let 文本: string = "内容";

文本.length;
文本.trim();
文本.includes("关键词");
文本.slice(开始索引, 结束索引);
文本.replace("旧内容", "新内容");
文本.split("分隔符");

const 模板字符串: string = `文本 ${表达式}`;
```

### 2. 基础例子

```ts
const message: string = "  TypeScript  ";

const cleanMessage: string = message.trim();
const upperMessage: string = cleanMessage.toUpperCase();
const hasScript: boolean = cleanMessage.includes("Script");
const chars: string[] = cleanMessage.split("");
```

### 3. 实际开发例子

```ts
function normalizeKeyword(keyword: string): string {
  return keyword.trim().toLowerCase();
}

function highlightKeyword(title: string, keyword: string): string {
  const cleanKeyword = normalizeKeyword(keyword);

  if (!cleanKeyword) {
    return title;
  }

  return title.replace(cleanKeyword, `<mark>${cleanKeyword}</mark>`);
}
```

### 4. 语法理解

字符串方法本身来自 JavaScript。TypeScript 会根据方法返回值自动推断类型：`trim()` 返回 `string`，`includes()` 返回 `boolean`，`split()` 返回 `string[]`。

### 5. 常见错误

- 字符串是不可变的，`trim()`、`replace()` 会返回新字符串，不会修改原字符串。
- `replace()` 默认只替换第一个匹配项，全部替换可以用 `replaceAll()` 或正则 `g`。
- `split()` 返回数组，所以结果类型是 `string[]`。

### 6. 本节练习

写一个 `formatUsername(name: string): string` 函数，要求去掉首尾空格，并把名字转成小写。

### 7. 和 JavaScript 的关系

参考文章里的字符串方法可以原样在 TypeScript 中使用。TS 的重点是把输入和输出标清楚，比如搜索关键词一定是 `string`，判断结果一定是 `boolean`。

---

## 17. 数组方法的类型推断

### 1. 标准语法格式

```ts
const 新数组 = 数组.map((元素) => 返回值);
const 筛选结果 = 数组.filter((元素) => 条件);
const 查找结果 = 数组.find((元素) => 条件);
const 累积结果 = 数组.reduce((累积值, 当前值) => 新累积值, 初始值);
```

### 2. 基础例子

```ts
const numbers: number[] = [1, 2, 3, 4];

const doubled: number[] = numbers.map((num) => num * 2);
const evens: number[] = numbers.filter((num) => num % 2 === 0);
const firstLarge: number | undefined = numbers.find((num) => num > 2);
const sum: number = numbers.reduce((total, num) => total + num, 0);
```

### 3. 实际开发例子

```ts
type Product = {
  id: number;
  title: string;
  price: number;
  stock: number;
};

const products: Product[] = [
  { id: 1, title: "鼠标", price: 99, stock: 10 },
  { id: 2, title: "键盘", price: 199, stock: 0 },
];

const visibleProducts = products.filter((product) => product.stock > 0);
const productTitles = visibleProducts.map((product) => product.title);
const totalPrice = visibleProducts.reduce((total, product) => total + product.price, 0);
```

### 4. 语法理解

只要数组类型明确，TS 就能推断回调函数参数类型。`Product[]` 里的 `product` 会自动拥有 `id`、`title`、`price`、`stock` 的类型提示。

### 5. 常见错误

- `find()` 可能找不到结果，所以返回类型通常是 `T | undefined`。
- `reduce()` 最好写初始值，避免空数组或推断不清。
- `sort()` 会修改原数组，如果不想改原数组，先复制：`[...arr].sort(...)`。

### 6. 本节练习

定义一个 `Student[]`，使用 `filter` 找出及格学生，使用 `map` 得到学生姓名数组，使用 `reduce` 计算平均分。

### 7. 和 JavaScript 的关系

数组方法完全来自 JavaScript。TypeScript 的优势是让回调参数和返回值更明确，减少把数组元素属性写错的情况。

---

## 18. Date 和时间处理类型

### 1. 标准语法格式

```ts
const 日期对象: Date = new Date();
const 时间戳: number = Date.now();

function 函数名(date: Date): string {
  return 格式化结果;
}
```

### 2. 基础例子

```ts
const now: Date = new Date();
const year: number = now.getFullYear();
const month: number = now.getMonth() + 1;
const timestamp: number = now.getTime();
```

### 3. 实际开发例子

```ts
function padZero(value: number): string {
  return String(value).padStart(2, "0");
}

function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = padZero(date.getMonth() + 1);
  const day = padZero(date.getDate());

  return `${year}-${month}-${day}`;
}

console.log(formatDate(new Date()));
```

### 4. 语法理解

`Date` 是 JavaScript 的内置对象类型。TypeScript 可以识别 `Date` 实例上的方法，也能约束函数必须传入真正的日期对象。

### 5. 常见错误

- `getMonth()` 返回 0 到 11，所以真实月份要加 1。
- 时间戳一般是 `number`，单位通常是毫秒。
- `new Date("2026-03-27")` 受解析规则和时区影响，复杂项目要更谨慎。

### 6. 本节练习

写一个 `formatDateTime(date: Date): string` 函数，返回 `YYYY-MM-DD HH:mm:ss` 格式。

### 7. 和 JavaScript 的关系

参考文章里的 Date API 可以直接在 TS 里使用。TS 主要补充 `Date`、`number`、`string` 这些输入输出类型。

---

## 19. 定时器、防抖和节流类型

### 1. 标准语法格式

```ts
const timerId: ReturnType<typeof setTimeout> = setTimeout(() => {
  // 延迟执行
}, 毫秒数);

clearTimeout(timerId);

const intervalId: ReturnType<typeof setInterval> = setInterval(() => {
  // 重复执行
}, 毫秒数);

clearInterval(intervalId);
```

### 2. 基础例子

```ts
const timerId: ReturnType<typeof setTimeout> = setTimeout(() => {
  console.log("2 秒后执行");
}, 2000);

clearTimeout(timerId);
```

### 3. 实际开发例子

```ts
function debounce<Args extends unknown[]>(
  fn: (...args: Args) => void,
  delay: number
): (...args: Args) => void {
  let timerId: ReturnType<typeof setTimeout> | undefined;

  return (...args: Args) => {
    if (timerId) {
      clearTimeout(timerId);
    }

    timerId = setTimeout(() => {
      fn(...args);
    }, delay);
  };
}

const search = debounce((keyword: string) => {
  console.log("搜索：", keyword);
}, 300);

search("typescript");
```

### 4. 语法理解

浏览器和 Node.js 对定时器 ID 的类型不完全一样。`ReturnType<typeof setTimeout>` 是更稳的写法，能根据当前环境自动得到正确类型。

### 5. 常见错误

- 不要把定时器 ID 固定写死成 `number`，跨环境可能不准确。
- `setInterval` 要记得清理，否则可能持续执行。
- 防抖/节流函数要保留原函数参数类型，否则调用时会失去提示。

### 6. 本节练习

写一个 `throttle(fn, delay)`，限制滚动事件处理函数在指定时间内最多执行一次，并保留参数类型。

### 7. 和 JavaScript 的关系

定时器、防抖、节流都来自 JavaScript 的异步机制。TypeScript 的重点是正确描述回调函数、定时器 ID 和参数列表。

---

## 20. 图片和脚本加载事件类型

### 1. 标准语法格式

```ts
const img: HTMLImageElement = new Image();

img.onload = () => {
  // 加载成功
};

img.onerror = () => {
  // 加载失败
};

img.src = 图片地址;
```

### 2. 基础例子

```ts
const img: HTMLImageElement = new Image();

img.onload = () => {
  console.log("图片加载成功");
};

img.onerror = () => {
  console.log("图片加载失败");
};

img.src = "/avatar.png";
```

### 3. 实际开发例子

```ts
function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();

    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`图片加载失败：${src}`));
    img.src = src;
  });
}

async function renderAvatar(src: string, container: HTMLElement): Promise<void> {
  try {
    const img = await loadImage(src);
    container.appendChild(img);
  } catch {
    container.textContent = "头像加载失败";
  }
}
```

### 4. 语法理解

`HTMLImageElement` 描述图片元素，`HTMLScriptElement` 描述脚本元素。资源加载成功或失败时，浏览器会触发 `onload` 和 `onerror`。

### 5. 常见错误

- `src` 通常要最后赋值，否则可能错过事件绑定。
- `onerror` 里不要无限切换到同一个失败地址。
- 动态脚本加载成功后再调用第三方 SDK，不能假设脚本立刻可用。

### 6. 本节练习

写一个 `loadScript(src: string): Promise<HTMLScriptElement>` 函数，脚本加载成功时 resolve，失败时 reject。

### 7. 和 JavaScript 的关系

参考文章里的 `onload/onerror` 逻辑可以直接迁移到 TS。TS 负责把图片、脚本、容器元素和 Promise 结果类型说清楚。

---

## 21. try...catch 和错误类型

### 1. 标准语法格式

```ts
try {
  // 可能出错的代码
} catch (error: unknown) {
  if (error instanceof Error) {
    console.log(error.message);
  }
}
```

### 2. 基础例子

```ts
try {
  JSON.parse("{ 错误 JSON }");
} catch (error: unknown) {
  if (error instanceof Error) {
    console.log(error.message);
  }
}
```

### 3. 实际开发例子

```ts
async function safeFetchJson<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return (await response.json()) as T;
  } catch (error: unknown) {
    if (error instanceof Error) {
      console.error("请求失败：", error.message);
    }

    return null;
  }
}
```

### 4. 语法理解

在严格模式下，`catch` 里的错误更适合按 `unknown` 处理，因为 JavaScript 允许抛出任何值：

```ts
throw "错误字符串";
throw 123;
throw new Error("错误对象");
```

所以访问 `error.message` 前，应该先判断 `error instanceof Error`。

### 5. 常见错误

- 直接写 `error.message` 可能出现 `error is of type 'unknown'`。
- `try...catch` 捕获不到语法错误。
- 异步回调里的错误要在回调内部捕获，或者用 Promise/async 统一处理。

### 6. 本节练习

写一个 `parseJson<T>(text: string): T | null` 函数，JSON 解析失败时返回 `null`。

### 7. 和 JavaScript 的关系

`try...catch` 是 JavaScript 错误处理语法。TypeScript 的增强点是提醒你不要假设捕获到的一定是 `Error` 对象。

---

## 22. JS 代码如何加类型

### 1. 标准语法格式

```ts
// 第一步：给数据结构起类型
type 数据类型 = {
  属性: 类型;
};

// 第二步：给函数参数和返回值加类型
function 函数名(参数: 参数类型): 返回值类型 {
  return 返回值;
}

// 第三步：给异步结果加 Promise 类型
async function 异步函数(): Promise<结果类型> {
  return 结果;
}
```

### 2. 基础例子

JavaScript 写法：

```js
function add(a, b) {
  return a + b;
}
```

TypeScript 写法：

```ts
function add(a: number, b: number): number {
  return a + b;
}
```

### 3. 实际开发例子

JavaScript 写法：

```js
async function login(username, password) {
  const response = await fetch("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  return response.json();
}
```

TypeScript 写法：

```ts
type LoginResponse = {
  token: string;
  user: {
    id: number;
    name: string;
  };
};

async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  return (await response.json()) as LoginResponse;
}
```

### 4. 语法理解

JS 改 TS 的顺序可以很固定：

1. 先找数据结构，比如用户、商品、订单。
2. 再给函数参数和返回值加类型。
3. 再处理 DOM、事件、接口返回值。
4. 最后逐步消灭 `any` 和不安全的 `as`。

### 5. 常见错误

- `Object is possibly 'null'`：通常是 DOM 查询结果可能为空，需要判空或使用更准确的断言。
- `Property 'value' does not exist on type 'Element'`：说明当前类型太宽，要判断或断言成 `HTMLInputElement`。
- `error is of type 'unknown'`：说明 `catch` 里的错误要先判断 `instanceof Error`。
- `Type 'string' is not assignable to type ...`：说明你传入的字符串不在目标类型允许范围内，常见于字面量联合类型。

### 6. 本节练习

把下面 JS 思路改成 TS：输入商品价格数组，筛选出大于 100 的商品价格，计算总价，并返回格式化字符串。

### 7. 和 JavaScript 的关系

TypeScript 学习的关键不是抛弃 JavaScript，而是给已经会写的 JS 补上类型边界。你越熟悉 JS 的字符串、数组、函数、Promise，学 TS 时就越能理解类型写在哪里。

---

## 22.5 装饰器入门与认识

### 1. 标准语法格式

开启实验性装饰器配置：

```json
{
  "compilerOptions": {
    "experimentalDecorators": true
  }
}
```

类装饰器：

```ts
function 装饰器名(target: Function): void {
  // target 是被装饰的类
}

@装饰器名
class 类名 {}
```

装饰器工厂：

```ts
function 装饰器工厂(参数: 参数类型) {
  return function (target: Function): void {
    // 装饰逻辑
  };
}

@装饰器工厂(参数)
class 类名 {}
```

常见装饰器类型：

```ts
// 类装饰器
function ClassDecorator(target: Function): void {}

// 属性装饰器
function PropertyDecorator(target: object, propertyKey: string | symbol): void {}

// 方法装饰器
function MethodDecorator(
  target: object,
  propertyKey: string | symbol,
  descriptor: PropertyDescriptor
): void {}

// 参数装饰器
function ParameterDecorator(
  target: object,
  propertyKey: string | symbol | undefined,
  parameterIndex: number
): void {}
```

### 2. 基础例子

```ts
function LogClass(target: Function): void {
  console.log("类被定义了：", target.name);
}

@LogClass
class Person {
  constructor(public name: string) {}
}
```

装饰器会在类定义时执行，而不是创建实例时才执行。

### 3. 实际开发例子

给类的原型补一个方法：

```ts
interface User {
  introduce(): void;
}

function AddIntroduce(target: Function): void {
  target.prototype.introduce = function (): void {
    console.log(`我是 ${this.name}`);
  };
}

@AddIntroduce
class User {
  constructor(public name: string) {}
}

const user = new User("Alice");
user.introduce();
```

装饰器工厂：

```ts
function RepeatLog(count: number) {
  return function (target: Function): void {
    target.prototype.logName = function (): void {
      for (let i = 0; i < count; i++) {
        console.log(this.name);
      }
    };
  };
}

interface Product {
  logName(): void;
}

@RepeatLog(3)
class Product {
  constructor(public name: string) {}
}
```

装饰器组合执行顺序：

```ts
function A(target: Function): void {
  console.log("A");
}

function B() {
  console.log("B 工厂");
  return function (target: Function): void {
    console.log("B");
  };
}

@A
@B()
class Demo {}
```

装饰器工厂会先从上到下执行，真正的装饰器函数再从下到上执行。

### 4. 语法理解

装饰器本质是函数。它可以在类、属性、方法、访问器、参数上附加逻辑，常见于框架和库，比如依赖注入、路由注册、权限校验、日志记录。

初学阶段重点理解三件事：

- `@Decorator` 是把函数应用到目标上。
- 装饰器通常在定义阶段执行。
- 装饰器会受 TypeScript 版本、编译配置、框架约定影响。

### 5. 常见错误

- 忘记在 `tsconfig.json` 中开启 `experimentalDecorators`。
- 以为装饰器是普通函数调用，忽略它的执行时机。
- 通过装饰器动态添加实例方法后，忘记用接口声明补充类型。
- 不同 TS 版本和不同框架的装饰器语义可能有差异，实际项目要看项目配置。
- 初学阶段不要把装饰器当成必学核心语法，它更偏进阶和框架应用。

### 6. 本节练习

写一个 `@LogCreate` 类装饰器，在类定义时打印类名。再写一个 `@AddCreatedTime` 类装饰器，给实例添加 `createdTime: Date` 属性，并用接口补充类型声明。

### 7. 和 JavaScript 的关系

装饰器不是普通 JavaScript 的稳定基础语法。它是 TypeScript 和部分现代框架常用的增强写法，最终仍然会被编译成 JavaScript。学习装饰器的重点是能看懂框架代码，而不是一开始就大量使用。

---

## 23. 学习路线总结

如果你刚学完 JavaScript，建议按下面顺序掌握 TypeScript：

1. 先掌握变量、函数、数组、对象的类型写法。
2. 再掌握 `type`、`interface`、联合类型。
3. 然后学习类与面向对象、DOM、事件、fetch 这些常见开发场景。
4. 再学习泛型、模块化、`tsconfig.json`。
5. 最后把装饰器当作进阶内容，用于看懂框架和库。

不要一开始就钻复杂类型和装饰器。初学阶段最重要的是能把日常 JS 代码写成清楚、稳定、可维护的 TS 代码。

## 24. 综合练习

用 TypeScript 写一个简单 Todo 页面逻辑，要求：

1. 定义 `Todo` 类型：
   - `id: number`
   - `title: string`
   - `done: boolean`
2. 获取输入框和按钮。
3. 点击按钮时创建一个 Todo。
4. 把 Todo 放进 `Todo[]` 数组。
5. 渲染 Todo 标题列表。
6. 输入为空时不允许添加。

可以先不写复杂样式，重点是把类型写清楚。


<section class="legacy-comments">
  <h2>评论区</h2>
  <div id="twikoo-article_1778150721669" data-twikoo-path="article_1778150721669"></div>
</section>
