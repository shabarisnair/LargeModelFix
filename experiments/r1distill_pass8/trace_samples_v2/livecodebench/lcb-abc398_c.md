# livecodebench — `lcb-abc398_c` (prompt v2)

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

## 32B — seed 1000 — 101 steps, 1968 tokens — correct: True

**Answer section is exactly the final answer:** `False`

<details><summary>v1 answer section (old prompt) — for contrast</summary>

```
To solve this problem, we need to identify the person with the unique highest integer among a group of people, where each person's integer is unique across the group. If no such person exists, we should return -1.

### Approach
1. **Read Input**: First, read the number of people and their respective integers.
2. **Frequency Count**: Use a dictionary to count the frequency of each integer.
3. **Identify Candidates**: Collect all people whose integer appears exactly once in the list.
4. **Determine Result**: If there are no candidates, output -1. Otherwise, find the candidate with the highest integer and output their label.

### Solution Code
```python
n = int(input())
a = list(map(int, input().split()))
freq = {}

for num in a:
    if num in freq:
        freq[num] += 1
    else:
        freq[num] = 1

candidates = []
for idx, num in enumerate(a):
    if freq[num] == 1:
        candidates.append((num, idx + 1))

if not candidates:
    print(-1)
else:
    max_candidate = max(candidates, key=lambda x: x[0])
    print(max_candidate[1])
```

### Explanation
1. **Reading Input**: The input is read and parsed into a list of integers.
2. **Frequency Dictionary**: We use a dictionary to count how many times each integer appears.
3. **Collecting Candidates**: For each person, if their integer appears exactly once, they are added to the list of candidates.
4. **Finding the Result**: If there are no candidates, we print -1. Otherwise, we find the candidate with the highest integer and pr
```

</details>

### v2 answer section (after `</think>`)

```
To solve this problem, we need to identify the person with the unique highest integer value among a group of people. If no such person exists, we should return -1.

### Approach
1. **Read Input**: Read the number of people, N, and their respective integers.
2. **Frequency Counting**: Use a dictionary to count the frequency of each integer. This helps us quickly determine which integers are unique.
3. **Identify Candidates**: Collect all people whose integer appears exactly once (i.e., unique integers).
4. **Determine the Result**: If there are no unique integers, return -1. Otherwise, find the person with the highest unique integer and return their label.

### Solution Code
```python
from collections import Counter

n = int(input())
a = list(map(int, input().split()))
freq = Counter(a)

candidates = []
for idx in range(n):
    val = a[idx]
    if freq[val] == 1:
        candidates.append((val, idx + 1))

if not candidates:
    print(-1)
else:
    max_val = -1
    max_idx = -1
    for val, idx in candidates:
        if val > max_val:
            max_val = val
            max_idx = idx
    print(max_idx)
```

### Explanation
1. **Reading Input**: We read the input values which include the number of people and their respective integers.
2. **Frequency Counting**: Using the `Counter` from the `collections` module, we count how many times each integer appears. This helps us identify which integers are unique.
3. **Identifying Candidates**: We iterate through the list of integers and collect those that appear exactly once along with their respective indices (converted to 1-based labels).
4. **Finding the Result**: If no unique integers are found, we print -1. Otherwise, we determine the person with the highest unique integer by iterating through the candidates and tracking the maximum value and its corresponding index.

This approach ensures that we efficiently handle the problem within the constraints, providing an optimal solution.
```

### Reasoning steps

**Step 1**

Okay, I need to solve this problem. Let's read it carefully.

**Step 2**

So, the problem is about finding a person whose integer is unique among all others. More precisely, for each person, we check if none of the other N-1 people have the same integer. Among those who satisfy this condition, we need to find the one with the largest integer and output their label. If no one satisfies the condition, we output -1.

**Step 3**

Hmm. So first, I need to process the list of integers and find all the people who have a unique value. Then, among those, pick the one with the maximum value.

**Step 4**

Let me think about how to approach this.

**Step 5**

First, I should count the frequency of each integer. Because if an integer appears only once, then the person with that integer is a candidate. So, the plan is:

**Step 6**

1. Count the frequency of each A_i.
2. For each person, check if their A_i has a frequency of 1.
3. Collect all such persons and their A_i.
4. If the collected list is empty, output -1.
5. Otherwise, find the person with the maximum A_i in this list and output their label.

**Step 7**

Wait, but the labels are from 1 to N, right? So, the person's label is their index in the input plus one (since input is 0-based in the array, but labels are 1-based).

**Step 8**

So, let's outline the steps more concretely.

**Step 9**

First, read N and the list A.

**Step 10**

Then, create a frequency dictionary. For each value in A, count how many times it occurs.

**Step 11**

Then, iterate through each element in A along with their index (starting from 1). For each element, if its frequency is 1, then add this element and its index to a list of candidates.

**Step 12**

After collecting all candidates, if the list is empty, output -1.

**Step 13**

Otherwise, among the candidates, find the one with the maximum A_i. If there are multiple, since all have unique A_i, the maximum is unique. Then, output the index of that element.

**Step 14**

Wait, but what if multiple candidates have the same maximum? Well, since all candidates have unique A_i, there can be only one maximum, right? So, that's not a problem.

**Step 15**

Let's think about the sample input 1:

**Step 16**

9
2 9 9 7 9 2 4 5 8

**Step 17**

The frequencies are:
2:2
9:3
7:1
4:1
5:1
8:1

**Step 18**

So, the candidates are the elements with 7,4,5,8. Their indices are 4,7,8,9. The max among their A_i is 8, so output 9.

**Step 19**

Sample input 2:

**Step 20**

4
1000000000 1000000000 998244353 998244353

**Step 21**

All have frequencies of 2 or more, so no candidates. Output -1.

**Step 22**

So, the approach seems solid.

**Step 23**

Now, in Python, how to implement this efficiently?

**Step 24**

Given that N can be up to 3e5, we need an O(N) solution.

**Step 25**

Using a dictionary to count frequencies is O(N), which is acceptable.

**Step 26**

Then, iterating through each element to collect candidates is O(N), and then finding the maximum is O(M), where M is the number of candidates, which is also acceptable.

**Step 27**

So, steps in code:

**Step 28**

Read N.

**Step 29**

Read the list A.

**Step 30**

Create a frequency dictionary, perhaps using collections.Counter.

**Step 31**

Then, for each index i (from 1 to N), check if A[i-1] has a count of 1.

**Step 32**

Collect all such (value, index) pairs.

**Step 33**

If no such pairs, print -1.

**Step 34**

Else, find the pair with the maximum value, and print its index.

**Step 35**

Wait, but in Python, the Counter will handle the frequencies correctly.

**Step 36**

Wait, in the code:

**Step 37**

A = list of integers.

**Step 38**

freq = Counter(A)

**Step 39**

Then, for each i in 0..N-1:

**Step 40**

if freq[A[i]] == 1:

**Step 41**

add (A[i], i+1) to candidates.

**Step 42**

Yes.

**Step 43**

Then, if len(candidates) == 0: print -1.

**Step 44**

Else, find the candidate with the maximum A_i, and output its index.

**Step 45**

So, how to find the max? We can sort the candidates by value in descending order and pick the first, or iterate through and keep track of the max.

**Step 46**

Probably, the latter is more efficient.

**Step 47**

Initialize max_val to -infinity, and max_index to -1.

**Step 48**

Loop through each (val, idx) in candidates:

**Step 49**

if val > max_val:

**Step 50**

max_val = val

**Step 51**

max_index = idx

**Step 52**

So, the code structure is clear.

**Step 53**

Now, let's think about possible edge cases.

**Step 54**

Case 1: N=1.

**Step 55**

Then, the person is the only one, so their frequency is 1. So, output 1.

**Step 56**

Case 2: All elements are unique.

**Step 57**

Then, all are candidates. We need to find the one with the maximum A_i.

**Step 58**

Case 3: Only one element is unique.

**Step 59**

Case 4: All elements are same except one.

**Step 60**

Yes, the code should handle all these.

**Step 61**

Another edge case: when all elements have frequency 2, except none. Then, output -1.

**Step 62**

Another case: when some elements have frequency 1, but their values are lower than others. So, the max is among the candidates.

**Step 63**

So, the code should handle all.

**Step 64**

Now, let's write the code.

**Step 65**

Read N:

**Step 66**

n = int(input())

**Step 67**

Then read the list:

**Step 68**

a = list(map(int, input().split()))

**Step 69**

Then, count frequencies.

**Step 70**

from collections import Counter

**Step 71**

freq = Counter(a)

**Step 72**

Then, collect the candidates.

**Step 73**

candidates = []

**Step 74**

for idx in range(n):

**Step 75**

val = a[idx]

**Step 76**

if freq[val] == 1:

**Step 77**

candidates.append( (val, idx+1) )

**Step 78**

Then, if no candidates:

**Step 79**

if not candidates:

**Step 80**

print(-1)

**Step 81**

else:

**Step 82**

find the maximum.

**Step 83**

max_val = -1

**Step 84**

max_idx = -1

**Step 85**

for val, idx in candidates:

**Step 86**

if val > max_val:

**Step 87**

max_val = val

**Step 88**

max_idx = idx

**Step 89**

print(max_idx)

**Step 90**

Wait, but what about the initial value for max_val? Because the A_i can be up to 1e9, but if we set max_val to -1, what if all the candidates have negative numbers?

**Step 91**

Wait, no. Because the problem says A_i >=1? Wait, looking back: the constraints say 1<=A_i<=1e9. So, A_i is at least 1. So, initializing max_val to -1 is safe because all candidates have values >=1.

**Step 92**

Yes.

**Step 93**

So, the code is correct.

**Step 94**

Testing sample input 1:

**Step 95**

The code would collect the 4th,7th,8th,9th elements as candidates. Then, the max is 8, so idx 9.

**Step 96**

Sample input 2: no candidates, output -1.

**Step 97**

Another test case: N=1, A=[5]. Output 1.

**Step 98**

Another test case: N=2, A=[3,3]. Output -1.

**Step 99**

Another test case: N=3, A=[5,5,4]. Candidates are [4], so output 3.

**Step 100**

Yes.

**Step 101**

So, the code should handle all cases.

## 1.5B — seed 1001 — 156 steps, 4339 tokens — correct: True

**Answer section is exactly the final answer:** `False`

<details><summary>v1 answer section (old prompt) — for contrast</summary>

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
2. **Frequency Counting:** Using `Counter` from the `collections` module, we coun
```

</details>

### v2 answer section (after `</think>`)

```
To solve this problem, we need to identify the person(s) among N people who satisfy the condition that none of the other N-1 people has the same integer as themselves. If no such person exists, we should report -1. Otherwise, we report the label of the person with the largest integer.

### Approach
1. **Read Input**: Read the number of people, N, and their respective integers.
2. **Frequency Map**: Create a frequency map to count occurrences of each integer.
3. **Identify Unique Integers**: Collect all integers that appear exactly once. These are the only integers that can satisfy the condition.
4. **Check for Valid People**: If there are no unique integers, output -1. Otherwise, find the maximum integer among these unique integers.
5. **Find the Person**: Determine the first occurrence (smallest index) of this maximum integer in the array and output its label.

### Solution Code
```python
n = int(input())
A = list(map(int, input().split()))

freq = {}
for a in A:
    if a in freq:
        freq[a] += 1
    else:
        freq[a] = 1

unique_a = [a for a in freq if freq[a] == 1]

if not unique_a:
    print(-1)
else:
    max_a = max(unique_a)
    for i, a in enumerate(A):
        if a == max_a:
            print(i + 1)
            exit()
```

### Explanation
1. **Reading Input**: The input is read and parsed into an integer list `A`.
2. **Frequency Map**: A dictionary `freq` is used to count how many times each integer appears in the list.
3. **Unique Integers**: The list `unique_a` contains all integers that appear exactly once, which are the only candidates to satisfy the condition.
4. **Check for Valid People**: If `unique_a` is empty, it means no integer appears exactly once, so we output -1. Otherwise, we find the maximum integer in `unique_a`.
5. **Finding the Person**: The first occurrence of the maximum integer in the list `A` is found using a loop, and its label (index + 1) is printed.

This approach ensures that we efficiently determine the required person or
```

### Reasoning steps

**Step 1**

Okay, I have this problem to solve. Let's read it carefully.

**Step 2**

So, the problem is about N people each having an integer A_i. We need to find among them the person(s) who satisfy a certain condition. The condition is that none of the other N-1 people has the same integer as themselves. So, for a person i, all other A_j (j != i) must be different from A_i. Then, among all such persons, we need to find the one with the largest integer. If there are none, we output -1.

**Step 3**

Hmm, let's break this down.

**Step 4**

First, I need to identify all the people who satisfy the condition. For a person to satisfy this, their A_i must be unique. Because if another person has the same A_i, then that person would not satisfy the condition.

**Step 5**

So, step one is to find all the people whose A_i is unique in the array. Because if a person has duplicates in the array, then they don't satisfy the condition.

**Step 6**

Wait, no. Wait, no. Let me think again. The condition is that none of the other N-1 people has the same integer as themselves. So for person i, all A_j for j != i must not equal A_i. So, A_i must not appear more than once in the array except for itself.

**Step 7**

Wait, no. Because if A_i appears exactly once in the array, then yes, no other j can have A_j = A_i. So, each such person i must have a unique A_i.

**Step 8**

Wait, no, no. Wait, suppose the array is [2,9,9,7]. Then, the person with A_i=9 has another 9, so they don't satisfy the condition. So, in the first sample input, the valid people are those with unique A_i.

**Step 9**

Wait, no. Let's see sample input 1:

**Step 10**

9
2 9 9 7 9 2 4 5 8

**Step 11**

So the array is [2,9,9,7,9,2,4,5,8]. So, for each element:

**Step 12**

- 2 appears at positions 1 and 6, so there are duplicates.
- 9 appears multiple times.
- 7 once.
- 4 once.
- 5 once.
- 8 once.

**Step 13**

So the valid people are those with A_i that are unique. So, the A_i's are 2,9,7,9,9,2,4,5,8. So the unique A_i's are 7,4,5,8.

**Step 14**

Wait, but wait. Let's think again: for a person to satisfy the condition, all other N-1 people must not have the same integer as themselves. So, if a person's A_i is unique, then yes. But what if another person's A_i is same as this one? Then, that person would have duplicates, so they don't satisfy the condition.

**Step 15**

Wait, no. Wait, for a person i, for all j != i, A_j != A_i. So, if in the array, A_i appears exactly once, then yes. Because all other elements are different. So, for example, if the array is [3,1,2,3], then the first 3 is unique, so it's valid. The other 3 is not, because there's another 3.

**Step 16**

So, the first step is to find all elements that are unique. So, we can create a frequency map of the A_i's, and collect all elements with frequency 1.

**Step 17**

Once we have that list of unique elements, we can then check for each of them whether they appear exactly once in the array.

**Step 18**

Wait, no. Because for a person to be valid, all other elements must not be equal to their own. So, if the array has multiple elements equal to A_i, then that A_i is invalid. So, the unique elements are those that appear exactly once in the array. So, the set of valid persons is those whose A_i is unique in the array.

**Step 19**

So, the first step is to find all elements that occur exactly once.

**Step 20**

Once we have this list, if it's empty, we output -1. Otherwise, among these, we need to find the one with the largest A_i.

**Step 21**

So, the plan is:

**Step 22**

1. Read N and the array A.

**Step 23**

2. Create a frequency dictionary for A.

**Step 24**

3. Collect all keys (A_i) that have a frequency of 1.

**Step 25**

4. If this collection is empty, output -1.

**Step 26**

5. Else, among these keys, find the maximum value.

**Step 27**

6. Output the maximum value's corresponding index.

**Step 28**

Wait, wait. No. Wait, the output is the person's label. So, for the elements in the collected set, which are the A_i's that are unique, each has a label (from 1 to N). So, we need to find the maximum A_i among these unique elements, then find the person with that A_i.

**Step 29**

Wait, but the problem says, for the persons who satisfy the condition, output the person's label. So, for example, in sample input 1, the valid persons are those with A_i=7,4,5,8. Among these, 8 is the maximum, so the output is 9.

**Step 30**

So, the steps are:

**Step 31**

- Find all unique elements (those with frequency 1).

**Step 32**

- Among them, find the maximum A_i.

**Step 33**

- Then, find the person's label with that A_i.

**Step 34**

But wait, the maximum A_i is the maximum in the unique set, but the person's label is just the position in the array.

**Step 35**

So, for example, in sample input 1, the unique elements are 7,4,5,8. So the maximum is 8, which is in position 9. So output 9.

**Step 36**

But wait, in the array, the person with A_i=8 is at index 8 (0-based) or 9 (1-based). So, the output is the label, which is 9.

**Step 37**

So, the approach is:

**Step 38**

- For each unique element, note its position.

**Step 39**

- Then, among these, find the one with the maximum A_i.

**Step 40**

- Then, output that position.

**Step 41**

Wait, but the problem says to output the person's label. So, the position is 1-based.

**Step 42**

So, how to proceed:

**Step 43**

We can create a dictionary that maps each A_i to its count. Then, collect all A_i with count 1. Then, for each such A_i, we can track their positions.

**Step 44**

Wait, but for each A_i, we can have multiple positions. But in the problem, each person has a unique label, so each A_i is unique per label.

**Step 45**

Wait, no. Because in the array, the same A_i can appear multiple times, but for the condition, the person is only valid if their A_i is unique, i.e., occurs exactly once.

**Step 46**

So, for example, if the array is [5,5,3], then 5 occurs twice, so the person with A_i=5 is invalid. The person with A_i=3 occurs once, so they are valid. So, their label is 3.

**Step 47**

So, the steps are:

**Step 48**

1. Read N and the array A.

**Step 49**

2. Create a frequency dictionary, say freq, where freq[A_i] is the count.

**Step 50**

3. Collect all A_i where freq[A_i] == 1. Let's call this list unique_A.

**Step 51**

4. If len(unique_A) == 0, output -1.

**Step 52**

5. Else, find the maximum value in unique_A.

**Step 53**

6. Find the label (i+1, since labels are 1-based) of the first occurrence of this maximum A_i.

**Step 54**

Wait, no. Because the maximum could be any of the unique_A elements. So, for all elements in unique_A, we need to find which one is the largest, and then find the position of the first occurrence of that value in the array.

**Step 55**

Wait, no. Because the array may have multiple occurrences of the maximum value. For example, in the array [3, 3, 3, 5, 5], the unique_A is [3,5]. The maximum is 5, and the position is 5.

**Step 56**

So, the steps are:

**Step 57**

- For each element in unique_A, find the maximum.

**Step 58**

- Then, find the label of the person with that A_i.

**Step 59**

So, the plan is:

**Step 60**

- Create a frequency map.

**Step 61**

- Collect unique elements (those with frequency 1).

**Step 62**

- If no unique elements, output -1.

**Step 63**

- Else, find the maximum value in unique_A.

**Step 64**

- Find the first occurrence (or any occurrence) of this maximum value in the array, and output its label.

**Step 65**

Wait, no. Because the array may have multiple occurrences of the maximum, but only one is valid, because only one person can have the maximum A_i. Wait, no, the maximum A_i can appear multiple times. Wait, no, because in the unique_A list, all elements are unique. So, the maximum in unique_A is the maximum A_i, and since unique_A has all A_i with frequency 1, there's only one person with that maximum A_i. So, the label is the position of the first occurrence of that A_i.

**Step 66**

Wait, no. Because the maximum may not be present in unique_A. Wait, no. Because unique_A is the list of elements that have frequency 1. So, the maximum of unique_A is the maximum A_i among all unique elements.

**Step 67**

So, in the array, there exists exactly one person with that maximum A_i, because the maximum is in unique_A.

**Step 68**

Wait, no. For example, consider the array [5, 3, 5]. The unique elements are [3,5]. So, the maximum is 5. In the array, 5 occurs at positions 0 and 2. So, the first occurrence is 0, which is label 1.

**Step 69**

So, in the code, for the maximum value in unique_A, find the first occurrence in the array, and output its label.

**Step 70**

But how do we do that?

**Step 71**

Wait, perhaps we can create a dictionary that maps each A_i to its list of positions.

**Step 72**

For example, for each A_i in the array, we can have a list of indices where it appears.

**Step 73**

Then, for the maximum A_i, we can look up its list of indices, pick the first one, and output that index +1.

**Step 74**

So, the steps are:

**Step 75**

1. Read N and the array A.

**Step 76**

2. Create a frequency dictionary: freq = {}
   for a in A:
       if a in freq:
           freq[a] +=1
       else:
           freq[a] = 1

**Step 77**

3. Collect unique_A: [a for a in freq if freq[a] == 1]

**Step 78**

4. If len(unique_A) == 0: output -1.

**Step 79**

5. Else, find the maximum in unique_A: max_a = max(unique_A)

**Step 80**

6. For each a in unique_A, find its first occurrence in the array.

**Step 81**

Wait, but for step 5, unique_A contains all a's with freq 1. So, the maximum is the largest a in unique_A.

**Step 82**

So, for that a, find the first occurrence in the array.

**Step 83**

So, for a given a, the first occurrence is the smallest index in A where A[i] == a.

**Step 84**

So, how to find the first occurrence.

**Step 85**

One approach is to precompute for each a in unique_A, the list of indices where it appears, and then pick the first one.

**Step 86**

So:

**Step 87**

a_dict = defaultdict(list)
   for idx, a in enumerate(A):
       a_dict[a].append(idx)
   Then, for each a in unique_A, the first occurrence is a_dict[a][0]

**Step 88**

But since unique_A is sorted in ascending order, the first a in unique_A is the smallest, so the first occurrence of that a is the earliest in the array.

**Step 89**

But wait, what if a in unique_A is in the middle of the array, but another a in unique_A is larger and occurs earlier?

**Step 90**

No, because unique_A is the list of a's with frequency 1, but in the array, the a's with frequency 1 may be in any order.

**Step 91**

But the maximum a is the largest in unique_A, so the earliest occurrence of that a in the array is the correct one.

**Step 92**

Wait, no. For example, suppose unique_A is [5,3,4], and the array is [3,5,4]. The maximum is 5. The first occurrence of 5 is at index 1, which is the correct person.

**Step 93**

Another example: unique_A is [3,5], and the array is [5,3]. The maximum is 5. The first occurrence is index 0, which is correct.

**Step 94**

So, the correct approach is to find the maximum a in unique_A, and then find the first occurrence of that a in the array.

**Step 95**

So, code steps:

**Step 96**

- Create a frequency map.

**Step 97**

- Create a list of unique a's.

**Step 98**

- If no unique a's, output -1.

**Step 99**

- Else, find the maximum a.

**Step 100**

- Find the first occurrence of this a in the array.

**Step 101**

- Output that index +1.

**Step 102**

So, the code outline is:

**Step 103**

Read N.

**Step 104**

Read A as a list.

**Step 105**

freq = {}
for a in A:
    if a in freq:
        freq[a] +=1
    else:
        freq[a] =1

**Step 106**

unique_a = [a for a in freq if freq[a] == 1]

**Step 107**

if not unique_a:
    print(-1)
else:
    max_a = max(unique_a)
    # find the first occurrence of max_a in A
    for i, a in enumerate(A):
        if a == max_a:
            print(i+1)
            exit()
    # should not reach here because unique_a is not empty
    # but for safety, perhaps find the first occurrence
    # perhaps use list comprehensions or the index method.

**Step 108**

Wait, but for the case where the max_a is not present in the array? No, because unique_a contains all a's with freq 1, which are all elements in A. So, the max_a must be in A.

**Step 109**

So, code can proceed.

**Step 110**

Testing the sample input 1:

**Step 111**

A = [2,9,9,7,9,2,4,5,8]

**Step 112**

freq: 2:2, 9:3, 7:1,4:1,5:1,8:1

**Step 113**

unique_a is [7,4,5,8]

**Step 114**

max_a is 8.

**Step 115**

Find the first occurrence of 8 in A: at index 8, so output 9.

**Step 116**

Sample input 2:

**Step 117**

4

**Step 118**

1000000000 1000000000 998244353 998244353

**Step 119**

freq: 1e9:2, 998244353:2

**Step 120**

unique_a is empty. So, output -1.

**Step 121**

Another test case: N=5, A=[1,2,3,4,5]. unique_a is all 5 elements. max_a is 5. First occurrence is 5, output 5.

**Step 122**

Another test case: N=3, A=[5,5,5]. unique_a is empty, output -1.

**Step 123**

Another test case: N=3, A=[3,4,3]. unique_a is [4]. So, output 2.

**Step 124**

So, the code seems to handle these cases.

**Step 125**

Now, for the implementation.

**Step 126**

But considering N can be up to 3e5, we need to make the code efficient.

**Step 127**

The steps are:

**Step 128**

- Read N.

**Step 129**

- Read the array as a list of integers.

**Step 130**

- Compute the frequency map. Using a dictionary.

**Step 131**

- Collect the unique_a.

**Step 132**

- If no unique_a, output -1.

**Step 133**

- Else, find the max_a in unique_a.

**Step 134**

- Iterate through the array to find the first occurrence of max_a, and output its index+1.

**Step 135**

In Python, to find the first occurrence, we can loop through the array, and for each a, if a == max_a, return the index+1.

**Step 136**

But for N up to 3e5, this is acceptable.

**Step 137**

So, the code in Python would be something like:

**Step 138**

n = int(input())
A = list(map(int, input().split()))
freq = {}
for a in A:
    if a in freq:
        freq[a] +=1
    else:
        freq[a] =1

**Step 139**

unique_a = [a for a in freq if freq[a] ==1]
if not unique_a:
    print(-1)
else:
    max_a = max(unique_a)
    for i, a in enumerate(A):
        if a == max_a:
            print(i+1)
            exit()

**Step 140**

This should work.

**Step 141**

Testing the sample input 1:

**Step 142**

n=9, A = [2,9,9,7,9,2,4,5,8]

**Step 143**

freq: 2:2,9:3,7:1,4:1,5:1,8:1

**Step 144**

unique_a is [7,4,5,8]

**Step 145**

max_a is 8.

**Step 146**

Loop through A:

**Step 147**

At i=8, a=8 is found. Output 9.

**Step 148**

Sample input 2: no unique_a, output -1.

**Step 149**

Another test case: N=5, A = [3,4,5,6,7]. unique_a is [3,4,5,6,7]. max_a is 7. Output is 5.

**Step 150**

Another test case: N=3, A = [5,5,5]. unique_a is empty, output -1.

**Step 151**

Another test case: N=3, A = [5,5,3]. unique_a is [5,3]. max_a is 5. The first occurrence is index 0, output 1.

**Step 152**

So, the code should handle all these cases.

**Step 153**

But wait, in the code, for the loop, it's possible that the for loop could be replaced by a list comprehension or a generator expression, but for the sake of code readability, perhaps it's better to write it as:

**Step 154**

for i, a in enumerate(A):
    if a == max_a:
        print(i+1)
        exit()

**Step 155**

Which is straightforward.

**Step 156**

So, the code should be correct.
