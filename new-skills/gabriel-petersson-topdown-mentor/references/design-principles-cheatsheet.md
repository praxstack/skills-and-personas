# 🏗️ Design Principles & Patterns Cheatsheet

A reference for recognizing **when** and **why** to apply design principles. **You'll learn these through pain first** — when your CodeCrafters code becomes unmaintainable, come back here.

---

## 🎯 When Do You Need Design Principles?

**Signs your code needs restructuring:**
- 😰 Adding a feature requires changes in 5+ places
- 😰 You're copy-pasting code blocks
- 😰 One change breaks unrelated functionality
- 😰 You can't test a component in isolation
- 😰 The file is 500+ lines and growing
- 😰 You're scared to modify working code

---

## 📐 SOLID Principles

### S — Single Responsibility Principle (SRP)

> **"A class should have only one reason to change."**

**The Pain You'll Feel Without It:**
```java
// BAD: ShellCommand does everything
class ShellCommand {
    void parse(String input) { ... }
    void execute() { ... }
    void redirectOutput() { ... }
    void logHistory() { ... }
    void handlePipes() { ... }
}
// Problem: Change to parsing? Might break execution. Change to logging? Might break redirection.
```

**The Fix:**
```java
// GOOD: Each class has ONE job
class CommandParser { String[] parse(String input); }
class CommandExecutor { int execute(String[] args); }
class OutputRedirector { void redirect(OutputStream out); }
class HistoryLogger { void log(String command); }
```

**When to Apply:**
- Your class has multiple "sections" doing different things
- You describe the class using "AND" (parses AND executes AND logs)

---

### O — Open/Closed Principle (OCP)

> **"Open for extension, closed for modification."**

**The Pain You'll Feel Without It:**
```java
// BAD: Adding new command requires modifying this method
void execute(String command) {
    if (command.equals("cd")) { ... }
    else if (command.equals("pwd")) { ... }
    else if (command.equals("echo")) { ... }
    // Every new command = modify this growing if-else
}
```

**The Fix:**
```java
// GOOD: Add new commands without changing existing code
interface Command {
    void execute(String[] args);
}

class CdCommand implements Command { ... }
class PwdCommand implements Command { ... }
class EchoCommand implements Command { ... }

Map<String, Command> commands = Map.of(
    "cd", new CdCommand(),
    "pwd", new PwdCommand()
);
// New command? Just add to map. No existing code changes.
```

**When to Apply:**
- You have a growing if-else or switch statement
- Adding features means touching stable, working code

---

### L — Liskov Substitution Principle (LSP)

> **"Subtypes must be substitutable for their base types."**

**The Pain You'll Feel Without It:**
```java
// BAD: Square "is a" Rectangle but behaves differently
class Rectangle {
    void setWidth(int w) { this.width = w; }
    void setHeight(int h) { this.height = h; }
}

class Square extends Rectangle {
    void setWidth(int w) { this.width = w; this.height = w; }  // Surprise!
    void setHeight(int h) { this.width = h; this.height = h; } // Surprise!
}

// Code expecting Rectangle breaks with Square
void resize(Rectangle r) {
    r.setWidth(10);
    r.setHeight(20);
    assert r.area() == 200;  // Fails for Square!
}
```

**The Fix:**
- Don't inherit if the subtype can't fully replace the parent
- Use composition or separate interfaces

**When to Apply:**
- Subclass overrides parent method with different behavior
- You're checking `instanceof` to handle subtypes differently

---

### I — Interface Segregation Principle (ISP)

> **"Clients shouldn't depend on interfaces they don't use."**

**The Pain You'll Feel Without It:**
```java
// BAD: One fat interface
interface Shell {
    void executeCommand();
    void handlePipe();
    void handleRedirection();
    void handleGlobbing();
    void handleAliases();
}

// SimpleShell forced to implement features it doesn't need
class SimpleShell implements Shell {
    void handleAliases() { throw new UnsupportedOperationException(); }  // Ugly!
}
```

**The Fix:**
```java
// GOOD: Small, focused interfaces
interface CommandExecutor { void execute(); }
interface PipeHandler { void handlePipe(); }
interface RedirectionHandler { void handleRedirection(); }

class SimpleShell implements CommandExecutor { ... }  // Only what it needs
class AdvancedShell implements CommandExecutor, PipeHandler, RedirectionHandler { ... }
```

**When to Apply:**
- Classes implement interfaces but leave methods empty/throwing
- Interface has 10+ methods

---

### D — Dependency Inversion Principle (DIP)

> **"Depend on abstractions, not concretions."**

**The Pain You'll Feel Without It:**
```java
// BAD: High-level Shell depends on low-level FileSystemImpl
class Shell {
    private FileSystemImpl fs = new FileSystemImpl();  // Hard dependency
    
    void executeCommand() {
        fs.readFile(...);  // Can't test without real file system!
    }
}
```

**The Fix:**
```java
// GOOD: Depend on interface, inject implementation
interface FileSystem {
    String readFile(String path);
}

class Shell {
    private FileSystem fs;  // Abstraction
    
    Shell(FileSystem fs) {  // Injection
        this.fs = fs;
    }
}

// In production: new Shell(new RealFileSystem())
// In tests: new Shell(new MockFileSystem())
```

**When to Apply:**
- You can't test a class without its dependencies
- You use `new` inside classes for dependencies
- Changing a low-level module breaks high-level modules

---

## 🎨 Common Design Patterns

### Creational Patterns

#### Factory Method
**Problem:** Object creation logic is complex or varies
**Solution:** Delegate creation to factory method/class

```java
interface Command { void execute(); }

class CommandFactory {
    static Command create(String name) {
        return switch(name) {
            case "cd" -> new CdCommand();
            case "ls" -> new LsCommand();
            default -> new ExternalCommand(name);
        };
    }
}
```

**Use when:** You have `new` scattered everywhere with conditional logic

---

#### Builder
**Problem:** Object has many optional parameters
**Solution:** Fluent API for step-by-step construction

```java
ProcessBuilder pb = new ProcessBuilder()
    .command("ls", "-la")
    .directory(new File("/home"))
    .redirectErrorStream(true);
```

**Use when:** Constructor has 4+ parameters, many optional

---

#### Singleton
**Problem:** Only one instance should exist
**Solution:** Private constructor, static instance

```java
class ShellConfig {
    private static ShellConfig instance;
    private ShellConfig() {}
    
    static synchronized ShellConfig getInstance() {
        if (instance == null) instance = new ShellConfig();
        return instance;
    }
}
```

**Use when:** Global state that must be consistent (use sparingly!)

---

### Structural Patterns

#### Adapter
**Problem:** Interface mismatch between components
**Solution:** Wrapper that translates interfaces

```java
// Old interface
interface LegacyPrinter { void printText(String text); }

// New interface you need
interface ModernPrinter { void print(Document doc); }

// Adapter
class PrinterAdapter implements ModernPrinter {
    private LegacyPrinter legacy;
    
    void print(Document doc) {
        legacy.printText(doc.getText());  // Translate!
    }
}
```

**Use when:** Integrating with external/legacy code

---

#### Decorator
**Problem:** Add behavior without modifying class
**Solution:** Wrapper that adds functionality

```java
interface InputStream { int read(); }

class BufferedInputStream implements InputStream {
    private InputStream wrapped;
    
    int read() {
        // Add buffering logic
        return wrapped.read();
    }
}

// Usage: new BufferedInputStream(new FileInputStream("file"))
```

**Use when:** Java I/O streams, adding cross-cutting concerns

---

#### Facade
**Problem:** Complex subsystem is hard to use
**Solution:** Simple interface hiding complexity

```java
// Complex subsystem
class Lexer { ... }
class Parser { ... }
class Executor { ... }

// Facade
class Shell {
    void run(String input) {
        tokens = new Lexer().tokenize(input);
        ast = new Parser().parse(tokens);
        new Executor().execute(ast);
    }
}
```

**Use when:** Subsystem has many classes, clients need simple interface

---

### Behavioral Patterns

#### Strategy
**Problem:** Algorithm varies based on context
**Solution:** Encapsulate algorithms in interchangeable classes

```java
interface SortStrategy { void sort(int[] arr); }
class QuickSort implements SortStrategy { ... }
class MergeSort implements SortStrategy { ... }

class Sorter {
    private SortStrategy strategy;
    void setStrategy(SortStrategy s) { this.strategy = s; }
    void sort(int[] arr) { strategy.sort(arr); }
}
```

**Use when:** Multiple algorithms for same task, selected at runtime

---

#### Command
**Problem:** Need to parameterize operations, queue them, or undo
**Solution:** Encapsulate request as object

```java
interface Command {
    void execute();
    void undo();
}

class TypeCommand implements Command {
    private Document doc;
    private String text;
    
    void execute() { doc.append(text); }
    void undo() { doc.removeLast(text.length()); }
}
```

**Use when:** Shell commands (!), undo/redo, task queues

---

#### Observer
**Problem:** Object changes should notify others
**Solution:** Subject maintains list of observers

```java
interface Observer { void update(Event e); }

class EventEmitter {
    private List<Observer> observers = new ArrayList<>();
    
    void subscribe(Observer o) { observers.add(o); }
    void emit(Event e) {
        for (Observer o : observers) o.update(e);
    }
}
```

**Use when:** Event systems, pub/sub, reactive programming

---

#### Template Method
**Problem:** Algorithm structure is same, steps vary
**Solution:** Abstract class with template method calling abstract steps

```java
abstract class DataProcessor {
    // Template method - structure fixed
    final void process() {
        readData();
        processData();
        writeResults();
    }
    
    abstract void readData();      // Subclass implements
    abstract void processData();   // Subclass implements
    abstract void writeResults();  // Subclass implements
}
```

**Use when:** Framework code, test fixtures (setup/test/teardown)

---

## 🔗 Pattern Selection Guide

| Problem | Consider |
|---------|----------|
| Object creation is complex | Factory, Builder |
| Need single instance | Singleton |
| Interface mismatch | Adapter |
| Add behavior dynamically | Decorator |
| Hide complex subsystem | Facade |
| Multiple algorithms | Strategy |
| Encapsulate operations | Command |
| Notify on state change | Observer |
| Fixed algorithm, variable steps | Template Method |

---

## 🎯 For CodeCrafters Shell Project

Patterns you'll likely encounter/need:

| Stage | Pain Point | Pattern/Principle |
|-------|------------|-------------------|
| Stage 5-6 | Growing if-else for commands | **Command Pattern** + OCP |
| Stage 7-8 | Execution logic everywhere | **SRP** - separate Parser, Executor |
| Stage 9+ | Testing is hard | **DIP** - inject dependencies |
| Piping | Chaining operations | **Decorator** or **Chain of Responsibility** |
| Refactoring | God class | **Facade** + **SRP** |

---

## 💡 The Learning Process

1. **Write code that works** (ignore patterns initially)
2. **Feel the pain** (code becomes hard to change)
3. **Identify the smell** (which principle is violated?)
4. **Apply minimal fix** (one pattern at a time)
5. **Verify improvement** (is it actually easier to change now?)

**Don't apply patterns preemptively.** Apply them when you feel the specific pain they solve.

---

*Patterns are not goals — they're tools. The goal is maintainable, testable, extensible code. Use the minimum pattern necessary.*
