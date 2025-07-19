# Session-Restart Resilient Development Guide

**Purpose**: Practical guide for maintaining development consistency across session restarts
**Integration**: TaskMaster + UCKN + Local CLAUDE.md + ai_docs
**Date**: 2025-07-12

---

## 🎯 **THE SESSION RESTART PROBLEM**

### **Challenge**
- Context window limitations require frequent session restarts
- Methodology knowledge gets lost between sessions
- Inconsistent development approach leads to technical debt
- "Big bang" integration issues when methodology not followed

### **Solution Strategy**
Make methodology **persistent and self-contained** in multiple layers:
1. **TaskMaster tasks** with embedded methodology context
2. **UCKN patterns** for methodology retrieval
3. **Local CLAUDE.md** for immediate context
4. **ai_docs** for comprehensive documentation

---

## 🔄 **SESSION RESTART PROCEDURE**

### **Step 1: Context Recovery (5 minutes)**
```bash
# 1. Read local methodology reminders
cat .claude/CLAUDE.md

# 2. Get current TaskMaster state
mcp__task-master-ai__get_tasks --projectRoot="." --status="in-progress"

# 3. Get next task with embedded methodology
mcp__task-master-ai__next_task --projectRoot="."

# 4. Read comprehensive methodology
cat ai_docs/development-methodology.md

# 5. Search UCKN for methodology patterns
mcp__uckn-knowledge__search_patterns --query="ci framework development methodology"
```

### **Step 2: State Validation (2 minutes)**
```bash
# Verify current state
git status
git branch --show-current
pixi list

# Check last completed subtask
mcp__task-master-ai__get_task --id="[current-task-id]" --projectRoot="."

# Validate environment
pixi run test
pixi run lint
```

### **Step 3: Resume Development (immediate)**
- Read current subtask methodology_step from TaskMaster
- Follow embedded 9-step cycle instructions
- Use target project paths from task description
- Apply gate requirements from task context

---

## 📋 **TASKMASTER METHODOLOGY EMBEDDING**

### **Initial TaskMaster Setup**
```bash
# Initialize TaskMaster for CI Framework project
mcp__task-master-ai__initialize_project --projectRoot="."

# Add methodology pattern to UCKN for persistence
mcp__uckn-knowledge__contribute_pattern \
  --pattern-title "CI Framework Development Methodology" \
  --pattern-type "best_practice" \
  --pattern-description "Integration-First BDD/TDD Hybrid for meta-tooling development with strict gates" \
  --pattern-code "9-step cycle: BDD → TDD → Implement → Integrate(2x) → Benchmark → Compatibility → Document → Gates" \
  --technologies ["ci-cd", "testing", "taskmaster", "meta-tooling", "bdd", "tdd", "integration-testing"]
```

### **Example: First Task with Embedded Methodology**
```bash
# Add first task with complete methodology context
mcp__task-master-ai__add_task \
  --projectRoot="." \
  --prompt="Create Quality Gates Action with complete methodology embedding:

TASK: Quality Gates Action - Tiered quality validation system

METHODOLOGY CONTEXT (embedded in task):
🔄 DEVELOPMENT CYCLE for this task:
1. BDD: Define acceptance scenarios (Given/When/Then)
2. TDD: Write component tests first
3. Implement: Minimal code to pass tests
4. Integrate: Test with hb-strategy-sandbox (/home/memento/ClaudeCode/Project/hb-strategy-sandbox/worktrees/feat-workspace-phase2)
5. Integrate: Test with cheap-llm (/home/memento/ClaudeCode/Servers/cheap-llm/worktrees/feat-phase1)
6. Benchmark: Performance validation vs baseline
7. Compatibility: Test Python 3.10-3.12, ubuntu/macos
8. Document: Update docs with examples
9. Gate Check: ALL criteria must pass before next task

🎯 MANDATORY GATES (ALL must pass):
- Unit tests: 100% pass, 95%+ coverage
- Integration: Works with 2+ real projects
- Performance: ≤5% regression or improvement
- Compatibility: Cross-platform validation
- CI: All automated checks passing
- Docs: Current and complete

ACCEPTANCE CRITERIA:
Given a project with tiered pyproject.toml (essential/extended/full)
When developer runs quality gates action
Then appropriate tier executes with zero-tolerance policy

Given hb-strategy-sandbox project
When quality gates action applied
Then existing framework integration maintained

Given cheap-llm project
When quality gates action applied
Then tiered quality approach works seamlessly"
```

### **Subtask Auto-Expansion with Methodology**
```bash
# Expand task into methodology-embedded subtasks
mcp__task-master-ai__expand_task \
  --id="1" \
  --projectRoot="." \
  --num="9" \
  --prompt="Expand into 9 subtasks following the Integration-First BDD/TDD Hybrid methodology. Each subtask must include:

1. methodology_step field indicating which of the 9 steps
2. Complete description with methodology context
3. Specific acceptance criteria
4. Target project paths for integration testing
5. Gate requirements for completion
6. Dependencies on previous subtask completion

Follow the template from ai_docs/development-methodology.md exactly."
```

---

## 🧠 **UCKN INTEGRATION FOR PATTERN PERSISTENCE**

### **Contributing Methodology Patterns**
```bash
# Core methodology pattern
mcp__uckn-knowledge__contribute_pattern \
  --pattern-title "Integration-First Testing for Meta-Tooling" \
  --pattern-type "best_practice" \
  --pattern-description "For CI/CD frameworks, integration testing is more critical than unit testing because value comes from real-world project integration" \
  --pattern-code "Test every component against 2+ real target projects immediately" \
  --technologies ["meta-tooling", "integration-testing", "ci-framework"]

# Gate validation pattern
mcp__uckn-knowledge__contribute_pattern \
  --pattern-title "Mandatory Development Gates for Quality" \
  --pattern-type "best_practice" \
  --pattern-description "ALL gates must pass before proceeding to prevent technical debt accumulation" \
  --pattern-code "Gates: Unit tests (100%), Integration (2+ projects), Performance (≤5% regression), Compatibility (matrix), CI (passing), Docs (current)" \
  --technologies ["quality-gates", "development-process", "technical-debt-prevention"]

# Performance-first pattern
mcp__uckn-knowledge__contribute_pattern \
  --pattern-title "Performance Benchmarking with Every Change" \
  --pattern-type "best_practice" \
  --pattern-description "CI framework speed directly impacts developer productivity - benchmark with every change" \
  --pattern-code "Baseline measurement → Implementation → Benchmark comparison → Accept only if ≤5% regression or improvement" \
  --technologies ["performance", "ci-framework", "developer-productivity"]
```

### **Retrieving Methodology on Session Restart**
```bash
# Get methodology patterns
mcp__uckn-knowledge__search_patterns \
  --query="ci framework development methodology" \
  --pattern-type="best_practice" \
  --limit=10

# Get integration testing patterns
mcp__uckn-knowledge__search_patterns \
  --query="integration-first testing meta-tooling" \
  --pattern-type="best_practice" \
  --limit=5

# Get gate validation patterns
mcp__uckn-knowledge__search_patterns \
  --query="mandatory development gates quality" \
  --pattern-type="best_practice" \
  --limit=5
```

---

## 📊 **CONSISTENCY VALIDATION**

### **Session Restart Consistency Check**
```bash
# Verify methodology consistency across sources
echo "=== METHODOLOGY CONSISTENCY CHECK ==="

echo "1. Local CLAUDE.md methodology summary:"
grep -A 5 "9-STEP CYCLE" .claude/CLAUDE.md

echo "2. Current TaskMaster task methodology:"
mcp__task-master-ai__get_task --id="[current-task]" --projectRoot="." | grep -A 10 "methodology"

echo "3. UCKN methodology patterns:"
mcp__uckn-knowledge__search_patterns --query="integration-first bdd tdd" --limit=3

echo "4. ai_docs methodology reference:"
grep -A 5 "STRICT DEVELOPMENT CYCLE" ai_docs/development-methodology.md
```

### **Validation Criteria**
- [ ] All sources mention 9-step development cycle
- [ ] All sources specify same mandatory gates
- [ ] Target project paths consistent across sources
- [ ] Performance requirements match across documentation
- [ ] Gate validation approach identical

---

## 🎯 **PRACTICAL SESSION RESTART EXAMPLE**

### **Scenario: Restart mid-development of Quality Gates Action**

#### **Context Recovery (what you'd see)**
```bash
# 1. Read local context
$ cat .claude/CLAUDE.md
# Shows: 9-step methodology, target projects, gate requirements

# 2. Get TaskMaster state
$ mcp__task-master-ai__get_tasks --projectRoot="." --status="in-progress"
# Returns: Task 1 (Quality Gates Action) with 9 subtasks, subtask 1.3 in-progress

# 3. Get specific subtask details
$ mcp__task-master-ai__get_task --id="1.3" --projectRoot="."
# Returns: "Implement minimal solution" with methodology_step="TDD_IMPLEMENTATION"
# Includes: Complete context, acceptance criteria, gate requirements

# 4. Check UCKN patterns
$ mcp__uckn-knowledge__search_patterns --query="tdd implementation minimal"
# Returns: Patterns about minimal implementation approach
```

#### **Resume Development (what you'd do)**
1. **Understand current state**: Subtask 1.3 "TDD Implementation"
2. **Read methodology context**: Write minimal code to pass tests only
3. **Check dependencies**: Subtask 1.2 (TDD Tests) completed
4. **Review acceptance criteria**: All unit tests passing, no over-engineering
5. **Implement**: Write minimal code following TDD approach
6. **Validate gates**: Unit tests pass, ready for integration testing
7. **Update TaskMaster**: Mark subtask 1.3 complete, proceed to 1.4

### **No Lost Context**
- Methodology consistent across all sources
- Target project paths available in task descriptions
- Gate requirements explicit in every subtask
- Performance baselines documented
- Development approach preserved

---

## ✅ **SUCCESS INDICATORS**

### **Session Restart Efficiency**
- **< 5 minutes** to full context recovery
- **Zero methodology confusion** across sessions
- **Consistent development approach** maintained
- **No technical debt accumulation** from forgotten gates

### **Development Consistency**
- **Same 9-step cycle** followed every session
- **Same gate requirements** applied every subtask
- **Same target projects** used for integration testing
- **Same performance standards** maintained

### **Knowledge Persistence**
- **TaskMaster tasks self-contained** with methodology
- **UCKN patterns retrievable** for methodology details
- **Local CLAUDE.md current** with project context
- **ai_docs comprehensive** for deep reference

---

**🎯 Result: Development methodology survives session restarts and maintains consistency throughout the entire PRD implementation, preventing "big bang" integration issues and ensuring high-quality, production-ready components.**
