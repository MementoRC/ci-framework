# CI Framework Development Methodology

**Version**: 1.0  
**Date**: 2025-07-12  
**Purpose**: Session-restart resilient development methodology for CI Framework PRD implementation  
**Integration**: TaskMaster AI + UCKN + CLAUDE.md  

---

## 🎯 **METHODOLOGY OVERVIEW: Integration-First BDD/TDD Hybrid**

### **Core Principle**
For CI/CD framework development, **integration testing is more critical than unit testing** because the framework's value comes from real-world project integration, not isolated component function.

### **3-Layer Testing Approach**
1. **BDD Layer**: User scenario acceptance criteria
2. **TDD Layer**: Component reliability through test-first development
3. **Integration Layer**: Real-world validation against target projects

---

## 🔄 **STRICT DEVELOPMENT CYCLE**

### **Per-Subtask Cycle (Mandatory Order)**
```
1. BDD Scenario Definition     ← Define acceptance criteria
2. TDD Test Implementation     ← Write failing tests first
3. Minimal Implementation      ← Code to pass tests only
4. Integration Test #1         ← Test against hb-strategy-sandbox
5. Integration Test #2         ← Test against cheap-llm or other project
6. Performance Benchmark       ← Validate speed requirements
7. Compatibility Matrix       ← Test across Python versions/platforms
8. Documentation Update       ← Maintain current documentation
9. TaskMaster Gate Validation ← ALL gates must pass before next subtask
```

### **Mandatory Gates (ALL must pass)**
- [ ] **Unit Tests**: 100% pass rate, 95%+ coverage
- [ ] **Integration Tests**: Works with 2+ target projects
- [ ] **Performance**: Within 5% of baseline or shows improvement
- [ ] **Compatibility**: Python 3.10-3.12, ubuntu/macos support
- [ ] **CI Validation**: All quality gates passing in CI environment
- [ ] **Documentation**: Updated with examples and troubleshooting

---

## 📋 **TASKMASTER INTEGRATION STRATEGY**

### **Session-Restart Resilience**
Each TaskMaster task/subtask contains **COMPLETE methodology context** so that when sessions restart, the development approach is preserved and consistent.

### **Self-Contained Task Template**
```yaml
# TaskMaster Task Structure with Embedded Methodology
Task X: [Feature Name]
  methodology_context: |
    🔄 DEVELOPMENT CYCLE for this task:
    1. BDD: Define acceptance scenarios (Given/When/Then)
    2. TDD: Write component tests first
    3. Implement: Minimal code to pass tests
    4. Integrate: Test with hb-strategy-sandbox
    5. Integrate: Test with second target project
    6. Benchmark: Performance validation vs baseline
    7. Compatibility: Test Python 3.10-3.12, ubuntu/macos
    8. Document: Update docs with examples
    9. Gate Check: ALL criteria must pass before next task
    
    🎯 QUALITY GATES (ALL mandatory):
    - Unit tests: 100% pass, 95%+ coverage
    - Integration: Works with 2+ real projects
    - Performance: ≤5% regression or improvement
    - Compatibility: Cross-platform validation
    - CI: All automated checks passing
    - Docs: Current and complete
  
  description: "[Specific task description]"
  acceptance_criteria: "[BDD scenarios]"
  
  subtasks:
    X.1:
      title: "BDD - Define acceptance scenarios"
      methodology_step: "BDD_SCENARIOS"
      description: |
        📝 BDD METHODOLOGY STEP 1:
        Define clear Given/When/Then scenarios for this feature
        Focus on user experience and real-world usage patterns
        
        ACCEPTANCE CRITERIA:
        - [Specific scenarios for this feature]
      
    X.2:
      title: "TDD - Write component tests"
      methodology_step: "TDD_TESTS"
      dependencies: ["X.1"]
      description: |
        🧪 TDD METHODOLOGY STEP 2:
        Write failing tests BEFORE implementation
        Tests should cover all scenarios from X.1
        
        MANDATORY REQUIREMENTS:
        - All tests initially failing (red state)
        - 95%+ code coverage target
        - Error condition testing included
      
    X.3:
      title: "Implement minimal solution"
      methodology_step: "TDD_IMPLEMENTATION"
      dependencies: ["X.2"]
      description: |
        ⚙️ TDD METHODOLOGY STEP 3:
        Write MINIMAL code to make tests pass (green state)
        No additional features beyond test requirements
        
        SUCCESS CRITERIA:
        - All unit tests passing
        - No over-engineering beyond test needs
        - Code ready for integration testing
      
    X.4:
      title: "Integration test - hb-strategy-sandbox"
      methodology_step: "INTEGRATION_PRIMARY"
      dependencies: ["X.3"]
      description: |
        🔗 INTEGRATION METHODOLOGY STEP 4:
        Test against PRIMARY target project
        Real-world validation of implementation
        
        TARGET PROJECT: /home/memento/ClaudeCode/Project/hb-strategy-sandbox/worktrees/feat-workspace-phase2
        
        VALIDATION REQUIREMENTS:
        - Feature works with existing framework structure
        - No breaking changes to current workflows
        - Performance comparable to current implementation
        - Integration success documented with examples
      
    X.5:
      title: "Integration test - second project"
      methodology_step: "INTEGRATION_SECONDARY"
      dependencies: ["X.4"]
      description: |
        🔗 INTEGRATION METHODOLOGY STEP 5:
        Test against SECONDARY target project
        Validate cross-project compatibility
        
        SUGGESTED TARGETS:
        - /home/memento/ClaudeCode/Servers/cheap-llm/worktrees/feat-phase1
        - /home/memento/ClaudeCode/Servers/claude-code-knowledge-framework/worktrees/feat-task-3
        
        VALIDATION REQUIREMENTS:
        - Works with different project patterns
        - Maintains functionality across diverse setups
        - Performance acceptable across project types
      
    X.6:
      title: "Performance benchmark"
      methodology_step: "PERFORMANCE_VALIDATION"
      dependencies: ["X.5"]
      description: |
        📊 PERFORMANCE METHODOLOGY STEP 6:
        Benchmark against baseline performance
        Prevent performance regressions
        
        BENCHMARK REQUIREMENTS:
        - Installation time ≤ current baseline
        - Execution time within 5% of current (or improvement)
        - Memory usage comparable to current
        - CI pipeline duration impact measured
        
        BASELINE PROJECTS for comparison:
        - Current hb-strategy-sandbox CI times
        - Current quality gate execution times
      
    X.7:
      title: "Compatibility matrix test"
      methodology_step: "COMPATIBILITY_VALIDATION"
      dependencies: ["X.6"]
      description: |
        🌐 COMPATIBILITY METHODOLOGY STEP 7:
        Cross-environment validation
        Ensure broad platform support
        
        MANDATORY TEST MATRIX:
        - Python 3.10, 3.11, 3.12
        - Ubuntu latest, macOS latest
        - Different pixi versions (v0.49.0+)
        
        SUCCESS CRITERIA:
        - 100% functionality across all matrix combinations
        - No platform-specific issues
        - Consistent behavior across environments
      
    X.8:
      title: "Documentation and examples"
      methodology_step: "DOCUMENTATION"
      dependencies: ["X.7"]
      description: |
        📚 DOCUMENTATION METHODOLOGY STEP 8:
        Complete and current documentation
        Real-world usage examples
        
        DOCUMENTATION REQUIREMENTS:
        - Usage examples for all features
        - Integration guide for existing projects
        - Troubleshooting section with common issues
        - Performance characteristics documented
        - API reference if applicable
      
    X.9:
      title: "Gate validation checkpoint"
      methodology_step: "GATE_VALIDATION"
      dependencies: ["X.8"]
      description: |
        ✅ GATE VALIDATION METHODOLOGY STEP 9:
        MANDATORY checkpoint before next task
        Verify ALL gates passed
        
        GATE CHECKLIST (ALL must be ✅):
        - [ ] Unit tests: 100% pass rate, 95%+ coverage
        - [ ] Integration: Works with 2+ target projects
        - [ ] Performance: Within 5% of baseline or improvement
        - [ ] Compatibility: Python 3.10-3.12, ubuntu/macos
        - [ ] CI Validation: All automated checks passing
        - [ ] Documentation: Complete and current
        
        ONLY AFTER ALL GATES PASS:
        - Update TaskMaster task status to "completed"
        - Proceed to next task/subtask
        
        IF ANY GATE FAILS:
        - Fix issues immediately
        - Re-run all validation steps
        - Do not proceed until ALL gates pass
```

---

## 🧠 **MEMORY PERSISTENCE STRATEGY**

### **TaskMaster as Source of Truth**
- **All methodology context embedded in tasks** - survives session restarts
- **Gate requirements explicit in each subtask** - no methodology knowledge assumed
- **Target project paths included** - specific integration test directions
- **Performance baselines documented** - consistent benchmark targets

### **UCKN Integration for Pattern Persistence**
```bash
# Contribute methodology patterns to UCKN
mcp__uckn-knowledge__contribute_pattern \
  --pattern-title "CI Framework Development Methodology" \
  --pattern-type "best_practice" \
  --pattern-description "Integration-First BDD/TDD Hybrid for meta-tooling" \
  --technologies ["ci-cd", "testing", "taskmaster", "meta-tooling"]

# Search for methodology patterns when restarting sessions
mcp__uckn-knowledge__search_patterns \
  --query "ci framework development methodology" \
  --pattern-type "best_practice"
```

### **Local CLAUDE.md for Development Context**
Create `.claude/CLAUDE.md` in project root with methodology reminders:

```markdown
# CI Framework Development Context

## 🔄 METHODOLOGY REMINDER
When working on CI Framework tasks, ALWAYS follow the Integration-First BDD/TDD Hybrid methodology.

## 📋 BEFORE STARTING ANY TASK:
1. Check TaskMaster for complete methodology context
2. Read the task's embedded methodology_step description
3. Follow the 9-step development cycle strictly
4. Validate ALL gates before proceeding

## 🎯 KEY PRINCIPLES:
- Integration testing more critical than unit testing
- Test against real projects (hb-strategy-sandbox, cheap-llm)
- Performance benchmarking with every change
- ALL gates must pass before next subtask

## 📂 TARGET PROJECTS for integration testing:
- Primary: /home/memento/ClaudeCode/Project/hb-strategy-sandbox/worktrees/feat-workspace-phase2
- Secondary: /home/memento/ClaudeCode/Servers/cheap-llm/worktrees/feat-phase1
- Additional: /home/memento/ClaudeCode/Servers/claude-code-knowledge-framework/worktrees/feat-task-3

## 🚨 CRITICAL: NO SHORTCUTS
Every subtask must complete all 9 methodology steps and pass all gates.
```

---

## 🔄 **SESSION RESTART PROCEDURE**

### **When Restarting Development Session**
1. **Read this methodology document** - `ai_docs/development-methodology.md`
2. **Check TaskMaster current task** - get complete context with embedded methodology
3. **Review local CLAUDE.md** - methodology reminders and project paths
4. **Query UCKN for patterns** - retrieve methodology patterns if contributed
5. **Validate current state** - ensure last completed subtask passed all gates
6. **Continue with strict methodology** - follow embedded task instructions

### **Context Recovery Commands**
```bash
# Get current TaskMaster state
mcp__task-master-ai__get_tasks --projectRoot="." --status="in-progress"

# Get next task with methodology context
mcp__task-master-ai__next_task --projectRoot="."

# Search UCKN for methodology patterns
mcp__uckn-knowledge__search_patterns --query="ci framework methodology"

# Read local methodology reminders
read .claude/CLAUDE.md
```

---

## 🎯 **SUCCESS CRITERIA FOR METHODOLOGY ADOPTION**

### **Immediate Success Indicators**
- [ ] TaskMaster tasks contain complete methodology context
- [ ] Each subtask has explicit gate requirements
- [ ] Target project paths documented in tasks
- [ ] Performance baselines established and documented

### **Ongoing Success Indicators**
- [ ] 100% gate passage rate before proceeding to next subtasks
- [ ] Zero "big bang" integration issues
- [ ] Consistent development velocity across sessions
- [ ] Real-world validation with every component

### **Long-term Success Indicators**
- [ ] Framework components production-ready upon completion
- [ ] No technical debt accumulation
- [ ] Performance maintained or improved throughout development
- [ ] Seamless integration across all target projects

---

## 🚨 **CRITICAL REMINDERS**

### **Never Skip Steps**
The 9-step methodology must be followed completely for every subtask. No exceptions.

### **Real Projects Are the Test**
Unit tests are necessary but not sufficient. Integration with real projects is the validation that matters.

### **Performance First**
Benchmark with every change. CI speed directly impacts developer productivity.

### **All Gates Must Pass**
Do not proceed to next subtask until ALL gates have passed. Fix issues immediately.

---

**This methodology ensures consistent, high-quality development that survives session restarts and maintains development velocity throughout the entire PRD implementation.**