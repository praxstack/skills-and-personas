# ☕ Java Quick Reference for CodeCrafters & DSA

A concise reference for Java constructs you'll encounter while building projects and solving problems. **Not a tutorial** — use this when you hit a gap.

---

## 📦 Collections Framework

### Core Interfaces Hierarchy
```
Collection
├── List (ordered, duplicates allowed)
│   ├── ArrayList  — O(1) access, O(n) insert middle
│   ├── LinkedList — O(n) access, O(1) insert if at position
│   └── Stack      — LIFO (use Deque instead)
│
├── Set (no duplicates)
│   ├── HashSet       — O(1) operations, no order
│   ├── LinkedHashSet — O(1) operations, insertion order
│   └── TreeSet       — O(log n) operations, sorted order
│
├── Queue (FIFO)
│   ├── LinkedList    — Queue implementation
│   ├── PriorityQueue — Heap-based, O(log n) poll/offer
│   └── ArrayDeque    — Double-ended, faster than LinkedList
│
└── Deque (double-ended)
    └── ArrayDeque — Use for Stack AND Queue

Map (key-value pairs)
├── HashMap       — O(1) operations, no order
├── LinkedHashMap — O(1) operations, insertion order
├── TreeMap       — O(log n) operations, sorted by key
└── ConcurrentHashMap — Thread-safe
```

### Essential Operations Cheatsheet

```java
// === LIST ===
List<Integer> list = new ArrayList<>();
list.add(1);                    // Append
list.add(0, 99);                // Insert at index
list.get(0);                    // Access by index
list.set(0, 100);               // Replace at index
list.remove(0);                 // Remove by index
list.remove(Integer.valueOf(1)); // Remove by value
list.contains(1);               // Check existence
list.size();                    // Length
list.isEmpty();                 // Empty check
Collections.sort(list);         // Sort ascending
Collections.reverse(list);      // Reverse

// === SET ===
Set<String> set = new HashSet<>();
set.add("a");                   // Add (returns false if exists)
set.remove("a");                // Remove
set.contains("a");              // Check existence

// === MAP ===
Map<String, Integer> map = new HashMap<>();
map.put("key", 1);              // Insert/update
map.get("key");                 // Get (null if missing)
map.getOrDefault("key", 0);     // Get with default
map.containsKey("key");         // Check key exists
map.containsValue(1);           // Check value exists
map.remove("key");              // Remove
map.keySet();                   // All keys
map.values();                   // All values
map.entrySet();                 // Key-value pairs

// Iterate map
for (Map.Entry<String, Integer> entry : map.entrySet()) {
    String key = entry.getKey();
    Integer value = entry.getValue();
}

// === QUEUE ===
Queue<Integer> queue = new LinkedList<>();
queue.offer(1);                 // Enqueue (add to tail)
queue.poll();                   // Dequeue (remove from head, null if empty)
queue.peek();                   // View head (null if empty)

// === STACK (use Deque) ===
Deque<Integer> stack = new ArrayDeque<>();
stack.push(1);                  // Push
stack.pop();                    // Pop (throws if empty)
stack.peek();                   // View top

// === PRIORITY QUEUE (Min-Heap by default) ===
PriorityQueue<Integer> minHeap = new PriorityQueue<>();
PriorityQueue<Integer> maxHeap = new PriorityQueue<>(Collections.reverseOrder());
// Or with custom comparator:
PriorityQueue<int[]> pq = new PriorityQueue<>((a, b) -> a[0] - b[0]);
pq.offer(element);              // Add
pq.poll();                      // Remove smallest/largest
pq.peek();                      // View smallest/largest
```

---

## 🔤 String Operations

```java
String s = "Hello World";

// Basic operations
s.length();                     // Length
s.charAt(0);                    // Char at index
s.substring(0, 5);              // "Hello" (end exclusive)
s.substring(6);                 // "World" (from index to end)

// Search
s.indexOf("o");                 // First occurrence (4)
s.lastIndexOf("o");             // Last occurrence (7)
s.contains("World");            // Check substring exists
s.startsWith("Hello");          // Prefix check
s.endsWith("World");            // Suffix check

// Comparison
s.equals("Hello World");        // Content equality
s.equalsIgnoreCase("hello world");
s.compareTo("other");           // Lexicographic comparison

// Transformation
s.toLowerCase();
s.toUpperCase();
s.trim();                       // Remove leading/trailing whitespace
s.strip();                      // Unicode-aware trim (Java 11+)
s.replace("o", "0");            // Replace all occurrences
s.replaceAll("\\s+", " ");      // Regex replace

// Split
String[] parts = s.split(" ");  // Split by delimiter
String[] words = s.split("\\s+"); // Split by whitespace (regex)

// Join
String joined = String.join("-", "a", "b", "c"); // "a-b-c"
String joined2 = String.join(",", list);         // Join list elements

// Char array conversion
char[] chars = s.toCharArray();
String fromChars = new String(chars);

// StringBuilder (mutable, efficient for concatenation)
StringBuilder sb = new StringBuilder();
sb.append("Hello");
sb.append(" World");
sb.insert(5, ",");              // "Hello, World"
sb.delete(5, 6);                // Remove range
sb.reverse();                   // Reverse in place
String result = sb.toString();
```

---

## 🔢 Arrays

```java
// Declaration & initialization
int[] arr = new int[10];                    // Size 10, default 0
int[] arr2 = {1, 2, 3, 4, 5};               // Direct init
int[][] matrix = new int[3][4];             // 2D array (3 rows, 4 cols)
int[][] jagged = {{1,2}, {3,4,5}, {6}};     // Jagged array

// Operations
arr.length;                                  // Length (property, not method!)
Arrays.sort(arr);                            // Sort ascending
Arrays.sort(arr, 0, 5);                      // Sort range [0, 5)
Arrays.fill(arr, -1);                        // Fill with value
Arrays.copyOf(arr, 10);                      // Copy with new length
Arrays.copyOfRange(arr, 1, 4);               // Copy range
Arrays.equals(arr, arr2);                    // Content equality
Arrays.binarySearch(arr, 3);                 // Binary search (must be sorted!)

// Convert to List
List<Integer> list = Arrays.asList(1, 2, 3); // Fixed-size list
List<Integer> list2 = new ArrayList<>(Arrays.asList(1, 2, 3)); // Mutable

// Stream operations (Java 8+)
int sum = Arrays.stream(arr).sum();
int max = Arrays.stream(arr).max().orElse(0);
int[] sorted = Arrays.stream(arr).sorted().toArray();

// 2D array iteration
for (int i = 0; i < matrix.length; i++) {
    for (int j = 0; j < matrix[i].length; j++) {
        // matrix[i][j]
    }
}
```

---

## 🔄 Iteration Patterns

```java
// Enhanced for loop
for (int num : list) { }
for (String key : map.keySet()) { }

// Index-based
for (int i = 0; i < list.size(); i++) { }

// Iterator (for safe removal during iteration)
Iterator<Integer> it = list.iterator();
while (it.hasNext()) {
    Integer val = it.next();
    if (condition) it.remove();  // Safe removal
}

// ListIterator (bidirectional)
ListIterator<Integer> lit = list.listIterator();
while (lit.hasNext()) {
    lit.next();
    lit.set(newValue);  // Replace current
    lit.add(value);     // Insert before next
}

// forEach with lambda
list.forEach(x -> System.out.println(x));
map.forEach((k, v) -> System.out.println(k + ": " + v));
```

---

## ⚡ Concurrency Essentials

### Thread Basics
```java
// Creating threads
// Option 1: Extend Thread
class MyThread extends Thread {
    public void run() { /* work */ }
}

// Option 2: Implement Runnable (preferred)
Runnable task = () -> { /* work */ };
Thread t = new Thread(task);
t.start();      // Start thread
t.join();       // Wait for completion

// Thread states
Thread.sleep(1000);         // Sleep (milliseconds)
Thread.yield();             // Hint to scheduler
Thread.currentThread();     // Current thread reference
```

### Synchronization
```java
// Synchronized method
public synchronized void method() { }

// Synchronized block
synchronized (lockObject) {
    // Critical section
}

// Volatile (visibility guarantee, no atomicity)
private volatile boolean flag;

// Atomic classes (thread-safe without locks)
AtomicInteger counter = new AtomicInteger(0);
counter.incrementAndGet();  // Atomic ++
counter.compareAndSet(expected, newValue);  // CAS
```

### Executor Framework
```java
// Thread pool
ExecutorService executor = Executors.newFixedThreadPool(4);
executor.submit(() -> { /* task */ });
executor.shutdown();

// Future (async result)
Future<Integer> future = executor.submit(() -> {
    return compute();
});
Integer result = future.get();          // Blocking wait
Integer result2 = future.get(5, TimeUnit.SECONDS);  // Timeout

// CompletableFuture (Java 8+)
CompletableFuture.supplyAsync(() -> compute())
    .thenApply(result -> transform(result))
    .thenAccept(result -> consume(result))
    .exceptionally(ex -> handleError(ex));
```

### Concurrent Collections
```java
ConcurrentHashMap<String, Integer> concurrentMap = new ConcurrentHashMap<>();
CopyOnWriteArrayList<String> cowList = new CopyOnWriteArrayList<>();
BlockingQueue<String> queue = new LinkedBlockingQueue<>();
queue.put("item");      // Blocks if full
queue.take();           // Blocks if empty
```

---

## 📁 File & I/O (For CodeCrafters)

### Reading Files
```java
// Read all lines
List<String> lines = Files.readAllLines(Path.of("file.txt"));

// Read as string
String content = Files.readString(Path.of("file.txt"));

// Buffered reading (large files)
try (BufferedReader reader = Files.newBufferedReader(Path.of("file.txt"))) {
    String line;
    while ((line = reader.readLine()) != null) {
        // Process line
    }
}
```

### Writing Files
```java
// Write string
Files.writeString(Path.of("file.txt"), "content");

// Write lines
Files.write(Path.of("file.txt"), lines);

// Buffered writing
try (BufferedWriter writer = Files.newBufferedWriter(Path.of("file.txt"))) {
    writer.write("content");
    writer.newLine();
}
```

### Process Execution (Shell Project!)
```java
// Execute external command
ProcessBuilder pb = new ProcessBuilder("ls", "-la");
pb.directory(new File("/path"));        // Working directory
pb.environment().put("VAR", "value");   // Environment variables

// Redirect I/O
pb.redirectInput(ProcessBuilder.Redirect.INHERIT);
pb.redirectOutput(ProcessBuilder.Redirect.INHERIT);
pb.redirectErrorStream(true);           // Merge stderr into stdout

Process process = pb.start();

// Read output
try (BufferedReader reader = new BufferedReader(
        new InputStreamReader(process.getInputStream()))) {
    String line;
    while ((line = reader.readLine()) != null) {
        System.out.println(line);
    }
}

int exitCode = process.waitFor();       // Wait for completion
```

### Environment Variables
```java
String path = System.getenv("PATH");
Map<String, String> env = System.getenv();  // All variables
String home = System.getProperty("user.home");
```

---

## 🛠️ Utility Classes

```java
// Math
Math.max(a, b);
Math.min(a, b);
Math.abs(x);
Math.pow(base, exp);
Math.sqrt(x);
Math.floor(x);
Math.ceil(x);
Math.round(x);
Math.random();          // [0.0, 1.0)

// Objects
Objects.equals(a, b);   // Null-safe equals
Objects.hash(a, b, c);  // Hash code
Objects.requireNonNull(obj, "message");

// Optional (avoid null)
Optional<String> opt = Optional.ofNullable(value);
opt.isPresent();
opt.orElse("default");
opt.orElseThrow();
opt.map(s -> s.toUpperCase());

// Comparator
list.sort(Comparator.naturalOrder());
list.sort(Comparator.reverseOrder());
list.sort(Comparator.comparing(Person::getName));
list.sort(Comparator.comparing(Person::getAge).reversed());
list.sort(Comparator.comparing(Person::getName)
                    .thenComparing(Person::getAge));
```

---

## 🎯 Common DSA Patterns in Java

### Two Pointers
```java
int left = 0, right = arr.length - 1;
while (left < right) {
    // Process arr[left] and arr[right]
    left++;
    right--;
}
```

### Sliding Window
```java
int left = 0, sum = 0;
for (int right = 0; right < arr.length; right++) {
    sum += arr[right];
    while (sum > target) {
        sum -= arr[left++];
    }
    // Window is [left, right]
}
```

### BFS Template
```java
Queue<Node> queue = new LinkedList<>();
Set<Node> visited = new HashSet<>();
queue.offer(start);
visited.add(start);

while (!queue.isEmpty()) {
    Node current = queue.poll();
    for (Node neighbor : current.neighbors) {
        if (!visited.contains(neighbor)) {
            visited.add(neighbor);
            queue.offer(neighbor);
        }
    }
}
```

### DFS Template
```java
void dfs(Node node, Set<Node> visited) {
    if (node == null || visited.contains(node)) return;
    visited.add(node);
    // Process node
    for (Node neighbor : node.neighbors) {
        dfs(neighbor, visited);
    }
}
```

### Binary Search
```java
int left = 0, right = arr.length - 1;
while (left <= right) {
    int mid = left + (right - left) / 2;  // Avoid overflow
    if (arr[mid] == target) return mid;
    else if (arr[mid] < target) left = mid + 1;
    else right = mid - 1;
}
return -1;  // Not found
```

---

## ⚠️ Common Gotchas

```java
// Integer comparison (use .equals() not ==)
Integer a = 128, b = 128;
a == b;        // FALSE! (outside cache range -128 to 127)
a.equals(b);   // TRUE

// String comparison
str1 == str2;        // Reference equality (usually wrong!)
str1.equals(str2);   // Content equality (usually right)

// Array length vs List size
arr.length;    // Array (field)
list.size();   // List (method)

// Modifying list during iteration
for (String s : list) {
    list.remove(s);  // ConcurrentModificationException!
}
// Use iterator.remove() or iterate backwards

// Integer division
5 / 2;         // = 2 (integer division)
5.0 / 2;       // = 2.5 (floating point)
(double) 5 / 2; // = 2.5

// Null checks
if (str != null && str.length() > 0)  // Safe
if (str.length() > 0 && str != null)  // NullPointerException!
```

---

*Reference this when you hit a Java syntax gap during CodeCrafters or DSA practice. If something isn't here, ask ATLAS to explain it in context.*
