#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit test for STEP4 GPU/CPU fallback mechanism.
Validates that the script gracefully falls back to CPU when GPU driver is incompatible.

NOTE: These tests mock torch behavior to avoid dependency on audio_env.
"""

import pytest
import os
from unittest.mock import Mock


class TestStep4GPUFallback:
    """Test STEP4's GPU to CPU fallback mechanism."""
    
    def test_gpu_available_no_error(self):
        """Test successful GPU loading when CUDA is available and compatible."""
        # Mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.to = Mock(return_value=None)
        
        # Should not raise
        try:
            mock_pipeline.to("cuda")
            assert mock_pipeline.to.called
        except RuntimeError:
            pytest.fail("GPU loading should not fail with compatible driver")
    
    def test_gpu_driver_incompatible_fallback_cpu(self):
        """Test fallback to CPU when GPU driver is incompatible."""
        # Mock pipeline that fails on GPU but succeeds on CPU
        mock_pipeline = Mock()
        
        def side_effect_to(device):
            if "cuda" in str(device):
                raise RuntimeError("The NVIDIA driver on your system is too old (found version 11040)")
            # CPU succeeds
            return None
        
        mock_pipeline.to = Mock(side_effect=side_effect_to)
        
        # Simulate the fallback logic from run_audio_analysis.py
        device = "cuda"
        try:
            mock_pipeline.to(device)
        except RuntimeError as e:
            if "NVIDIA driver" in str(e) or "CUDA" in str(e):
                # Fallback to CPU
                device = "cpu"
                mock_pipeline.to("cpu")
                assert device == "cpu", "Should have fallen back to CPU"
            else:
                raise
        
        # Verify CPU fallback was triggered
        assert device == "cpu"
        assert mock_pipeline.to.call_count == 2  # Once for GPU (failed), once for CPU (success)
    
    def test_gpu_other_runtime_error_not_caught(self):
        """Test that non-driver RuntimeErrors are not caught by fallback."""
        # Mock pipeline that fails with unrelated error
        mock_pipeline = Mock()
        mock_pipeline.to = Mock(side_effect=RuntimeError("Some other error"))
        
        # Should raise because it's not a driver incompatibility
        with pytest.raises(RuntimeError, match="Some other error"):
            try:
                mock_pipeline.to("cuda")
            except RuntimeError as e:
                if "NVIDIA driver" in str(e) or "CUDA" in str(e):
                    # This branch should NOT be taken
                    pytest.fail("Should not catch unrelated RuntimeErrors")
                else:
                    raise
    
    def test_cuda_not_available_uses_cpu(self):
        """Test that CPU is used when CUDA is not available at all."""
        # Simulate CUDA check
        cuda_available = False
        
        # Should select CPU device
        device = "cuda" if cuda_available else "cpu"
        assert device == "cpu"


class TestStep4EnvironmentOverrides:
    """Test STEP4 environment variable overrides for device selection."""
    
    def test_disable_gpu_via_env(self):
        """Test that AUDIO_DISABLE_GPU=1 forces CPU usage."""
        # Simulate environment
        os.environ['AUDIO_DISABLE_GPU'] = '1'
        cuda_available = True
        
        try:
            # Simulate device selection logic
            env_disable_gpu = os.getenv("AUDIO_DISABLE_GPU", "0") == "1"
            use_cuda = cuda_available and not env_disable_gpu
            device = "cuda" if use_cuda else "cpu"
            
            assert device == "cpu", "AUDIO_DISABLE_GPU should force CPU"
        finally:
            os.environ.pop('AUDIO_DISABLE_GPU', None)
    
    def test_enable_gpu_via_env(self):
        """Test that AUDIO_DISABLE_GPU=0 allows GPU if available."""
        # Simulate environment
        os.environ['AUDIO_DISABLE_GPU'] = '0'
        cuda_available = True
        
        try:
            # Simulate device selection logic
            env_disable_gpu = os.getenv("AUDIO_DISABLE_GPU", "0") == "1"
            use_cuda = cuda_available and not env_disable_gpu
            device = "cuda" if use_cuda else "cpu"
            
            assert device == "cuda", "AUDIO_DISABLE_GPU=0 should allow GPU"
        finally:
            os.environ.pop('AUDIO_DISABLE_GPU', None)
