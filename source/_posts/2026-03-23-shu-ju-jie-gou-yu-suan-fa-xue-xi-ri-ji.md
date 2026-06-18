---
title: "数据结构与算法学习日记"
date: "2026-03-23"
updated: "2026-03-23"
categories:
  - "数据结构与算法"
old_id: "article_1774253776836"
twikooPath: "article_1774253776836"
---
<h2>数据结构与算法学习日记</h2>
2026.3.23
也许很快就会给博客更新代码高亮显示功能…？

2026年3月23日19:38:08
想到自己以前总是眼高手低，想得太多而做得太少，故创建这篇博客来记录自己学习数据结构与算法的过程
顺便更新了博客显示代码块的功能

<strong>1.合并两个有序链表</strong>
<a href="https://leetcode.cn/problems/merge-two-sorted-lists/" target="_blank" style="color: #0366d6; text-decoration: underline;">点击这里跳转</a>
<pre><code class="language-c++">
class Solution {
public:
    ListNode* mergeTwoLists(ListNode* list1, ListNode* list2) {
        //创建虚拟头结点
        ListNode dummy(-1);
        ListNode *p = &dummy;

        ListNode *p1 = list1;
        ListNode *p2 = list2;

        while(p1 != nullptr && p2 != nullptr){
            if(p1->val > p2->val){
                p->next = p2;
                p2 = p2->next;
            }else{
                p->next = p1;
                p1 = p1->next;
            }
            p = p->next;
        }

        if(p1 != nullptr){
            p->next = p1;
        }

        if(p2 != nullptr){
            p->next = p2;
        }

        return dummy.next;
    }
};
</code></pre>
<span style="color: red; font-weight: bold;">什么时候使用虚拟头结点：当你需要创造一条新链表的时候</span>
头结点的作用：
（1）：统一处理空链表和头结点。如果没有虚拟头节点，当需要操作头节点时（比如删除、插入、或像本题这样需要将头节点移动到另一个链表），代码会变得很复杂，需要额外判断 head 是否为空或是否要修改 head
（2）：避免复杂的空指针判断。使用虚拟头节点后，所有节点操作都可以用相同的逻辑处理，无需区分第一个节点和后续节点。
（3）：简化边界条件处理

<strong>2.分隔链表</strong>
<a href="https://leetcode.cn/problems/partition-list/description/" target="_blank" style="color: #0366d6; text-decoration: underline;">点击这里跳转</a>

<pre><code class="language-javascript">
class Solution {
public:
    ListNode* partition(ListNode* head, int x) {
        // 存放小于 x 的链表的虚拟头结点
        ListNode* dummy1 = new ListNode(-1);
        // 存放大于等于 x 的链表的虚拟头结点
        ListNode* dummy2 = new ListNode(-1);
        // p1, p2 指针负责生成结果链表
        ListNode* p1 = dummy1, *p2 = dummy2;
        // p 负责遍历原链表，类似合并两个有序链表的逻辑
        // 这里是将一个链表分解成两个链表
        ListNode* p = head;
        while (p != nullptr) {
            if (p->val >= x) {
                p2->next = p;
                p2 = p2->next;
            } else {
                p1->next = p;
                p1 = p1->next;
            }
            // 不能直接让 p 指针前进，
            // p = p->next
            // 断开原链表中的每个节点的 next 指针
            ListNode* temp = p->next;
            p->next = nullptr;
            p = temp;
        }
        // 连接两个链表
        p1->next = dummy2->next;

        return dummy1->next;
    }
};
</code></pre>
<strong>为什么在创建虚拟头结点的时候需要使用new？</strong>
使用虚拟头节点（无论 new 还是栈上）是链表题目的最佳实践，它能：
1.消除对头节点的特殊处理
2.让代码逻辑更清晰
3.减少边界条件 bug

至于用 new 还是栈上分配，两种都可以：
用 new：习惯使然，和原链表节点创建方式一致
用栈上：更简洁，无需 delete，但要注意虚拟节点的 next 被修改后，不能通过虚拟节点本身访问链表（这本来就不需要）

对比总结
写法	                                        优点	                                                         缺点
new 创建虚拟头节点	统一处理逻辑，代码简洁	需要手动 delete（但力扣通常不检查）
栈上创建虚拟头节点	统一处理逻辑，无需 delete	需要小心作用域，返回后栈对象被销毁但它的 next 还在用（这没问题）
不用虚拟头节点                  	无额外内存	                                      代码复杂，边界条件多

<span style="color: red; font-weight: bold;">注：本题在while循环最后不能直接让p = p->next</span>
否则会让p2链表指向p1链表的最后一个节点，使得两个链表形成一个环

<span style="color: #0366d6; font-weight: bold;">总的来说，如果我们需要把原链表的节点接到新链表上，而不是 new 新节点来组成新链表的话，那么断开节点和原链表之间的链接可能是必要的。那其实我们可以养成一个好习惯，但凡遇到这种情况，就把原链表的节点断开，这样就不会出错了。</span>

<section class="legacy-comments">
  <h2>评论区</h2>
  <div id="twikoo-article_1774253776836" data-twikoo-path="article_1774253776836"></div>
</section>
