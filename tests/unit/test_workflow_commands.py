#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for WorkflowCommandsConfig.
Tests the centralized workflow commands configuration.
"""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch

from config.settings import config
from config.workflow_commands import WorkflowCommandsConfig


@pytest.fixture
def temp_base_path(tmp_path):
    """Create a temporary base path for testing."""
    # Create necessary directory structure
    (tmp_path / "workflow_scripts").mkdir()
    for step in range(1, 9):
        (tmp_path / "workflow_scripts" / f"step{step}").mkdir()
    
    (tmp_path / "projets_extraits").mkdir()
    (tmp_path / "logs").mkdir()
    
    # Create virtual environment directories
    (tmp_path / "transnet_env" / "bin").mkdir(parents=True)
    (tmp_path / "audio_env" / "bin").mkdir(parents=True)
    (tmp_path / "tracking_env" / "bin").mkdir(parents=True)
    (tmp_path / "tracking_env_slim" / "bin").mkdir(parents=True)
    
    return tmp_path


class TestWorkflowCommandsConfigInitialization:
    """Test WorkflowCommandsConfig initialization."""
    
    def test_init_with_default_path(self):
        """Test initialization with default path."""
        commands = WorkflowCommandsConfig()
        
        assert commands.base_path is not None
        assert commands.logs_base_dir == commands.base_path / "logs"
    
    def test_init_with_custom_path(self, temp_base_path):
        """Test initialization with custom base path."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        assert commands.base_path == temp_base_path
        assert commands.logs_base_dir == temp_base_path / "logs"
    
    def test_init_with_hf_token(self, temp_base_path):
        """Test initialization with HuggingFace token."""
        token = "test_token_123"
        commands = WorkflowCommandsConfig(base_path=temp_base_path, hf_token=token)
        
        assert commands.hf_token == token
        
        # Check that token is in STEP4 command when the Pyannote runner is active
        step4_cmd = commands.get_step_command('STEP4')
        cmd_str = ' '.join(step4_cmd)
        if 'run_audio_analysis.py' in cmd_str:
            assert '--hf_auth_token' in step4_cmd
            assert token in step4_cmd
    
    def test_log_directories_created(self, temp_base_path):
        """Test that log directories are created."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        for step in range(1, 9):
            log_dir = commands.logs_base_dir / f"step{step}"
            assert log_dir.exists()


class TestConfigurationRetrieval:
    """Test configuration retrieval methods."""
    
    def test_get_config_returns_all_steps(self, temp_base_path):
        """Test that get_config returns all 8 steps."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        config = commands.get_config()
        
        assert len(config) == 8
        assert all(f"STEP{i}" in config for i in range(1, 9))
    
    def test_get_step_config_valid_key(self, temp_base_path):
        """Test getting config for valid step key."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        step1_config = commands.get_step_config('STEP1')
        
        assert step1_config is not None
        assert 'display_name' in step1_config
        assert 'cmd' in step1_config
        assert 'cwd' in step1_config
    
    def test_get_step_config_invalid_key(self, temp_base_path):
        """Test getting config for invalid step key."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        config = commands.get_step_config('INVALID_STEP')
        
        assert config is None
    
    def test_validate_step_key(self, temp_base_path):
        """Test step key validation."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        assert commands.validate_step_key('STEP1') is True
        assert commands.validate_step_key('STEP7') is True
        assert commands.validate_step_key('STEP8') is True
        assert commands.validate_step_key('INVALID') is False
    
    def test_get_all_step_keys(self, temp_base_path):
        """Test getting all step keys."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        keys = commands.get_all_step_keys()
        
        assert len(keys) == 8
        assert all(f"STEP{i}" in keys for i in range(1, 9))


class TestStepSpecificMethods:
    """Test step-specific getter methods."""
    
    def test_get_step_display_name(self, temp_base_path):
        """Test getting step display name."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        name = commands.get_step_display_name('STEP1')
        assert name == "1. Extraction des archives"
        
        name = commands.get_step_display_name('STEP5')
        assert name == "5. Analyse du tracking"
    
    def test_get_step_display_name_invalid(self, temp_base_path):
        """Test getting display name for invalid step."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        name = commands.get_step_display_name('INVALID')
        assert name is None
    
    def test_get_step_command(self, temp_base_path):
        """Test getting step command."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        cmd = commands.get_step_command('STEP1')
        
        assert isinstance(cmd, list)
        assert len(cmd) > 0
        assert 'extract_archives.py' in ' '.join(cmd)
    
    def test_get_step_cwd(self, temp_base_path):
        """Test getting step working directory."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        cwd = commands.get_step_cwd('STEP2')
        
        assert cwd is not None
        assert 'projets_extraits' in cwd


class TestStepConfigurations:
    """Test individual step configurations."""
    
    def test_step1_config_structure(self, temp_base_path):
        """Test STEP1 configuration structure."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        config = commands.get_step_config('STEP1')
        
        assert config['display_name'].startswith('1.')
        assert 'extract_archives.py' in ' '.join(config['cmd'])
        assert 'specific_logs' in config
        assert 'progress_patterns' in config
    
    def test_step3_uses_transnet_env(self, temp_base_path):
        """Test that STEP3 uses transnet_env."""
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', False), \
             patch.object(config, 'USE_OPENCV5_STEP3', False, create=True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP3')
            cmd_str = ' '.join(cmd)
            
            assert 'transnet_env' in cmd_str
            assert 'run_transnet.py' in cmd_str
    
    def test_step3_uses_tpu_when_accelerated(self, temp_base_path):
        """Test that STEP3 uses Coral TPU script when accelerated."""
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', True), \
             patch.object(config, 'STEP3_ENABLE_CORAL_TPU', True, create=True), \
             patch.object(config, 'USE_OPENCV5_STEP3', False, create=True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP3')
            cmd_str = ' '.join(cmd)
            
            assert 'coral_env' in cmd_str
            assert 'run_scene_detect_tpu.py' in cmd_str
    
    def test_step3_uses_transnet_when_tpu_disabled_for_step(self, temp_base_path):
        """Test that STEP3 uses transnet_env when global TPU is enabled but step TPU is disabled."""
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', True), \
             patch.object(config, 'STEP3_ENABLE_CORAL_TPU', False, create=True), \
             patch.object(config, 'USE_OPENCV5_STEP3', False, create=True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP3')
            cmd_str = ' '.join(cmd)
            
            assert 'transnet_env' in cmd_str
            assert 'run_transnet.py' in cmd_str

    def test_step3_uses_opencv5(self, temp_base_path):
        """Test that STEP3 uses OpenCV 5.0 when enabled."""
        with patch.object(config, 'USE_OPENCV5_STEP3', True, create=True):
            # Create the virtual environment directory structure for CV5
            (temp_base_path / "transnet_cv5_env" / "bin").mkdir(parents=True, exist_ok=True)
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP3')
            cmd_str = ' '.join(cmd)
            
            assert 'transnet_cv5_env' in cmd_str
            assert 'run_transnet_cv5.py' in cmd_str

    
    def test_step4_uses_audio_env(self, temp_base_path):
        """Test that STEP4 uses audio_env."""
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', False):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP4')
            cmd_str = ' '.join(cmd)
            
            assert 'audio_env' in cmd_str
            assert (
                ('run_audio_analysis.py' in cmd_str)
                or ('run_audio_analysis_lemonfox.py' in cmd_str)
                or ('run_audio_analysis_deepinfra.py' in cmd_str)
            )

    def test_step4_uses_tpu_when_accelerated(self, temp_base_path):
        """Test that STEP4 uses Coral TPU script when accelerated."""
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP4')
            cmd_str = ' '.join(cmd)
            
            assert 'coral_env' in cmd_str
            assert 'run_audio_diarization_tpu.py' in cmd_str
    
    def test_step4_uses_audio_when_tpu_disabled_for_step(self, temp_base_path):
        """Test that STEP4 uses audio_env when global TPU is enabled but step TPU is disabled."""
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', True), \
             patch.object(config, 'STEP4_ENABLE_CORAL_TPU', False, create=True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP4')
            cmd_str = ' '.join(cmd)
            
            assert 'audio_env' in cmd_str
            assert (
                ('run_audio_analysis.py' in cmd_str)
                or ('run_audio_analysis_lemonfox.py' in cmd_str)
                or ('run_audio_analysis_deepinfra.py' in cmd_str)
            )
    
    def test_step5_uses_tracking_env_slim(self, temp_base_path):
        """Test that STEP5 uses tracking_env_slim."""
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', False), \
             patch.object(config, 'USE_OPENCV5_STEP5', False, create=True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP5')
            cmd_str = ' '.join(cmd)
            
            assert 'tracking_env_slim' in cmd_str
            assert 'run_tracking_manager.py' in cmd_str
 
    def test_step5_uses_tpu_when_accelerated(self, temp_base_path):
        """Test that STEP5 uses Coral TPU script when accelerated."""
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', True), \
             patch.object(config, 'STEP5_ENABLE_CORAL_TPU', True, create=True), \
             patch.object(config, 'USE_OPENCV5_STEP5', False, create=True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP5')
            cmd_str = ' '.join(cmd)
            
            assert 'coral_env' in cmd_str
            assert 'run_tracking_tpu.py' in cmd_str
 
    def test_step5_uses_tracking_when_tpu_disabled_for_step(self, temp_base_path):
        """Test that STEP5 uses tracking_env_slim when global TPU is enabled but step TPU is disabled."""
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', True), \
             patch.object(config, 'STEP5_ENABLE_CORAL_TPU', False, create=True), \
             patch.object(config, 'USE_OPENCV5_STEP5', False, create=True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP5')
            cmd_str = ' '.join(cmd)
            
            assert 'tracking_env_slim' in cmd_str
            assert 'run_tracking_manager.py' in cmd_str

    def test_step5_uses_opencv5(self, temp_base_path):
        """Test that STEP5 uses OpenCV 5.0 when enabled."""
        with patch.object(config, 'USE_OPENCV5_STEP5', True, create=True):
            # Create the virtual environment directory structure for CV5
            (temp_base_path / "tracking_cv5_env" / "bin").mkdir(parents=True, exist_ok=True)
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            
            cmd = commands.get_step_command('STEP5')
            cmd_str = ' '.join(cmd)
            
            assert 'tracking_cv5_env' in cmd_str
            assert 'run_tracking_cv5.py' in cmd_str

    
    def test_step5_has_post_completion_message(self, temp_base_path):
        """Test that STEP5 has post_completion_message_ui."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        config = commands.get_step_config('STEP5')
        
        assert 'post_completion_message_ui' in config
        assert 'tracking' in config['post_completion_message_ui'].lower()
    
    def test_step7_has_post_completion_message(self, temp_base_path):
        """Test that STEP7 has post_completion_message_ui."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        config = commands.get_step_config('STEP7')
        
        assert 'post_completion_message_ui' in config


class TestHFTokenManagement:
    """Test HuggingFace token management."""
    
    def test_init_without_token(self, temp_base_path):
        """Test initialization without HF token."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        cmd = commands.get_step_command('STEP4')
        cmd_str = ' '.join(cmd)
        
        # Pyannote runner requires a token (only appended when hf_token is provided).
        if 'run_audio_analysis.py' in cmd_str:
            assert '--hf_auth_token' not in cmd_str
    
    def test_init_with_token(self, temp_base_path):
        """Test initialization with HF token."""
        token = "hf_test123"
        commands = WorkflowCommandsConfig(base_path=temp_base_path, hf_token=token)
        
        cmd = commands.get_step_command('STEP4')

        cmd_str = ' '.join(cmd)
        if 'run_audio_analysis.py' in cmd_str:
            assert '--hf_auth_token' in cmd
            assert token in cmd
    
    def test_update_hf_token(self, temp_base_path):
        """Test updating HF token after initialization."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        cmd_before = commands.get_step_command('STEP4')
        cmd_before_str = ' '.join(cmd_before)
        if 'run_audio_analysis.py' in cmd_before_str:
            assert '--hf_auth_token' not in cmd_before_str
        
        # Update token
        new_token = "hf_newtoken456"
        commands.update_hf_token(new_token)
        
        cmd_after = commands.get_step_command('STEP4')
        cmd_after_str = ' '.join(cmd_after)
        if 'run_audio_analysis.py' in cmd_after_str:
            assert '--hf_auth_token' in cmd_after
            assert new_token in cmd_after


class TestProgressPatterns:
    """Test progress patterns in configurations."""
    
    def test_all_steps_have_progress_patterns(self, temp_base_path):
        """Test that all steps have progress patterns defined."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        for step_key in commands.get_all_step_keys():
            config = commands.get_step_config(step_key)
            assert 'progress_patterns' in config
            assert isinstance(config['progress_patterns'], dict)
    
    def test_step1_progress_patterns(self, temp_base_path):
        """Test STEP1 progress patterns."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        patterns = commands.get_step_config('STEP1')['progress_patterns']
        
        assert 'total' in patterns
        assert 'current_success_line_pattern' in patterns
    
    def test_step2_progress_patterns(self, temp_base_path):
        """Test STEP2 progress patterns."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        patterns = commands.get_step_config('STEP2')['progress_patterns']
        
        assert 'total' in patterns
        assert 'current' in patterns


class TestLogConfiguration:
    """Test log configuration for steps."""
    
    def test_all_steps_have_log_config(self, temp_base_path):
        """Test that all steps have log configuration."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        for step_key in commands.get_all_step_keys():
            config = commands.get_step_config(step_key)
            assert 'specific_logs' in config
            assert isinstance(config['specific_logs'], list)
            assert len(config['specific_logs']) > 0
    
    def test_step5_has_multiple_logs(self, temp_base_path):
        """Test that STEP5 has multiple log configurations."""
        # Test default/non-accelerated mode
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', False), \
             patch.object(config, 'USE_OPENCV5_STEP5', False, create=True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            logs = commands.get_step_config('STEP5')['specific_logs']
            assert len(logs) >= 3
            log_names = [log['name'] for log in logs]
            assert any('Manager' in name for name in log_names)
            assert any('CPU' in name for name in log_names)
            assert any('GPU' in name for name in log_names)

        # Test accelerated mode (TPU)
        with patch.object(config, 'ENABLE_CORAL_TPU_ACCELERATION', True), \
             patch.object(config, 'STEP5_ENABLE_CORAL_TPU', True, create=True), \
             patch.object(config, 'USE_OPENCV5_STEP5', False, create=True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            logs = commands.get_step_config('STEP5')['specific_logs']
            assert len(logs) == 1
            assert logs[0]['name'] == 'Log Tracking TPU'

    def test_step5_opencv5_logs(self, temp_base_path):
        """Test that STEP5 has OpenCV 5.0 specific logs when enabled."""
        with patch.object(config, 'USE_OPENCV5_STEP5', True, create=True):
            commands = WorkflowCommandsConfig(base_path=temp_base_path)
            logs = commands.get_step_config('STEP5')['specific_logs']
            assert len(logs) == 2
            log_names = [log['name'] for log in logs]
            assert 'Log Tracking CV5' in log_names
            assert 'Log Worker CV5' in log_names




class TestRepr:
    """Test string representation."""
    
    def test_repr(self, temp_base_path):
        """Test __repr__ method."""
        commands = WorkflowCommandsConfig(base_path=temp_base_path)
        
        repr_str = repr(commands)
        
        assert 'WorkflowCommandsConfig' in repr_str
        assert 'base_path' in repr_str
        assert 'steps=8' in repr_str
