# livecodebench — `lcb-abc396_b`

## Question

```
There is a stack of 100 cards, each labeled with the integer 0.
Process Q queries. Each query is of one of the following:

- Type 1: Place a card labeled with an integer x on top of the stack.
- Type 2: Remove the top card of the stack and output the integer written on that removed card. Under the constraints of this problem, the stack always has at least one card.

Input

The input is given from Standard Input in the following format:
Q
\text{query}_1
\text{query}_2
\vdots
\text{query}_Q

The i-th query \text{query}_i starts with the query type c_i (1 or 2), followed by the integer x if c_i=1.
That is, each query is in one of the following two formats:
1 x

2

Output

Let q be the number of queries with c_i=2. Print q lines.
The j-th line (1 \le j \le q) should contain the answer to the j-th such query.

Constraints


- 1 \le Q \le 100
- 1 \le x \le 100
- There is at least one query of type 2.
- All input values are integers.

Sample Input 1

6
2
1 4
1 3
2
2
2

Sample Output 1

0
3
4
0

After processing each query, the stack is as follows:

- Remove the top card of the stack. The integer on the removed card is 0, so output 0.
- The stack then has 99 cards labeled with 0.


- Add a card labeled 4 on top.
- The stack then has 1 card labeled 4, and 99 cards labeled 0, from top to bottom.


- Add a card labeled 3 on top.
- The stack then has 1 card labeled 3, 1 card labeled 4, and 99 cards labeled 0, from top to bottom.


- Remove the top card. The integer on that card is 3, so output 3.
- The stack then has 1 card labeled 4, and 99 cards labeled 0, from top to bottom.


- Remove the top card. The integer on that card is 4, so output 4.
- The stack then has 99 cards labeled 0.


- Remove the top card. The integer on that card is 0, so output 0.
- The stack then has 98 cards labeled 0.

Sample Input 2

5
2
2
2
2
2

Sample Output 2

0
0
0
0
0
```

**Graded by:** LiveCodeBench executor (atcoder, easy)

## Comparison

| model | reasoning steps | completion tokens | seed |
|---|---|---|---|
| 32B | 82 | 2201 | 1000 |
| 1.5B | 202 | 3442 | 1000 |

## 32B — seed 1000 — 82 steps (2201 tokens)

**Step 1**

Okay, I need to solve this problem. Let's read it carefully.

**Step 2**

So, there's a stack of 100 cards, each labeled 0. Then, we process Q queries. Each query is either type 1 or 2.

**Step 3**

Type 1: Place a card with x on top.
Type 2: Remove the top card and output its value. The stack always has at least one card.

**Step 4**

The output is for each type 2 query, print the number on the removed card.

**Step 5**

Hmm, so the stack starts with 100 zeros. When we add a card, it goes on top. When we remove, we take from the top.

**Step 6**

Let me think about the data structure. A stack is perfect here. So, I can represent the stack as a list, where the end is the top.

**Step 7**

Wait, but the initial stack is 100 zeros. So I can initialize a list with 100 zeros. But wait, when we add a new card, it goes on top, which is the end of the list. So for example, the initial stack is [0, 0, 0, ..., 0] (100 times). Then, when we do a type 1, we append x to the list. For type 2, we pop the last element and print it.

**Step 8**

Wait, no. Because the initial stack has 100 zeros, and the top is the first card. Wait, no, when you have a stack, the top is the last element. So when you add a card, it's placed on top, which is the end of the list.

**Step 9**

So for example, initial stack is [0, 0, ..., 0] (100 elements). After adding 4, it's [0, 0, ..., 0,4]. Then adding 3, it's [0,0,...,0,4,3]. Then, when we pop, we get 3, then 4, then 0, etc.

**Step 10**

Wait, but the sample input 1 shows that after the first type 2 query, the stack has 99 zeros. So the initial stack is 100 zeros, and the top is the first zero. Wait, no. Wait, when you have a stack, the top is the most recent element. So perhaps I need to model the stack as a list where the top is the end.

**Step 11**

Wait, in the sample input 1:

**Step 12**

After the first query (type 2), the output is 0. Then the stack has 99 cards. So the initial stack is 100 cards, and after removing one, it's 99. So the initial stack has 100 cards, all 0s. So the stack is a list of 100 zeros.

**Step 13**

So for the initial state, the stack is [0] * 100. Then, for each type 1 query, we add x to the end (stack.append(x)). For type 2, we pop the last element and print it.

**Step 14**

Wait, let's see the sample input 1:

**Step 15**

Sample Input 1:

**Step 16**

6
2 → output 0. Stack becomes 99 zeros.
1 4 → stack becomes 99 zeros +4 → 100 elements.
1 3 → stack is 99 zeros, 4,3 → 101 elements.
2 → pop 3, output 3. Stack now has 100 elements (99 zeros +4).
2 → pop 4, output 4. Stack now 99 zeros.
2 → pop 0, output 0.

**Step 17**

So the output is 0,3,4,0. Wait, but the sample output is four lines: 0,3,4,0. Because in the sample input, there are four type 2 queries.

**Step 18**

Wait, sample input 1 has six queries. Let's count the type 2's:

**Step 19**

Queries:
1. 2 → type 2 → output 0.
2. 1 4 → type 1.
3. 1 3 → type 1.
4. 2 → output 3.
5. 2 → output4.
6. 2 → output0.

**Step 20**

So four type 2 queries, and four outputs.

**Step 21**

So the initial stack is 100 zeros. So, in the code, I need to represent this stack.

**Step 22**

So in Python, I can initialize the stack as a list with 100 zeros.

**Step 23**

Then, for each query:

**Step 24**

If it's type 1, append x to the stack.

**Step 25**

If it's type 2, pop the last element and print it.

**Step 26**

Yes, that makes sense.

**Step 27**

So the plan is:

**Step 28**

1. Read Q.

**Step 29**

2. Initialize stack as [0] * 100.

**Step 30**

3. For each of Q queries:

**Step 31**

a. Read the query.

**Step 32**

b. If it's type 1, append x to stack.

**Step 33**

c. If it's type 2, pop the last element and print it.

**Step 34**

But wait, the initial stack is 100 elements, so when we process type 2, we can pop safely because the problem says that the stack always has at least one card.

**Step 35**

So the code should handle that.

**Step 36**

Testing with sample input 1:

**Step 37**

After the initial stack is [0] * 100.

**Step 38**

First query is 2: pop 0, output 0. Stack has 99 zeros.

**Step 39**

Then, add 4 → stack is 99 zeros +4 → 100 elements.

**Step 40**

Add 3 → 99 zeros +4,3 → 101 elements.

**Step 41**

Then, type 2: pop 3 → output 3. Stack is 99 zeros +4 → 100.

**Step 42**

Type 2: pop 4 → output4. Stack is 99 zeros.

**Step 43**

Type 2: pop 0 → output0.

**Step 44**

Which matches the sample output.

**Step 45**

Another sample input is 5 type 2 queries. Each time, the stack has 100, 99, 98, etc. So the first pop gives 0, then 0, etc.

**Step 46**

So the code should work.

**Step 47**

Now, the code:

**Step 48**

Read Q.

**Step 49**

Initialize stack = [0] * 100.

**Step 50**

Then, for each query in Q:

**Step 51**

Read the line, split into parts.

**Step 52**

If it's type 1, append x.

**Step 53**

Else, pop and print.

**Step 54**

Wait, but in Python, when you read from stdin, for each query, you need to read the entire line.

**Step 55**

So the code structure could be:

**Step 56**

Read Q.

**Step 57**

stack = [0] * 100

**Step 58**

for _ in range(Q):

**Step 59**

line = input().split()

**Step 60**

if line[0] == '1':

**Step 61**

x = int(line[1])

**Step 62**

stack.append(x)

**Step 63**

else:

**Step 64**

# type 2

**Step 65**

print(stack.pop())

**Step 66**

Yes.

**Step 67**

Wait, but in the first sample, the initial stack has 100 elements. After the first pop, it's 99, and the next appends bring it back to 100, then 101, etc.

**Step 68**

Yes.

**Step 69**

But wait, in the initial setup, the stack has 100 zeros. So the first pop is the last element of the initial 100 zeros, which is 0. So that's correct.

**Step 70**

Wait, because in the initial stack, the top is the last element. So yes.

**Step 71**

So the code seems correct.

**Step 72**

Testing sample input 2:

**Step 73**

5 queries, all type 2.

**Step 74**

Each time, pop the last element, which is 0.

**Step 75**

So output is 0,0,0,0,0. Which matches the sample.

**Step 76**

So the code should handle that.

**Step 77**

What about cases where we have multiple appends and pops?

**Step 78**

For example, if we have 100 type 1 queries, each adding 5, then 100 type 2 queries. The first 100 pops would be 5, then the next pops would be 0.

**Step 79**

But in the problem statement, the initial stack is 100 zeros, so after 100 appends, the stack has 100 zeros + 100 fives → 200 elements. Then, popping 100 times would remove all fives, leaving 100 zeros. Then, popping again gives 0.

**Step 80**

Yes.

**Step 81**

So the code should handle that.

**Step 82**

Thus, the code should be correct.

### Final answer (after `</think>`)

```
To solve this problem, we need to simulate a stack of cards where each card is labeled with an integer. The stack initially contains 100 cards, each labeled with 0. We will process a series of queries that either add a new card to the top of the stack or remove the top card and output its value.

### Approach
1. **Initialize the Stack**: Start with a stack of 100 cards, each labeled 0.
2. **Process Queries**: For each query:
   - If the query is of type 1, add a new card with the specified integer to the top of the stack.
   - If the query is of type 2, remove the top card from the stack and output its value.
3. **Stack Operations**: Use a list to represent the stack, where appending to the list simulates placing a card on top, and popping from the list simulates removing the top card.

### Solution Code
```python
# Read the number of queries
Q = int(input())
stack = [0] * 100  # Initialize stack with 100 zeros

for _ in range(Q):
    parts = input().split()
    if parts[0] == '1':
        x = int(parts[1])
        stack.append(x)
    else:
        print(stack.pop())
```

### Explanation
1. **Initialization**: The stack is initialized with 100 zeros, representing the initial state.
2. **Processing Queries**:
   - For type 1 queries, the integer is appended to the stack, making it the new top.
   - For type 2 queries, the top element is removed and printed. The stack operations ensure that the most recent elements are handled first, maintaining the correct order of the stack.
3. **Efficiency**: Each operation (append and pop) on the list is efficient, with an average time complexity of O(1), making the solution suitable for the given constraints.

This approach ensures that we correctly simulate the stack operations and handle each query efficiently.
```

## 1.5B — seed 1000 — 202 steps (3442 tokens)

**Step 1**

Okay, I have to solve this problem. Let's read it carefully.

**Step 2**

So, the problem is about a stack of 100 cards, each labeled with 0. We have to process Q queries. Each query is either adding a card or removing the top card and outputting its value.

**Step 3**

Hmm, the constraints are small: Q is up to 100. So I don't need to worry about efficiency beyond that. So the approach can be straightforward.

**Step 4**

Let me think about the data structure. Since each card is added to the top, the stack is a LIFO structure. So, for each add operation, we need to push the new x onto the stack. For remove operations, we need to pop the top element.

**Step 5**

Wait, but how to represent the stack? A list in Python can be used, where the first element is the top (since list is 0-indexed). So when we add a card, it's at the end. When we pop, we take the last element.

**Step 6**

Wait, but when you add to the top, it's the last element. So, for example, if the stack is [0], and you add 4, it becomes [0,4], but wait, no, that's not right. Because the top is the last element. So adding to the top would mean appending to the end. So the stack is represented as a list where the first element is the top.

**Step 7**

Wait no, in a stack, the top is the last element. So, when you add a new card to the top, you append it to the end. So, for example, if the stack is [0], adding 4 would make it [0,4], but the top is 4. So when you pop, you get 4, then 0.

**Step 8**

Wait, no, wait. Let me think again. The initial stack is [0,0,0,...] 100 times. So when you add a card, you add to the top, which is the end of the list. So, for example, adding 4 to the stack makes it [0,0,0,...,4]. So when you pop, the top is 4.

**Step 9**

Wait, no. Let's see:

**Step 10**

Original stack: [0,0,0,...,0] (100 elements). The top is the last element. So when you add a new card, it's placed on top, so the list becomes [0,0,...,0, x]. So, the top is the last element, x.

**Step 11**

Wait, no. Because when you add to the top, the new card is on top, which is the next position after the current top. So, for a stack represented as a list, the first element is the bottom, the last is the top. So when you push x, you append it to the end. So, for example:

**Step 12**

Initial stack: [0,0,0,...,0] (100 elements). The top is the last 0.

**Step 13**

After adding a 4, the stack becomes [0,0,0,...,0,4]. The top is 4.

**Step 14**

So, for each add, we push x to the end of the list. For each remove, we pop the last element.

**Step 15**

So, the steps for the sample input 1:

**Step 16**

Sample Input 1:
6
2
1 4
1 3
2
2
2

**Step 17**

Processing:

**Step 18**

1. Query type 2: pop top (0), output 0. Stack is now 99 zeros.
2. Add 4: stack is [0,0,...,0,4].
3. Add 3: stack is [0,0,...,0,4,3].
4. Remove top: 3. Output 3.
5. Remove top:4. Output4.
6. Remove top:0. Output0.

**Step 19**

Which matches the sample output.

**Step 20**

So, in Python, the initial stack is a list of 100 zeros. Then, for each query:

**Step 21**

If it's type 1, append x to the list.

**Step 22**

If it's type 2, pop the last element, and output it.

**Step 23**

So, the plan is:

**Step 24**

- Initialize the stack as [0] * 100. Or, perhaps, create a list of 100 zeros.

**Step 25**

But wait, wait. Wait, no. The initial stack has 100 cards, all 0. So when we process the queries, the stack starts as [0,0,0,...,0] (100 elements).

**Step 26**

Wait, no. Wait, the initial stack has 100 cards, each labeled 0. So the stack is a list of 100 0s.

**Step 27**

So, in code:

**Step 28**

stack = [0] * 100

**Step 29**

Then, for each query:

**Step 30**

If type is 1:

**Step 31**

stack.append(x)

**Step 32**

If type is 2:

**Step 33**

print(stack.pop())

**Step 34**

But wait, for the sample input 1:

**Step 35**

After processing the first query (type 2), stack is 99 0s.

**Step 36**

Then, type 1 x=4: stack becomes [0,0,...,0,4].

**Step 37**

Type 1 x=3: stack is [0,0,...,0,4,3].

**Step 38**

Then, type 2: pop 3, output 3.

**Step 39**

Then, type 2: pop 4.

**Step 40**

Type 2: pop 0.

**Step 41**

So, the sample output is as expected.

**Step 42**

So, that seems correct.

**Step 43**

Now, in terms of code:

**Step 44**

We can read Q, then read Q lines, each starting with a type. For each line, if it's type 1, append x to the stack. Else, pop and print.

**Step 45**

But wait, the problem says that the stack always has at least one card, so we don't have to handle the case where pop is called when the stack is empty.

**Step 46**

So, in code:

**Step 47**

Read Q.

**Step 48**

stack = [0] * 100

**Step 49**

count = 0

**Step 50**

for each of Q queries:

**Step 51**

read the query line.

**Step 52**

if query starts with 1:

**Step 53**

x = int(query.split()[1])

**Step 54**

stack.append(x)

**Step 55**

else:

**Step 56**

print(stack.pop())

**Step 57**

count +=1

**Step 58**

So, after processing all queries, print count.

**Step 59**

Wait, but the problem says that the output is q lines, where q is the number of type 2 queries. So, we have to count how many type 2 queries there are, and output that many lines.

**Step 60**

Wait, no. Let me read the problem statement again.

**Step 61**

The j-th line (1<=j<=q) should contain the answer to the j-th such query. So, for each type 2 query, we output the popped value.

**Step 62**

So, the code should collect all the type 2 outputs, count them, and then output them in order.

**Step 63**

Wait, no. Because for each type 2 query, we output the value. So, the number of type 2 queries is the number of lines to print. So, in the sample input 1, there are 4 type 2 queries, so 4 lines are printed.

**Step 64**

So, in code, the output is the count of type 2 queries, each line is the popped value.

**Step 65**

So, in the code:

**Step 66**

We can have a variable to track the number of type 2 queries, say q_count, and for each type 2 query, we print the value.

**Step 67**

But wait, no. Because for each type 2 query, we have to print the popped value. So, the number of type 2 queries is the number of lines to print.

**Step 68**

Wait, but the problem says that the output is q lines, where q is the number of type 2 queries. So, the code should collect all the outputs from type 2 queries, and print them in order.

**Step 69**

So, the code can have a list to collect the outputs.

**Step 70**

For example:

**Step 71**

outputs = []

**Step 72**

for each query:

**Step 73**

if type 2:

**Step 74**

outputs.append(stack.pop())

**Step 75**

Then, after all queries, print each element of outputs.

**Step 76**

Yes, that's better. Because the outputs can be collected in a list, and then printed.

**Step 77**

So, in the code:

**Step 78**

Read Q.

**Step 79**

stack = [0] * 100

**Step 80**

outputs = []

**Step 81**

for _ in range(Q):

**Step 82**

query = input().split()

**Step 83**

if query[0] == '2':

**Step 84**

# type 2: pop and add to outputs

**Step 85**

outputs.append(stack.pop())

**Step 86**

else:

**Step 87**

x = int(query[1])

**Step 88**

stack.append(x)

**Step 89**

Then, after processing all queries, print each in outputs, each on a new line.

**Step 90**

Wait, but the sample input 1's outputs are:

**Step 91**

0 (from first 2), 3,4,0.

**Step 92**

So, the outputs list is [0,3,4,0], which when printed in order, gives the correct output.

**Step 93**

So, the code is correct.

**Step 94**

Now, the sample input 2:

**Step 95**

5

**Step 96**

All queries are type 2, each outputs 2.

**Step 97**

So, after 5 type 2 queries, the output is 5 lines, each with 2.

**Step 98**

Which matches the sample output.

**Step 99**

So, the code should handle that.

**Step 100**

Now, let's think about edge cases.

**Step 101**

What if the stack is empty? But the problem states that the stack always has at least one card, so we don't have to handle that.

**Step 102**

Another edge case: when multiple type 2 queries are in a row, popping the same card multiple times.

**Step 103**

So, for example, adding 5, then 3, then 5, then 3.

**Step 104**

So, stack is [5,3,5,3].

**Step 105**

Type 2 queries: pop 3, then 5, then 3, then5.

**Step 106**

So, the outputs would be 3,5,3,5.

**Step 107**

Which the code correctly handles.

**Step 108**

So, the code should be correct.

**Step 109**

Now, implement this in Python.

**Step 110**

The code steps:

**Step 111**

Read Q.

**Step 112**

Initialize stack as [0]*100.

**Step 113**

Initialize outputs as empty list.

**Step 114**

For each query:

**Step 115**

Read the line.

**Step 116**

Split into parts.

**Step 117**

If the first part is '2', pop from stack and append to outputs.

**Step 118**

Else, append x to stack.

**Step 119**

After all queries, for each item in outputs, print it.

**Step 120**

Wait, but the code as I wrote earlier for the first approach: for each query, process and collect the outputs.

**Step 121**

Wait, in the first approach, in the code, the stack is [0]*100, and for each type 2 query, stack.pop() is called, which removes the top.

**Step 122**

But the stack is a list, and when we pop, it's the last element.

**Step 123**

Yes.

**Step 124**

So, the code in Python would be:

**Step 125**

Read Q.

**Step 126**

stack = [0] * 100

**Step 127**

outputs = []

**Step 128**

for _ in range(Q):

**Step 129**

query = input().split()

**Step 130**

if query[0] == '2':

**Step 131**

outputs.append(stack.pop())

**Step 132**

else:

**Step 133**

x = int(query[1])

**Step 134**

stack.append(x)

**Step 135**

for output in outputs:

**Step 136**

print(output)

**Step 137**

Wait, but wait: in the first approach, the stack is a list, and popping the last element is the correct way. So that should be correct.

**Step 138**

Wait, but let me think about the sample input 1:

**Step 139**

After the first query, stack is [0,0,0,...,0] (99 0s), then 4 is added, making it [0,...,0,4], then 3 is added, making [0,...,0,4,3], then pop 3, then 4, then 0.

**Step 140**

So the outputs are [3,4,0], but the code appends the popped values in the order of the queries.

**Step 141**

Wait, in the first query (type 2), stack.pop() returns 0, which is correct.

**Step 142**

Wait, no. Wait, the initial stack is [0,0,...,0]. So when you pop, it's 0.

**Step 143**

In the first type 2 query, the output is 0.

**Step 144**

Then, after adding 4 and 3, the stack is [0,0,...,0,4,3]. So next type 2 query pops 3, which is correct.

**Step 145**

Then, next type 2 pops 4, then 0.

**Step 146**

So, the outputs list is [0,3,4,0], which is correct.

**Step 147**

So, the code should handle that correctly.

**Step 148**

I think this should work.

**Step 149**

Now, testing the code.

**Step 150**

Sample Input 1:

**Step 151**

6

**Step 152**

Queries:

**Step 153**

2 → pop 0.

**Step 154**

1 4 → stack becomes [0,0,...,0,4]

**Step 155**

1 3 → stack becomes [0,0,...,0,4,3]

**Step 156**

2 → pop 3.

**Step 157**

2 → pop4.

**Step 158**

2 → pop0.

**Step 159**

So, outputs are [0,3,4,0].

**Step 160**

Which is correct.

**Step 161**

Another test case: all type 2.

**Step 162**

Sample Input 2:

**Step 163**

5

**Step 164**

All queries are 2.

**Step 165**

So, after each, the output is 2.

**Step 166**

So, the code should output 5 lines of 2.

**Step 167**

Which it will.

**Step 168**

Another test case: adding multiple cards.

**Step 169**

Like:

**Step 170**

3

**Step 171**

1 5

**Step 172**

1 6

**Step 173**

2 → output 6.

**Step 174**

So, after 3 queries, the stack is [5,6]. So the output is 6.

**Step 175**

Yes.

**Step 176**

Another test case: adding in reverse order.

**Step 177**

So, queries:

**Step 178**

2 → output 0.

**Step 179**

1 5 → stack [0,5]

**Step 180**

1 6 → stack [0,5,6]

**Step 181**

2 → output 6.

**Step 182**

So, outputs are [0,6].

**Step 183**

Yes.

**Step 184**

So, the code should handle all cases.

**Step 185**

Now, let's write the code.

**Step 186**

The code will read Q, then process each query, collect the outputs, and print them.

**Step 187**

So, the code:

**Step 188**

Read Q.

**Step 189**

stack = [0] * 100

**Step 190**

outputs = []

**Step 191**

for _ in range(Q):

**Step 192**

parts = input().split()

**Step 193**

if parts[0] == '2':

**Step 194**

outputs.append(stack.pop())

**Step 195**

else:

**Step 196**

x = int(parts[1])

**Step 197**

stack.append(x)

**Step 198**

for output in outputs:

**Step 199**

print(output)

**Step 200**

Wait, but in Python, when you have a list of integers, and you print them, each print adds a new line, which is correct.

**Step 201**

Yes.

**Step 202**

So, that's the code.

### Final answer (after `</think>`)

```
To solve this problem, we need to simulate the process of adding cards to a stack and removing the top card repeatedly. Each card has an integer label, and we need to output the label of the card removed at each type 2 query.

### Approach
1. **Initialization**: Start with a stack of 100 cards, each labeled with the integer 0.
2. **Processing Queries**: For each query:
   - If the query is of type 1, add a new card with the given integer label to the top of the stack.
   - If the query is of type 2, remove the top card from the stack and output its label.
3. **Output Management**: Collect all the outputs of type 2 queries and print them in order.

The stack is represented as a list in Python, where the first element is the top of the stack. This allows efficient appending (for type 1 queries) and popping (for type 2 queries).

### Solution Code
```python
Q = int(input())
stack = [0] * 100
outputs = []

for _ in range(Q):
    parts = input().split()
    if parts[0] == '2':
        outputs.append(stack.pop())
    else:
        x = int(parts[1])
        stack.append(x)

for output in outputs:
    print(output)
```

### Explanation
- **Initialization**: We start with a list `stack` containing 100 zeros. This list represents the stack where the first element is the top card.
- **Processing Queries**: For each query:
  - If the query is type 1, we read the integer and append it to the end of the list.
  - If the query is type 2, we pop the last element from the list and store it in the `outputs` list.
- **Output Management**: After processing all queries, we print each value in the `outputs` list, which contains all the values of type 2 queries in the order they were processed.

This approach efficiently handles the problem constraints and ensures that each operation (append and pop) is performed in constant time, making the solution both time and space efficient.
```
