Feature: Python CI Workflow Template
  As a Python developer
  I want a comprehensive CI workflow template
  So that I can ensure code quality with optimal performance

  Background:
    Given I have a Python project with pixi package manager
    And I have the CI workflow template installed
    And I have proper GitHub repository permissions

  Scenario: Quick checks complete under 2 minutes for small changes
    Given I make a small change to a single Python file
    When I push the commit to GitHub
    Then the quick checks stage should complete within 2 minutes
    And the quick checks should include critical lint violations (F,E9)
    And the quick checks should validate basic syntax
    And the result should be reported via GitHub Status API

  Scenario: Comprehensive tests run only when Python files change
    Given I have change detection configured
    When I modify only documentation files
    Then the comprehensive test stage should be skipped
    And the workflow should complete with "success" status
    When I modify Python source files
    Then the comprehensive test stage should execute
    And all tests in the test suite should run

  Scenario: Security audit catches known vulnerabilities
    Given I have security scanning configured
    When I introduce a dependency with known vulnerabilities
    Then the security audit stage should fail
    And the failure should be reported with specific vulnerability details
    And the SARIF report should be uploaded to GitHub Security tab
    When I have no vulnerable dependencies
    Then the security audit stage should pass

  Scenario: Performance benchmarks detect 10%+ regressions
    Given I have performance benchmarking configured
    When I introduce code changes that slow performance by >10%
    Then the performance check stage should fail
    And the regression should be reported with specific metrics
    And comparison to baseline should be shown
    When performance is within acceptable limits
    Then the performance check stage should pass

  Scenario: Summary reports consolidate all stage results
    Given all CI stages have completed
    When I view the summary report
    Then it should show results from all 6 stages:
      | Stage | Status |
      | change-detection | success |
      | quick-checks | success |
      | comprehensive-tests | success |
      | security-audit | success |
      | performance-check | success |
      | summary | success |
    And the summary should include total execution time
    And the summary should include artifact links

  Scenario: Matrix testing covers Python 3.10-3.12 on ubuntu/macos
    Given I have matrix testing configured
    When the CI workflow runs
    Then it should test Python 3.10 on ubuntu-latest
    And it should test Python 3.10 on macos-latest
    And it should test Python 3.11 on ubuntu-latest
    And it should test Python 3.11 on macos-latest
    And it should test Python 3.12 on ubuntu-latest
    And it should test Python 3.12 on macos-latest
    And all matrix combinations should use consistent PIXI_VERSION

  Scenario: Change detection correctly identifies affected modules
    Given I have change detection configured
    When I modify files in the "framework/actions/" directory
    Then the change detection should identify "actions" module as affected
    And should skip unrelated test modules
    When I modify test files only
    Then the change detection should run tests but skip security/performance
    When I modify pyproject.toml
    Then all stages should execute as dependencies may have changed

  Scenario: GitHub Status API shows real-time CI progress
    Given I have GitHub Status API integration configured
    When the CI workflow starts
    Then the status should show "pending" for all stages
    When a stage completes successfully
    Then the status should update to "success" for that stage
    When a stage fails
    Then the status should update to "failure" with error details
    And the final status should reflect overall pipeline result

  Scenario: Job skipping logic optimizes CI execution time
    Given I have intelligent job skipping configured
    When I make changes that don't affect tests
    Then test stages should be skipped
    And execution time should be <50% of full pipeline
    When I make changes affecting security
    Then security audit should run regardless of other changes
    When I modify performance-critical code
    Then performance benchmarks should always execute

  Scenario: Environment variable consistency across stages
    Given I have PIXI_VERSION environment variable configured
    When any CI stage executes
    Then it should use the same PIXI_VERSION across all jobs
    And the version should be compatible with all Python versions in matrix
    And environment setup should be consistent between stages

  Scenario: Artifact management between stages
    Given I have artifact management configured
    When the quick checks stage generates reports
    Then those reports should be available to summary stage
    When comprehensive tests generate coverage reports
    Then coverage data should be included in final summary
    When security audit generates SARIF reports
    Then SARIF data should be uploaded to GitHub Security tab
    And all artifacts should be consolidated in summary

  Scenario: Timeout enforcement prevents hanging jobs
    Given I have timeout enforcement configured
    When a stage runs longer than its timeout limit
    Then the stage should be terminated
    And the failure should be reported with timeout reason
    And subsequent stages should handle the failure gracefully
    And the overall workflow should fail fast

  Scenario: Parallel execution maximizes performance
    Given I have parallel execution configured
    When multiple independent stages can run simultaneously
    Then they should execute in parallel
    And total execution time should be minimized
    And resource usage should be optimized
    And stage dependencies should be respected

  Scenario: Error handling and recovery
    Given I have error handling configured
    When a transient failure occurs (network timeout)
    Then the stage should retry up to configured limit
    When a permanent failure occurs (syntax error)
    Then the workflow should fail fast without retries
    And error messages should be clear and actionable
    And logs should be preserved for debugging

  Scenario: Cross-project template compatibility
    Given I have the workflow template
    When I apply it to different Python project structures
    Then it should work without modifications for:
      | Project Type | Package Manager | Test Framework |
      | CLI Tool | pixi | pytest |
      | Web API | poetry | pytest |
      | Library | pip | unittest |
      | Data Science | conda | pytest |
    And all matrix combinations should succeed
    And performance should be acceptable across project types