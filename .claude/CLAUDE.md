# CI Framework Development Context

**Project**: MementoRC CI Framework
**Methodology**: Integration-First BDD/TDD Hybrid
**Memory Strategy**: TaskMaster + UCKN + This Document

---

## 🔄 **METHODOLOGY REMINDER (Session Restart Safe)**

### **BEFORE STARTING ANY TASK:**
1. ✅ Check TaskMaster for current task with embedded methodology context
2. ✅ Read `ai_docs/development-methodology.md` for complete approach
3. ✅ Follow the 9-step development cycle strictly (no shortcuts)
4. ✅ Validate ALL gates before proceeding to next subtask

### **9-STEP CYCLE (Mandatory Order):**
```
1. BDD Scenario Definition     ← User acceptance criteria
2. TDD Test Implementation     ← Write failing tests first
3. Minimal Implementation      ← Code to pass tests only
4. Integration Test #1         ← hb-strategy-sandbox
5. Integration Test #2         ← cheap-llm or other project
6. Performance Benchmark       ← Speed validation vs baseline
7. Compatibility Matrix       ← Python 3.10-3.12, ubuntu/macos
8. Documentation Update       ← Current docs with examples
9. Gate Validation            ← ALL gates pass before next subtask
```

### **MANDATORY GATES (ALL must pass):**
- [ ] Unit Tests: 100% pass rate, 95%+ coverage
- [ ] Integration: Works with 2+ target projects
- [ ] Performance: Within 5% of baseline or improvement
- [ ] Compatibility: Python 3.10-3.12, ubuntu/macos
- [ ] CI Validation: All automated checks passing
- [ ] Documentation: Complete and current

---

## 📂 **TARGET PROJECTS (Integration Testing)**

### **Primary Integration Target:**
```
/home/memento/ClaudeCode/Project/hb-strategy-sandbox/worktrees/feat-workspace-phase2
```
- **Use for**: Option 1 drop-in testing, framework replacement validation
- **Contains**: Existing framework/ folder that can be replaced
- **Testbed branches**: testbed/ci-option1-drop-in, testbed/ci-option2-remote-actions, testbed/ci-option3-hybrid

### **Secondary Integration Targets:**
```
/home/memento/ClaudeCode/Servers/cheap-llm/worktrees/feat-phase1
/home/memento/ClaudeCode/Servers/claude-code-knowledge-framework/worktrees/feat-task-3
/home/memento/ClaudeCode/Servers/git/worktrees/feat-llm-compliance
/home/memento/ClaudeCode/Servers/aider/development
/home/memento/ClaudeCode/Servers/pytest-analyzer/worktrees/feat-security-hardening
/home/memento/ClaudeCode/candles-feed/hummingbot/sub-packages/candles-feed
```

---

## 🎯 **PROJECT CONTEXT (Current State)**

### **What We Have:**
- ✅ Comprehensive PRD in `ai_docs/ci-framework-comprehensive-prd.md`
- ✅ Development methodology in `ai_docs/development-methodology.md`
- ✅ Current cleanup action in `action.yml`
- ✅ Existing framework separation pattern in hb-strategy-sandbox
- ✅ Tiered pyproject.toml guidelines in `.claude/commands/references/`

### **What We're Building:**
- **3 Deployment Options**: Drop-in, Remote Actions, Hybrid
- **Quality Gates Action**: Tiered quality validation (essential/extended/full)
- **Security Scan Action**: Unified security scanning with SARIF
- **Performance Bench Action**: Benchmarking with regression detection
- **Change Detection Action**: Smart CI optimization
- **Local CI Scripts**: Self-contained local development capabilities

### **Architecture:**
```
ci-framework/
├── actions/           # GitHub Actions (Remote CI)
├── scripts/           # Local CI Scripts (Drop-in)
├── templates/         # Configuration templates
├── workflows/         # Complete workflow templates
├── configs/           # Portable configurations
└── ai_docs/          # Development documentation
```

---

## 🧠 **MEMORY PERSISTENCE COMMANDS**

### **Session Restart Recovery:**
```bash
# Get current TaskMaster state with methodology context
mcp__task-master-ai__get_tasks --projectRoot="." --status="in-progress"

# Get next task (contains embedded methodology)
mcp__task-master-ai__next_task --projectRoot="."

# Get specific task with complete context
mcp__task-master-ai__get_task --id="[task-id]" --projectRoot="."

# Search UCKN for methodology patterns
mcp__uckn-knowledge__search_patterns --query="ci framework development methodology"

# Contribute new patterns to UCKN
mcp__uckn-knowledge__contribute_pattern \
  --pattern-title "CI Framework Integration Testing" \
  --pattern-type "best_practice" \
  --pattern-description "Test against real projects with every change"
```

### **Validate Current State:**
```bash
# Check git status
git status

# Verify project structure
ls -la

# Check if on correct branch
git branch --show-current

# Validate pixi environment
pixi list

# Run current quality checks
pixi run test
pixi run lint
pixi run quality
```

---

## ⚠️ **CRITICAL SUCCESS FACTORS**

### **🚨 NO SHORTCUTS ALLOWED:**
- Every subtask MUST complete all 9 methodology steps
- ALL gates must pass before proceeding
- Integration testing is MORE important than unit testing
- Performance benchmarking with EVERY change

### **🎯 INTEGRATION-FIRST PRINCIPLE:**
- **Unit tests are necessary but NOT sufficient**
- **Real-world validation with target projects is critical**
- **Meta-tooling must work with actual projects, not just in isolation**

### **📊 PERFORMANCE REQUIREMENTS:**
- Installation time ≤ current baseline
- Execution time within 5% of current (or improvement)
- CI pipeline duration impact measured and minimized

---

## 🔄 **TASK WORKFLOW INTEGRATION**

### **Starting a Task:**
1. Read TaskMaster task description (contains methodology context)
2. Check embedded `methodology_step` for current phase
3. Follow specific step instructions in task description
4. Use target project paths provided in task

### **Completing a Subtask:**
1. Verify ALL gates passed (checklist in task description)
2. Update TaskMaster status to "completed"
3. Move to next subtask ONLY after gate validation

### **Handling Issues:**
1. Fix immediately, don't accumulate technical debt
2. Re-run ALL validation steps after fixes
3. Document issues and solutions in task updates
4. Only proceed when ALL gates pass

---

## 🎯 **3 DEPLOYMENT OPTIONS CONTEXT**

### **Option 1: Drop-in Replacement**
- Target: Replace existing framework/ folders
- Test with: hb-strategy-sandbox framework/ replacement
- Validation: Same CLI interface, enhanced capabilities

### **Option 2: Remote GitHub Actions**
- Target: Pure GitHub Actions approach
- Test with: Remote action workflows
- Validation: No local dependencies, centralized maintenance

### **Option 3: Hybrid Local + Remote**
- Target: Best of both worlds
- Test with: Local development + remote CI
- Validation: Development velocity + centralized quality

---

## 📚 **DOCUMENTATION HIERARCHY**

1. **This File**: Session restart context and methodology reminders
2. **ai_docs/development-methodology.md**: Complete methodology documentation
3. **ai_docs/ci-framework-comprehensive-prd.md**: Full product requirements
4. **TaskMaster Tasks**: Self-contained methodology context per task
5. **UCKN Patterns**: Contributed best practices for retrieval

---

**🎯 REMEMBER: TaskMaster tasks contain complete methodology context. When in doubt, check the current task description for embedded methodology instructions.**
