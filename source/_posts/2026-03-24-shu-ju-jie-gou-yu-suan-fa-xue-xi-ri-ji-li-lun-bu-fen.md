---
title: "数据结构与算法学习日记（理论部分）"
date: "2026-03-24"
updated: "2026-03-25"
categories:
  - "数据结构与算法"
old_id: "article_1774365835226"
twikooPath: "article_1774365835226"
---
<h2>数据结构与算法学习日记（理论部分）</h2>
<strong>1.优先级队列及二叉堆</strong>
参考文章：<a href="https://labuladong.online/zh/algo/data-structure-basic/binary-heap-implement/#%E7%AE%80%E5%8C%96%E7%89%88%E4%BC%98%E5%85%88%E7%BA%A7%E9%98%9F%E5%88%97" target="_blank" style="color: #0366d6; text-decoration: underline;">点击这里跳转</a>

我们可以使用数组来模拟二叉堆（本质上还是一棵二叉树）
此处我们只讨论索引从0开始的情况

<img src="/images/img_1774365422873.png" alt="图片" style="max-width: 100%;">
因此我们可以得到父节点，左右子节点的索引公式

<pre><code class="language-javascript">
// 父节点的索引
int parent(int node) {
    return (node - 1) / 2;
}

// 左子节点的索引
int left(int node) {
    return node * 2 + 1;
}

// 右子节点的索引
int right(int node) {
    return node * 2 + 2;
}
</code></pre>

<strong>核心操作：增</strong>
以小顶堆为例，向小顶堆中插入新元素遵循两个步骤：
1、先把新元素追加到二叉树底层的最右侧，保持完全二叉树的结构。此时该元素的父节点可能比它大，不满足小顶堆的性质。
2、为了恢复小顶堆的性质，需要将这个新元素不断上浮（swim），直到它的父节点比它小为止，或者到达根节点。此时整个二叉树就满足小顶堆的性质了。

<strong>核心操作：删</strong>
以小顶堆为例，删除小顶堆的堆顶元素遵循两个步骤：
1、先把堆顶元素删除，把二叉树底层的最右侧元素摘除并移动到堆顶，保持完全二叉树的结构。此时堆顶元素可能比它的子节点大，不满足小顶堆的性质。
2、为了恢复小顶堆的性质，需要将这个新的堆顶元素不断下沉（sink），直到它比它的子节点小为止，或者到达叶子节点。此时整个二叉树就满足小顶堆的性质了。

<span style="color: #0366d6;">用数组模拟二叉堆的原因</span>
1.链表节点需要一个额外的指针存储相邻节点的地址，所以相对数组，链表的内存消耗会大一些。
2.假如我们使用二叉树来构造二叉堆，那么就需要层序遍历或递归遍历二叉树，时间复杂度是 O（N），导致push和pop方法的时间复杂度也为O（N），假如我们使用数组，那么时间复杂度就为O（1）

<span style="color: #0366d6;">优先级队列完整代码实现</span>
此处以二叉堆实现为例

<pre><code class="language-cpp">
#include &lt;iostream&gt;
#include &lt;vector&gt;
#include &lt;functional&gt;
#include &lt;stdexcept&gt;
#include &lt;algorithm&gt;  // 添加这个头文件用于 std::swap

template&lt;typename T&gt;
class MyPriorityQueue{
private:
    //堆数组
    std::vector&lt;T&gt; heap;

    //堆中元素的数量
    int size;

    //元素比较器
    std::function&lt;bool(const T&, const T&)&gt; comparator;

    //父节点的索引
    int parent(int node){
        return (node - 1) / 2;
    }

    //左子节点的索引
    int left(int node){
        return node * 2 + 1;
    }

    //右子节点的索引
    int right(int node){
        return node * 2 + 2;
    }

    //交换数组的两个元素
    void swap(int i, int j){
        std::swap(heap[i], heap[j]);  // 使用 std::swap
    }

    //调整堆的大小
    void resize(int capacity){
        heap.resize(capacity);
    }

    //上浮操作，时间复杂度是树高O(logN)
    void swim(int node){
        while(node &gt; 0 && comparator(heap[parent(node)], heap[node])){
            swap(parent(node), node);
            node = parent(node);
        }
    }

    //下沉操作
    void sink(int node){
        while(left(node) &lt; size){
            int min = node;
            int l = left(node);
            int r = right(node);
            
            // 使用 comparator 进行比较
            if(l &lt; size && comparator(heap[min], heap[l])){
                min = l;
            }
            if(r &lt; size && comparator(heap[min], heap[r])){
                min = r;
            }
            
            if(min == node){
                break;
            }
            
            swap(node, min);
            node = min;
        }
    }

public:
    //构造函数 - 参数名改为 comp 避免与成员变量混淆
    MyPriorityQueue(int capacity, std::function&lt;bool(const T&, const T&)&gt; comp)
        : heap(capacity), size(0), comparator(std::move(comp)){}

    //返回堆的大小
    int getSize() const{
        return size;
    }

    //判断堆是否为空
    bool isEmpty() const{
        return size == 0;
    }

    //查，返回堆顶元素,时间复杂度O(1)
    const T& peek() const{
        if(isEmpty()){
            throw std::underflow_error("Priority queue underflow"); 
        }
        return heap[0];
    }

    //增，向堆中插入一个元素，时间复杂度O(logN)
    void push(const T& x){
        //扩容
        if(size == heap.size()){
            if(heap.size() == 0){
                resize(1);
            } else {
                resize(2 * heap.size());
            }
        }
        //把新元素追加到最后
        heap[size] = x;
        //然后上浮到正确位置
        swim(size);
        size++;
    }

    //删，删除堆顶元素，时间复杂度O(logN)
    T pop(){
        if(isEmpty()){
            throw std::underflow_error("Priority queue underflow");
        }
        T res = heap[0];
        //把堆底元素放到堆顶
        swap(0, size - 1);
        size--;
        //然后下沉到正确位置
        sink(0);
        //缩容
        if(size &gt; 0 && size &lt;= heap.size() / 4 && heap.size() &gt; 1){
            resize(heap.size() / 2);
        }
        return res;
    }
};

// 测试代码
int main() {
    // 使用lambda表达式来传递比较器
    // 小顶堆
    MyPriorityQueue&lt;int&gt; pq(3, [](const int& a, const int& b) { return a &gt; b; });
    pq.push(3);
    pq.push(1);
    pq.push(4);
    pq.push(1);
    pq.push(5);
    pq.push(9);

    // 1 1 3 4 5 9
    while (!pq.isEmpty()) {
        std::cout &lt;&lt; pq.pop() &lt;&lt; " ";
    }
    std::cout &lt;&lt; std::endl;

    // 测试大顶堆
    MyPriorityQueue&lt;int&gt; pq2(3, [](const int& a, const int& b) { return a &lt; b; });
    pq2.push(3);
    pq2.push(1);
    pq2.push(4);
    pq2.push(1);
    pq2.push(5);
    pq2.push(9);

    // 9 5 4 3 1 1
    while (!pq2.isEmpty()) {
        std::cout &lt;&lt; pq2.pop() &lt;&lt; " ";
    }
    std::cout &lt;&lt; std::endl;

    return 0;
}
</code></pre>

语法部分：
1.什么时候应该用move？

<pre><code class="language-none">
// 1. 构造函数参数（避免拷贝）
MyClass(std::vector&lt;int&gt; v) : data(std::move(v)) {}

// 2. 函数返回值（自动移动，不需要显式move）
vector&lt;int&gt; createVector() {
    vector&lt;int&gt; v = {1, 2, 3};
    return v;  // 自动移动，不需要 std::move(v)
}

// 3. 转移资源所有权
unique_ptr&lt;Widget&gt; ptr1 = make_unique&lt;Widget&gt;();
unique_ptr&lt;Widget&gt; ptr2 = std::move(ptr1);  // ptr1 失去所有权
</code></pre>

2.std::function<bool(const T&, const T&)> comp
等价写法：

<pre><code class="language-none">
// std::function 写法
std::function&lt;bool(const T&, const T&)&gt; comp;

// 等价的函数指针写法
bool (*comp)(const T&, const T&);

// 等价的函数引用写法
bool (&comp)(const T&, const T&);
</code></pre>



<section class="legacy-comments">
  <h2>评论区</h2>
  <div id="twikoo-article_1774365835226" data-twikoo-path="article_1774365835226"></div>
</section>
