# livecodebench — `lcb-abc398_c`

## Question

```
There are N people, labeled 1 to N. Person i has an integer A_i.
Among the people who satisfy the condition "None of the other N-1 people has the same integer as themselves," find the one with the greatest integer, and print that person's label.
If no person satisfies the condition, report that fact instead.

Input

The input is given from Standard Input in the following format:
N
A_1 A_2 \ldots A_N

Output

If no person satisfies the condition "None of the other N-1 people has the same integer as themselves," print -1.
Otherwise, among those who satisfy it, print the label of the person whose integer is the largest.

Constraints


- 1 \leq N \leq 3\times 10^5
- 1 \leq A_i \leq 10^9
- All input values are integers.

Sample Input 1

9
2 9 9 7 9 2 4 5 8

Sample Output 1

9

Those who satisfy the condition are the persons labeled 4, 7, 8, and 9.
Their integers are 7, 4, 5, and 8, respectively, and the person with the largest integer is the person labeled 9.
Thus, the answer is 9.

Sample Input 2

4
1000000000 1000000000 998244353 998244353

Sample Output 2

-1

If no person satisfies the condition, print -1.
```

**Graded by:** LiveCodeBench executor (atcoder, medium)

## Comparison

| model | reasoning steps | completion tokens | seed |
|---|---|---|---|
| 32B | 168 | 4114 | 1000 |
| 1.5B | 96 | 3169 | 1002 |

## 32B — seed 1000 — 168 steps (4114 tokens)

**Step 1**

Okay, I need to solve this problem. Let's read it carefully.

**Step 2**

So, the problem is about finding a person whose integer is unique among all others. That is, for a person i, none of the other N-1 people have the same integer as A_i. Then, among all such people, I need to find the one with the largest A_i and output their label. If there are no such people, output -1.

**Step 3**

Hmm. So, the steps I need to take are:

**Step 4**

1. Read the input: first N, then the list of A_i's.
2. For each A_i, determine if it's unique in the list.
3. Collect all the indices (labels) where the A_i is unique.
4. If there are none, output -1.
5. Otherwise, among these, find the one with the maximum A_i. Then output their label.

**Step 5**

Wait, but wait. Wait, the condition is that none of the others have the same integer. So for person i, when we check, we have to make sure that A_i occurs exactly once in the entire list. Because if it's present in more than one, then it's not unique.

**Step 6**

So, the approach is:

**Step 7**

- First, count the frequency of each A_i.
- Then, for each person, check if their A_i has a frequency of exactly 1. Those are the candidates.
- Among these candidates, find the maximum A_i, and return the earliest (or correct) label.

**Step 8**

Wait, but the label is the index (but wait, in programming terms, the list is zero-based, but the labels are 1-based). So, for each element, if it's unique, we add its label to a list.

**Step 9**

So, let's think about how to implement this.

**Step 10**

First, I can create a frequency dictionary. For each A_i, count how many times it appears.

**Step 11**

Then, for each index i (starting from 1 to N), check if the frequency of A_i is 1. If so, add the index (i) to a list of candidates.

**Step 12**

If the list is empty, output -1.

**Step 13**

Else, among these candidates, find the one with the maximum A_i. Then output their label.

**Step 14**

Wait, but wait: the maximum A_i among the unique ones. So, for each candidate, we have their A_i, and we need the maximum of those.

**Step 15**

So, how to do this efficiently?

**Step 16**

Let's think about the steps:

**Step 17**

- Read N, then the list A. But since the labels are 1-based, the list is 0-based in Python, but when processing, we'll consider 1-based indices.

**Step 18**

For example, in sample input 1:

**Step 19**

9
2 9 9 7 9 2 4 5 8

**Step 20**

The frequencies:

**Step 21**

2 appears 2 times.
9 appears 3 times.
7 appears once.
4 appears once.
5 appears once.
8 appears once.

**Step 22**

So the unique A_i's are 7,4,5,8. Their positions are 4,7,8,9 (since indexes are 1-based). The maximum among these is 8, so output 9.

**Step 23**

So, the plan is:

**Step 24**

1. Read N and the list A.
2. Create a frequency dictionary using a Counter from collections.
3. Iterate through each element in A, check if its count is 1. Collect the indices (i+1) where this is true.
4. If no such indices, output -1.
5. Else, among the collected indices, find the one with the maximum A_i. Output that index.

**Step 25**

Wait, but when we collect the indices, each of them has a unique A_i, so their A_i's are all unique. So, among them, the maximum is the one with the highest value.

**Step 26**

But to find the maximum, I can iterate through the candidates and track the maximum value and its index.

**Step 27**

Alternatively, since the list of candidates is all the unique ones, I can create a list of tuples (A_i, index) for each candidate, then sort them in descending order of A_i, and pick the first one's index.

**Step 28**

But for large N, like up to 3e5, it's better to process this efficiently.

**Step 29**

So, perhaps, during the iteration, we can keep track of the maximum value and the corresponding index.

**Step 30**

Yes, that's better. So:

**Step 31**

- Initialize max_val to -infinity, and max_index to -1.
- For each candidate in the list of indices (i+1):
   - Get the A_i (since it's unique, and the index is i+1)
   - Compare A_i to max_val. If it's larger, update max_val and max_index.
- At the end, if max_index is still -1, output -1. Else, output max_index.

**Step 32**

Wait, but wait: the list of candidates is the indices where the A_i is unique. So for each candidate index, I can get A_i by A[index-1] (since the list is zero-based in Python).

**Step 33**

So, putting it all together.

**Step 34**

Now, the code steps:

**Step 35**

Read N: n = int(input())

**Step 36**

Read the list A: a = list(map(int, input().split()))

**Step 37**

Create frequency count: from collections import Counter. freq = Counter(a)

**Step 38**

Then, for each index i (0-based), check if freq[a[i]] == 1. If so, add (i+1) to the list of candidates.

**Step 39**

If the list is empty, print -1.

**Step 40**

Else, among the candidates, find the one with the maximum a[i-1].

**Step 41**

Wait, no. Wait, for each candidate, the index is (i+1), so to get the value, it's a[i], since i is 0-based.

**Step 42**

Wait, no. Wait, for i in 0-based, the label is i+1. So for the candidate index (i+1), the value is a[i].

**Step 43**

Wait, no: a[i] is the value for the (i+1)th person. So, for the candidate, the value is a[i], and the label is i+1.

**Step 44**

So, during the iteration over each element, when we find that the frequency is 1, we add (i+1) to the candidates list.

**Step 45**

Once the candidates list is built, we need to find the candidate with the maximum a[i].

**Step 46**

So, for each candidate in the list, the value is a[candidate - 1].

**Step 47**

So, the code could be:

**Step 48**

candidates = []
for i in range(n):
    if freq[a[i]] == 1:
        candidates.append(i+1)

**Step 49**

if not candidates:
    print(-1)
else:
    max_val = -1
    max_idx = -1
    for idx in candidates:
        val = a[idx-1]
        if val > max_val:
            max_val = val
            max_idx = idx
    print(max_idx)

**Step 50**

Wait, but is there a way to do this without building the candidates list?

**Step 51**

Yes, perhaps. We can iterate through each element, and for each, check if its frequency is 1. If so, compare its value to the current maximum.

**Step 52**

So, that would save some space, but for N up to 3e5, it's manageable either way.

**Step 53**

But for the code, perhaps it's more efficient to process in a single pass.

**Step 54**

Wait, but the first approach is to create a frequency counter, then iterate through each element, and for each, check if it's unique.

**Step 55**

But perhaps, for the second part, when we have the list of candidates, we can find the maximum in a single pass.

**Step 56**

But in any case, the approach is manageable.

**Step 57**

Now, let's test the sample inputs.

**Step 58**

Sample Input 1:

**Step 59**

9
2 9 9 7 9 2 4 5 8

**Step 60**

The frequency is:

**Step 61**

2:2, 9:3,7:1,4:1,5:1,8:1.

**Step 62**

So, the candidates are indices where A_i is unique: positions 4,7,8,9 (since 7 is at index 3 (0-based), 4 is at 6, 5 at 7, 8 at 8.

**Step 63**

So the candidates are 4,7,8,9.

**Step 64**

Their values are 7,4,5,8.

**Step 65**

So, the maximum is 8, so output 9.

**Step 66**

Sample Input 2:

**Step 67**

4
1000000000 1000000000 998244353 998244353

**Step 68**

Frequency: 1e9 appears 2 times, 998244353 appears 2 times.

**Step 69**

So, no candidates. Output -1.

**Step 70**

Another test case: N=1. Then, the only person has no others, so it's unique. Output 1.

**Step 71**

Another test case: N=2, A = [5,5]. Both have frequency 2. So output -1.

**Step 72**

Another test case: N=3, A = [3,1,2]. All are unique. So the maximum is 3, at position 1. So output 1.

**Step 73**

Wait, no. Wait, the values are 3,1,2. All are unique. So all are candidates. The maximum is 3, which is at index 1 (label 1). So output 1.

**Step 74**

Wait, but in the code, for each i in 0-based, if freq[a[i]] is 1, then add i+1 to the candidates. So in this case, all a[i] have freq 1. So the candidates are 1,2,3.

**Step 75**

Then, among them, the maximum a[i] is 3, which is at index 0, label 1.

**Step 76**

So code would correctly output 1.

**Step 77**

Another test case: N=5, A = [1,2,3,2,1]. So freq is 1:2, 2:2, 3:1. So the only candidate is 3, which is at position 3 (label 3). So output 3.

**Step 78**

So the code seems to handle these cases.

**Step 79**

Now, about the constraints: N can be up to 3e5. So the solution needs to be O(N) time.

**Step 80**

The frequency counter is O(N), and the candidate collection is O(N), and then the maximum is O(K) where K is the number of candidates, which is up to N. So overall O(N), which is acceptable.

**Step 81**

In Python, for 3e5 elements, this is manageable.

**Step 82**

So, now, the code.

**Step 83**

Wait, but how to handle the case where all A_i are unique?

**Step 84**

Like N=5, A = [5,4,3,2,1]. All are unique. So the maximum is 5, label 1.

**Step 85**

The code will collect all 5 candidates, and then find the maximum among them, which is 5 at index 0, label 1.

**Step 86**

So, correct.

**Step 87**

Now, let's think about the code.

**Step 88**

We can use the Counter from collections.

**Step 89**

But in Python, for large N, using a dictionary is efficient.

**Step 90**

So, the steps:

**Step 91**

Import Counter from collections.

**Step 92**

Read N.

**Step 93**

Read the list A.

**Step 94**

Compute freq = Counter(A).

**Step 95**

Initialize a list of candidates.

**Step 96**

Loop through each index i from 0 to N-1:

**Step 97**

if freq[A[i]] == 1:

**Step 98**

add i+1 to candidates.

**Step 99**

If len(candidates) ==0:

**Step 100**

print -1.

**Step 101**

Else:

**Step 102**

find the candidate with the maximum A[i], and output its label.

**Step 103**

Wait, but in code, for each candidate, the index is i+1, but the value is A[i]. So for each candidate in the list, we can get A[i-1], because the label is i+1, so in the code:

**Step 104**

for idx in candidates:

**Step 105**

val = A[idx - 1]

**Step 106**

But perhaps, it's more efficient to collect the values along with the indices.

**Step 107**

Alternatively, during the initial loop, we can track the maximum and its index.

**Step 108**

Wait, perhaps a better approach is to, during the first loop, for each element, if it's unique, compare its value to the current maximum and update.

**Step 109**

This way, we don't need to store all the candidates. Instead, we just track the maximum value and the earliest (or latest) index where it occurs.

**Step 110**

Wait, but the problem requires the maximum value among all unique elements. So, if multiple unique elements have the same maximum value, we need to choose the one with the smallest index? Or the largest index? Wait, the problem says to print the label of the person whose integer is the largest. So, if two people have the same maximum, but that's impossible because all are unique. Wait, no: because if a value is unique, it's only present once. So, in the candidates, all have unique A_i's. So, the maximum is unique.

**Step 111**

Wait, no. Wait, because for a candidate, their A_i is unique in the entire list. So, no two candidates can have the same A_i. Because if two have the same A_i, then each would have a frequency of 2, and thus they wouldn't be candidates.

**Step 112**

Wait, no. Because if A_i is same for two people, then both have a frequency of 2, so neither is a candidate.

**Step 113**

So, the candidates all have unique A_i's. So, the maximum is unique.

**Step 114**

Therefore, when we collect the candidates, their A_i's are all distinct. So, the maximum is unique.

**Step 115**

So, in the code, we can process each element, and if it's unique, compare its value to the current maximum, and keep track of the maximum value and the corresponding index.

**Step 116**

This would save space, as we don't need to store all the candidates. So, for each element in A:

**Step 117**

if freq[A[i]] == 1:

**Step 118**

if A[i] > current_max:

**Step 119**

current_max = A[i]

**Step 120**

current_max_index = i+1

**Step 121**

So, this approach is better, as it reduces space usage.

**Step 122**

So, the code steps:

**Step 123**

Initialize current_max to -infinity, current_max_index to -1.

**Step 124**

Loop through each index i from 0 to N-1:

**Step 125**

if freq[A[i]] == 1:

**Step 126**

if A[i] > current_max:

**Step 127**

current_max = A[i]

**Step 128**

current_max_index = i+1

**Step 129**

So, after processing all elements:

**Step 130**

if current_max_index is -1, output -1.

**Step 131**

else, output current_max_index.

**Step 132**

Yes, this is more efficient in terms of space, as it doesn't require storing the list of candidates.

**Step 133**

So, for the sample input 1, during the loop:

**Step 134**

i=0, A[i]=2, freq is 2. Not a candidate.

**Step 135**

i=1, A=9, freq 3. Not a candidate.

**Step 136**

i=2, A=9, same.

**Step 137**

i=3, A=7, freq 1. So, current_max is 7, index 4.

**Step 138**

i=4, A=9, same.

**Step 139**

i=5, A=2, same.

**Step 140**

i=6, A=4, freq 1. 4 >7? No.

**Step 141**

i=7, A=5, freq 1. 5>7? No.

**Step 142**

i=8, A=8, freq 1. 8>7? Yes. current_max becomes 8, index 9.

**Step 143**

So, output is 9.

**Step 144**

This works.

**Step 145**

Another test case: all unique. So, the maximum is the largest A_i, and the code correctly picks it.

**Step 146**

Another test case where the maximum is in the middle.

**Step 147**

So, this approach is correct.

**Step 148**

So, the code can be written as:

**Step 149**

import sys
from collections import Counter

**Step 150**

n = int(sys.stdin.readline())
a = list(map(int, sys.stdin.readline().split()))

**Step 151**

freq = Counter(a)

**Step 152**

current_max = -float('inf')
current_max_index = -1

**Step 153**

for i in range(n):
    if freq[a[i]] == 1:
        if a[i] > current_max:
            current_max = a[i]
            current_max_index = i + 1

**Step 154**

if current_max_index == -1:
    print(-1)
else:
    print(current_max_index)

**Step 155**

Wait, but wait: what about when N is 0? But according to constraints, N is at least 1.

**Step 156**

So, no problem.

**Step 157**

Testing sample input 2:

**Step 158**

n=4, a = [1e9, 1e9, 998244353, 998244353]

**Step 159**

freq: 1e9:2, 998244353:2.

**Step 160**

So, no candidates. current_max_index remains -1. So output -1.

**Step 161**

Another test case: n=1, a = [5]. Then, freq is 5:1. So, current_max is 5, index 1. Output 1.

**Step 162**

So, the code seems to handle all cases.

**Step 163**

Now, let's think about the time complexity.

**Step 164**

Counter is O(N).

**Step 165**

Loop is O(N).

**Step 166**

So, total O(N), which is acceptable for N=3e5.

**Step 167**

So, the code should be efficient enough.

**Step 168**

Therefore, the code is correct.

### Final answer (after `</think>`)

```
To solve this problem, we need to identify the person with the unique highest integer among a group of people. Each person has a unique label and an associated integer. The goal is to find the person whose integer is unique and is the highest among all such unique integers.

### Approach
1. **Read Input**: Read the number of people and their respective integers.
2. **Frequency Count**: Use a frequency counter to determine how many times each integer appears.
3. **Identify Unique Integers**: Iterate through each person's integer and check if it appears exactly once (i.e., it is unique).
4. **Track Maximum Unique Integer**: Among the unique integers, track the highest value and the corresponding person's label.
5. **Output Result**: If no unique integers are found, output -1. Otherwise, output the label of the person with the highest unique integer.

### Solution Code
```python
import sys
from collections import Counter

def main():
    n = int(sys.stdin.readline())
    a = list(map(int, sys.stdin.readline().split()))
    
    freq = Counter(a)
    
    current_max = -float('inf')
    current_max_index = -1
    
    for i in range(n):
        if freq[a[i]] == 1:
            if a[i] > current_max:
                current_max = a[i]
                current_max_index = i + 1  # Convert to 1-based index
    
    print(current_max_index if current_max_index != -1 else -1)

if __name__ == "__main__":
    main()
```

### Explanation
1. **Reading Input**: The input is read using `sys.stdin.readline()` for efficiency, especially given the constraints.
2. **Frequency Count**: The `Counter` from the `collections` module is used to count occurrences of each integer.
3. **Identify Unique Integers**: For each integer, if it appears exactly once, it is considered unique. The corresponding person's label is noted.
4. **Track Maximum Unique Integer**: During the iteration, we keep track of the highest unique integer and its label.
5. **Output**: If no unique integers are found, we print -1. Otherwise, we print the label of the person with the highest unique integer.

This approach ensures that we efficiently determine the required result with a time complexity of O(N), making it suitable for large inputs up to 300,000 elements.
```

## 1.5B — seed 1002 — 96 steps (3169 tokens)

**Step 1**

Okay, so I've got this problem to solve. Let's see what it's about. The task is to find a person among N people who has a unique integer, meaning no one else has the same integer. Then, among those who satisfy this condition, find the one with the largest integer. If there are none, output -1.

**Step 2**

Hmm. Let's break this down. First, for each person, we need to check if all other people have different integers. Wait, no. The condition is that none of the other N-1 people have the same integer as themselves. So, for a person to satisfy this condition, their A_i must be unique. Because if any other person has the same A_i, then they don't satisfy the condition.

**Step 3**

So, step one: find all the people whose A_i is unique. Because only those can possibly satisfy the condition. Then, among these, find the one with the largest A_i. If there are none, output -1.

**Step 4**

Wait, but the sample input 1 has 9 people. The A array is 2 9 9 7 9 2 4 5 8. So let's see which are unique.

**Step 5**

Looking at the array:

**Step 6**

Index 0: 2 appears 3 times (indices 0,5,8? Wait no, 2 appears at 0,5,8? Wait 2 is in positions 0,5,8? Let's count:

**Step 7**

A = [2,9,9,7,9,2,4,5,8]

**Step 8**

So A[0] = 2 appears in positions 0,5, etc.? Wait, 2 appears at 0,5, and 0 is index 0, 5 is index 5, and 8 is index 8? Wait no, wait the array is 2,9,9,7,9,2,4,5,8. So 2 appears in positions 0,5, and 8? Wait wait 2 is at 0, then 9 is at 1 and 2, 7 at 3, 9 at 4, 2 at 5, 4 at 6, 5 at 7, 8 at 8. So 2 appears twice (positions 0 and 5), 9 appears three times (positions 1,2,4). 7 appears once. 4,5,8 once each.

**Step 9**

So the unique elements are 7,4,5,8. So for each of them, their A_i is unique. So when we collect all such A_i, we get 7,4,5,8. The maximum among these is 8, which is at index 8 (person 9). So the output is 9.

**Step 10**

So the plan is:

**Step 11**

1. For each A_i, count how many times it appears.
2. Collect all A_i where their count is exactly 1. These are the possible candidates.
3. If there are no such candidates, output -1.
4. Else, find the maximum among them. Then, find the person (index +1) who has this maximum A_i.

**Step 12**

Wait, but how to handle this efficiently, given that N can be up to 3e5? We need an O(N) solution.

**Step 13**

So first, we can count the frequency of each A_i. For each A_i, if the count is 1, then it's a candidate.

**Step 14**

Once we have all the candidates, we need to find the maximum A_i among them and the corresponding index.

**Step 15**

So steps in code:

**Step 16**

- Read N and A array.
- Create a frequency dictionary: count each A_i.
- Collect all A_i where count is 1.
- If the list is empty, output -1.
- Else, find the maximum value in this list.
- Find all indices where A_i is this maximum, pick the one with the highest index, and output that index+1.

**Step 17**

Wait, no. Because the problem says, among the people who satisfy the condition, find the one with the greatest integer. So if multiple have the same maximum, but in the list of unique A_i, but perhaps multiple A_i have the same value. So for example, if two people have A_i=7, but one is unique. Then, the maximum is 7, and we need to find the person with the largest index among those with A_i=7.

**Step 18**

Wait no. Wait, the problem says: "the person with the greatest integer". So if two people have A_i=7, the maximum is 7, and among those, we select the one with the largest index. So the person with the highest label among those with A_i equal to the maximum value.

**Step 19**

Wait, no. Let me read the problem statement again.

**Step 20**

"In the condition, None of the other N-1 people has the same integer as themselves. So, for a person to satisfy, their A_i must be unique. Then, among those, find the one with the greatest integer. If there are multiple, pick the one with the largest index.

**Step 21**

So, for example, if two people have A_i=7, but both are unique, then the maximum is 7, and the person with the largest index (like if one is index 3 and the other is 5, the 5 is chosen).

**Step 22**

So, the steps are:

**Step 23**

- Find all unique A_i (i.e., count is 1).
- If none, output -1.
- Else, among these, find the maximum value.
- Among all A_i equal to this maximum, find the person with the highest index.
- Output that person's label.

**Step 24**

So the code needs to do that.

**Step 25**

So, how to implement this.

**Step 26**

In Python:

**Step 27**

Read N.

**Step 28**

Read A as a list of integers.

**Step 29**

Create a frequency dictionary: using a Counter.

**Step 30**

candidates = [a for a in A if Counter[a] == 1]

**Step 31**

if not candidates:
    print(-1)
else:
    max_a = max(candidates)
    max_indices = [i+1 for i, a in enumerate(A) if a == max_a]
    print(max_indices[-1])

**Step 32**

Wait, but that's not quite right. Because if multiple people have the same max_a, we need to select the one with the highest index. So yes, the list comprehension for max_indices will collect all the indices where A_i is max_a. Then, the last element (since list is in order of increasing indices) is the one with the highest index.

**Step 33**

So this should work.

**Step 34**

Testing on sample input 1:

**Step 35**

A = [2,9,9,7,9,2,4,5,8]

**Step 36**

Candidates are [7,4,5,8]. max is 8. The indices are [8], so output 9.

**Step 37**

Sample input 2:

**Step 38**

A = [1000000000, 1000000000, 998244353, 998244353]

**Step 39**

Candidates are empty, so output -1.

**Step 40**

Another test case: suppose N=3, A = [1,2,3]. Each A_i is unique. So candidates are all three. Max is 3. Output 3.

**Step 41**

Another case: N=4, A = [5,5,3,3]. Candidates are empty, output -1.

**Step 42**

Another case: N=5, A = [3,3,3,3,4]. Candidates are [4]. So output 5.

**Step 43**

Another case: N=6, A = [2,2,3,3,4,4]. Candidates are empty, output -1.

**Step 44**

Another case: N=5, A = [1,2,3,4,5]. Candidates are all. Max is 5, output 5.

**Step 45**

Another case: N=4, A = [1,1,2,3]. Candidates are [1,2,3]. Wait no, wait 2 and 3 are unique. So candidates are [1,2,3]. Max is 3. So output is 4.

**Step 46**

Wait, no. Because the candidates are [1,2,3], their max is 3. So the person with A_i=3 is index 3, output 4.

**Step 47**

Wait, but in the list of candidates, the person with A_i=3 is at index 3, which is the fourth person. So that's correct.

**Step 48**

So the code seems correct.

**Step 49**

Now, the problem is to implement this efficiently.

**Step 50**

But for N up to 3e5, using Counter is feasible. The steps are O(N), which is acceptable.

**Step 51**

So the code should read N, read A as a list, count frequencies, collect candidates, check if any, and then proceed.

**Step 52**

So in Python:

**Step 53**

Read N.

**Step 54**

A = list of integers.

**Step 55**

from collections import Counter.

**Step 56**

Then:

**Step 57**

freq = Counter(A)

**Step 58**

candidates = [a for a in freq if freq[a] == 1]

**Step 59**

if not candidates:
    print(-1)
else:
    max_a = max(candidates)
    # find the indices where A[i] == max_a, and pick the highest index.
    max_indices = [i+1 for i, a in enumerate(A) if a == max_a]
    print(max(max_indices))

**Step 60**

Wait, but wait: in the candidates list, we can also collect all the A_i's, but perhaps that's not needed.

**Step 61**

Alternatively, perhaps it's better to collect the unique A_i's in a list, and then process.

**Step 62**

But the approach is correct.

**Step 63**

Wait, but in the code, the list comprehension [a for a in A if freq[a] == 1] will give all A_i's that are unique.

**Step 64**

But wait, if two people have the same A_i, they are not unique. So, in the candidates, it's only when the count is 1.

**Step 65**

Yes.

**Step 66**

So that's correct.

**Step 67**

Now, what about the sample input 2:

**Step 68**

A = [1000000000, 1000000000, 998244353, 998244353]

**Step 69**

freq is {1000000000:2, 998244353:2}

**Step 70**

candidates is empty, so output -1.

**Step 71**

Yes.

**Step 72**

Another test case: N=5, A = [5,5,5,5,6]. Then candidates are [6], so output 5.

**Step 73**

Another test case: N=6, A = [1,2,1,3,4,5]. Candidates are [2,3,4,5]. Max is 5, so output 6.

**Step 74**

Yes.

**Step 75**

So the code seems to handle all cases.

**Step 76**

Now, considering the constraints, N up to 3e5 is manageable.

**Step 77**

But wait, in Python, the list comprehensions are okay. Because for 3e5 elements, it's manageable.

**Step 78**

So, the code should be:

**Step 79**

Read N.

**Step 80**

Read A as list of integers.

**Step 81**

Compute freq = Counter(A).

**Step 82**

candidates = [a for a in A if freq[a] == 1]

**Step 83**

if not candidates:
    print(-1)
else:
    max_a = max(candidates)
    max_indices = [i+1 for i, a in enumerate(A) if a == max_a]
    print(max(max_indices))

**Step 84**

Wait, but wait, in the else part, after finding max_a, the code is creating a list of all indices where A[i] is max_a, then taking the maximum of that list. That is correct.

**Step 85**

Yes.

**Step 86**

So, the code should handle all cases.

**Step 87**

Let me think about possible edge cases.

**Step 88**

Case where N=1: A = [5]. Then, the candidate is [5], so output 1.

**Step 89**

Case where N=2: A = [1,1]. Then, no candidates, output -1.

**Step 90**

Case where N=3: A = [1,2,3]. Then, output 3.

**Step 91**

Another case where multiple max_a and same max_a: N=5, A = [3,3,4,4,5]. Then, candidates are [3,4,5], but no. Wait, 3 appears twice, 4 appears twice, 5 once. So candidates are [5]. So output 5.

**Step 92**

Wait, no. Wait, 5 is in the list, but the candidates are [5], so output 5.

**Step 93**

Wait, another case: A = [1,2,2,3,3]. Then, the unique elements are 1,3. So candidates are [1,3], max is 3. So output 5.

**Step 94**

Yes.

**Step 95**

So, the code seems correct.

**Step 96**

I think that's the correct approach.

### Final answer (after `</think>`)

```
To solve this problem, we need to identify a person among N people whose integer is unique and then find the person with the greatest integer among those who satisfy the condition. If no such person exists, we should return -1.

### Approach
1. **Read Input:** Read the number of people, N, and their respective integers.
2. **Count Frequencies:** Use a frequency counter to determine how many times each integer appears.
3. **Identify Candidates:** Collect all integers that appear exactly once (i.e., unique integers).
4. **Check for Valid Candidates:** If there are no valid candidates, output -1.
5. **Find Maximum Integer:** If there are valid candidates, determine the maximum integer among them.
6. **Determine the Person:** Identify the person with the highest label (index + 1) who has this maximum integer.

### Solution Code
```python
from collections import Counter

def main():
    import sys
    input = sys.stdin.read().split()
    N = int(input[0])
    A = list(map(int, input[1:N+1]))
    
    freq = Counter(A)
    candidates = [a for a in A if freq[a] == 1]
    
    if not candidates:
        print(-1)
        return
    
    max_a = max(candidates)
    max_indices = [i + 1 for i, a in enumerate(A) if a == max_a]
    print(max(max_indices))

if __name__ == "__main__":
    main()
```

### Explanation
1. **Reading Input:** The input is read and parsed into an integer N and a list of integers A.
2. **Frequency Counting:** Using `Counter` from the `collections` module, we count the frequency of each integer in A.
3. **Candidate Identification:** We filter out integers that appear exactly once to form the list of candidates.
4. **Validation:** If the list of candidates is empty, it means no person has a unique integer, so we print -1.
5. **Finding Maximum Integer:** Among the candidates, we find the maximum integer value.
6. **Identifying the Person:** We then find the highest index (label) among those with the maximum integer and print it.

This approach ensures that we efficiently determine the required person using frequency counting and list comprehensions, making it suitable for large input sizes up to 300,000.
```
