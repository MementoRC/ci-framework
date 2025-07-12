"""
Integration Test #2: cheap-llm Compatibility

Testing the Quality Gates Action against the second integration target
to ensure compatibility with different project patterns and configurations.
"""

import pytest
from pathlib import Path
from framework.actions.quality_gates import QualityGatesAction


class TestCheapLLMIntegration:
    """
    Integration tests for cheap-llm project compatibility
    
    These tests verify that the Quality Gates Action works with
    different project configurations and patterns beyond hb-strategy-sandbox.
    """
    
    @pytest.fixture
    def cheap_llm_path(self):
        """Path to cheap-llm project"""
        return Path("/home/memento/ClaudeCode/Servers/cheap-llm/worktrees/feat-phase1")
    
    @pytest.fixture
    def quality_gates_action(self):
        """Quality Gates Action instance"""
        return QualityGatesAction()
    
    def test_cheap_llm_project_exists(self, cheap_llm_path):
        """Verify the integration target project exists"""
        if not cheap_llm_path.exists():
            pytest.skip("cheap-llm project not available for integration testing")
        
        assert cheap_llm_path.is_dir()
        assert (cheap_llm_path / "pyproject.toml").exists()
    
    def test_package_manager_detection(self, quality_gates_action, cheap_llm_path):
        """Test package manager detection with cheap-llm"""
        if not cheap_llm_path.exists():
            pytest.skip("cheap-llm project not available")
        
        manager = quality_gates_action.detect_package_manager(cheap_llm_path)
        
        assert manager.name == "pixi", f"Expected pixi, got {manager.name}"
        assert manager.environment_support is True
        assert "pyproject.toml" in manager.detected_files
    
    def test_pattern_detection_differences(self, quality_gates_action, cheap_llm_path):
        """Test project pattern detection differences from hb-strategy-sandbox"""
        if not cheap_llm_path.exists():
            pytest.skip("cheap-llm project not available")
        
        patterns = quality_gates_action._detect_project_patterns(cheap_llm_path)
        
        assert patterns["package_manager"] == "pixi"
        
        # cheap-llm should have different characteristics than hb-strategy-sandbox
        if "platforms" in patterns:
            platforms = patterns["platforms"]
            # cheap-llm is CI-optimized, likely linux-64 only
            assert isinstance(platforms, list)
            assert "linux-64" in platforms
        
        # cheap-llm uses pyright instead of mypy
        if "type_checker" in patterns:
            type_checker = patterns["type_checker"]
            assert type_checker in ["pyright", "mypy"], f"Unexpected type checker: {type_checker}"
    
    def test_dry_run_compatibility_check(self, quality_gates_action, cheap_llm_path):
        """Test dry-run compatibility check with cheap-llm"""
        if not cheap_llm_path.exists():
            pytest.skip("cheap-llm project not available")
        
        # Test all tiers in dry-run mode
        for tier in ["essential", "extended", "full"]:
            result = quality_gates_action.execute_tier(
                project_dir=cheap_llm_path,
                tier=tier,
                dry_run=True
            )
            
            assert result.success is True, f"Dry run failed for tier {tier}"
            assert result.compatibility_check is True
            assert result.tier == tier
    
    def test_configuration_structure_analysis(self, quality_gates_action, cheap_llm_path):
        """Analyze cheap-llm configuration structure"""
        if not cheap_llm_path.exists():
            pytest.skip("cheap-llm project not available")
        
        config = quality_gates_action._load_project_config(cheap_llm_path)
        
        # Should have pixi configuration
        assert "tool" in config
        assert "pixi" in config["tool"]
        
        pixi_config = config["tool"]["pixi"]
        
        # Analyze environment structure
        if "environments" in pixi_config:
            envs = pixi_config["environments"]
            env_names = list(envs.keys())
            
            # Document environment structure
            print(f"cheap-llm environments: {env_names}")
            
            # Should have quality-related environments
            quality_envs = [env for env in env_names if "quality" in env]
            assert len(quality_envs) > 0, f"No quality environments found in {env_names}"
        
        # Analyze tasks structure
        if "tasks" in pixi_config:
            tasks = pixi_config["tasks"]
            task_names = list(tasks.keys())
            
            # Document task structure
            print(f"cheap-llm tasks: {task_names}")
            
            # Should have essential quality tasks
            essential_tasks = ["test", "lint", "typecheck"]
            available_essential = [task for task in essential_tasks if task in task_names]
            assert len(available_essential) > 0, f"No essential tasks found in {task_names}"
    
    def test_project_size_comparison(self, cheap_llm_path):
        """Compare project size to establish different complexity baseline"""
        if not cheap_llm_path.exists():
            pytest.skip("cheap-llm project not available")
        
        # Analyze project size
        metrics = {
            "python_files": len(list(cheap_llm_path.glob("**/*.py"))),
            "total_files": len(list(cheap_llm_path.glob("**/*"))),
            "directories": len([d for d in cheap_llm_path.rglob("*") if d.is_dir()])
        }
        
        print(f"cheap-llm project metrics: {metrics}")
        
        # cheap-llm should be smaller/simpler than hb-strategy-sandbox
        # This gives us a different complexity target for testing
        assert metrics["python_files"] >= 0
        
        # Document for comparison with hb-strategy-sandbox baseline
        return metrics
    
    def test_mcp_server_specific_patterns(self, cheap_llm_path):
        """Test MCP server specific patterns in cheap-llm"""
        if not cheap_llm_path.exists():
            pytest.skip("cheap-llm project not available")
        
        # Look for MCP server patterns
        mcp_indicators = []
        
        # Check for common MCP patterns
        potential_mcp_files = [
            "server.py",
            "mcp_server.py", 
            "__main__.py",
            "main.py"
        ]
        
        for file_name in potential_mcp_files:
            if (cheap_llm_path / file_name).exists():
                mcp_indicators.append(file_name)
        
        # Check for MCP in any Python file
        python_files = list(cheap_llm_path.glob("**/*.py"))
        mcp_content_files = []
        
        for py_file in python_files[:10]:  # Sample first 10 files
            try:
                content = py_file.read_text()
                if "mcp" in content.lower() or "model context protocol" in content.lower():
                    mcp_content_files.append(py_file.name)
            except:
                pass
        
        print(f"MCP indicators in cheap-llm: files={mcp_indicators}, content={mcp_content_files}")
        
        # MCP servers have different quality requirements than general applications
        # They need to be more focused and have specific patterns
        
        return {
            "mcp_file_indicators": mcp_indicators,
            "mcp_content_indicators": mcp_content_files
        }


class TestMultiProjectCompatibility:
    """
    Test compatibility patterns across both integration projects
    
    This ensures the Quality Gates Action can handle diverse project types
    """
    
    @pytest.fixture
    def hb_project_path(self):
        return Path("/home/memento/ClaudeCode/Project/hb-strategy-sandbox/worktrees/feat-workspace-phase2")
    
    @pytest.fixture
    def cheap_llm_path(self):
        return Path("/home/memento/ClaudeCode/Servers/cheap-llm/worktrees/feat-phase1")
    
    @pytest.fixture
    def quality_gates_action(self):
        return QualityGatesAction()
    
    def test_consistent_package_manager_detection(self, quality_gates_action, hb_project_path, cheap_llm_path):
        """Test that package manager detection is consistent across projects"""
        projects = []
        
        if hb_project_path.exists():
            hb_manager = quality_gates_action.detect_package_manager(hb_project_path)
            projects.append(("hb-strategy-sandbox", hb_manager))
        
        if cheap_llm_path.exists():
            cheap_llm_manager = quality_gates_action.detect_package_manager(cheap_llm_path)
            projects.append(("cheap-llm", cheap_llm_manager))
        
        if len(projects) < 2:
            pytest.skip("Need at least 2 projects for multi-project testing")
        
        # Both should detect pixi (based on our analysis)
        for project_name, manager in projects:
            assert manager.name == "pixi", f"{project_name} should use pixi"
            assert manager.environment_support is True
    
    def test_tier_execution_consistency(self, quality_gates_action, hb_project_path, cheap_llm_path):
        """Test that tier execution is consistent across different projects"""
        projects = []
        
        if hb_project_path.exists():
            projects.append(("hb-strategy-sandbox", hb_project_path))
        
        if cheap_llm_path.exists():
            projects.append(("cheap-llm", cheap_llm_path))
        
        if len(projects) < 2:
            pytest.skip("Need at least 2 projects for multi-project testing")
        
        # Test dry-run consistency across projects
        for project_name, project_path in projects:
            for tier in ["essential", "extended", "full"]:
                result = quality_gates_action.execute_tier(
                    project_dir=project_path,
                    tier=tier,
                    dry_run=True
                )
                
                assert result.success is True, f"{project_name} tier {tier} should succeed in dry-run"
                assert result.compatibility_check is True
                assert result.tier == tier
    
    def test_configuration_adaptation(self, quality_gates_action, hb_project_path, cheap_llm_path):
        """Test that configuration adapts appropriately to different projects"""
        projects = []
        
        if hb_project_path.exists():
            hb_patterns = quality_gates_action._detect_project_patterns(hb_project_path)
            projects.append(("hb-strategy-sandbox", hb_patterns))
        
        if cheap_llm_path.exists():
            cheap_llm_patterns = quality_gates_action._detect_project_patterns(cheap_llm_path)
            projects.append(("cheap-llm", cheap_llm_patterns))
        
        if len(projects) < 2:
            pytest.skip("Need at least 2 projects for multi-project testing")
        
        # Compare patterns between projects
        print("Project pattern comparison:")
        for project_name, patterns in projects:
            print(f"  {project_name}: {patterns}")
        
        # Both should detect pixi but may have different characteristics
        for project_name, patterns in projects:
            assert patterns["package_manager"] == "pixi"
        
        # Document differences for adaptation logic
        if len(projects) == 2:
            hb_patterns = projects[0][1] if projects[0][0] == "hb-strategy-sandbox" else projects[1][1]
            cheap_llm_patterns = projects[1][1] if projects[1][0] == "cheap-llm" else projects[0][1]
            
            differences = {}
            all_keys = set(hb_patterns.keys()) | set(cheap_llm_patterns.keys())
            
            for key in all_keys:
                hb_val = hb_patterns.get(key)
                cheap_llm_val = cheap_llm_patterns.get(key)
                if hb_val != cheap_llm_val:
                    differences[key] = {
                        "hb-strategy-sandbox": hb_val,
                        "cheap-llm": cheap_llm_val
                    }
            
            print(f"Pattern differences: {differences}")
            
            # Quality Gates Action should handle these differences gracefully
            return differences


class TestSecondaryIntegrationTargets:
    """
    Test other secondary integration targets for broader compatibility
    """
    
    def test_available_secondary_targets(self):
        """Document which secondary integration targets are available"""
        secondary_targets = [
            "/home/memento/ClaudeCode/Servers/claude-code-knowledge-framework/worktrees/feat-task-3",
            "/home/memento/ClaudeCode/Servers/git/worktrees/feat-llm-compliance",
            "/home/memento/ClaudeCode/Servers/aider/development",
            "/home/memento/ClaudeCode/Servers/pytest-analyzer/worktrees/feat-security-hardening",
            "/home/memento/ClaudeCode/candles-feed/hummingbot/sub-packages/candles-feed"
        ]
        
        available_targets = []
        for target_path in secondary_targets:
            path = Path(target_path)
            if path.exists() and path.is_dir():
                available_targets.append(target_path)
        
        print(f"Available secondary integration targets: {available_targets}")
        
        # Document for future integration testing phases
        return available_targets
    
    @pytest.mark.parametrize("target_path", [
        "/home/memento/ClaudeCode/Servers/claude-code-knowledge-framework/worktrees/feat-task-3",
        "/home/memento/ClaudeCode/Servers/pytest-analyzer/worktrees/feat-security-hardening"
    ])
    def test_secondary_target_basic_compatibility(self, target_path):
        """Basic compatibility check for secondary targets"""
        project_path = Path(target_path)
        
        if not project_path.exists():
            pytest.skip(f"Secondary target not available: {target_path}")
        
        quality_gates_action = QualityGatesAction()
        
        # Basic package manager detection
        manager = quality_gates_action.detect_package_manager(project_path)
        assert manager.name in ["pixi", "poetry", "hatch", "pip"]
        
        # Basic pattern detection
        patterns = quality_gates_action._detect_project_patterns(project_path)
        assert "package_manager" in patterns
        
        # Basic dry-run test
        result = quality_gates_action.execute_tier(
            project_dir=project_path,
            tier="essential",
            dry_run=True
        )
        assert result.compatibility_check is True