#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for WorkflowService.
Tests the complete workflow execution with helper methods.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import time
import json

from services.workflow_service import WorkflowService
from services.filesystem_service import FilesystemService


class TestWorkflowServiceSTEP5Integration:
    """Integration tests for STEP5 (tracking) workflow."""
    
    def test_prepare_tracking_step_with_videos(self, tmp_path):
        """Test STEP5 preparation when videos are found."""
        # Create test video files without JSON
        projets_dir = tmp_path / "projets_extraits"
        project_dir = projets_dir / "test_project"
        project_dir.mkdir(parents=True)
        
        # Create test videos
        video1 = project_dir / "video1.mp4"
        video2 = project_dir / "video2.mov"
        video1.touch()
        video2.touch()
        
        # Should find both videos
        videos = WorkflowService.prepare_tracking_step(
            projets_dir,
            keyword="",
            subdir=""
        )
        
        assert videos is not None
        assert len(videos) == 2
        assert any('video1.mp4' in v for v in videos)
        assert any('video2.mov' in v for v in videos)
    
    def test_prepare_tracking_step_no_videos(self, tmp_path):
        """Test STEP5 preparation when no videos need processing."""
        # Create test video with existing JSON
        projets_dir = tmp_path / "projets_extraits"
        project_dir = projets_dir / "test_project"
        project_dir.mkdir(parents=True)
        
        video = project_dir / "video.mp4"
        json_file = project_dir / "video.json"
        video.touch()
        json_file.write_text('{}')
        
        # Should return None (no videos to process)
        videos = WorkflowService.prepare_tracking_step(
            projets_dir,
            keyword="",
            subdir=""
        )
        
        assert videos is None
    
    def test_create_tracking_temp_file(self, tmp_path):
        """Test creation of temporary tracking JSON file."""
        videos = [
            str(tmp_path / "video1.mp4"),
            str(tmp_path / "video2.mp4")
        ]
        
        temp_file = WorkflowService.create_tracking_temp_file(videos)
        
        assert temp_file.exists()
        assert temp_file.suffix == '.json'
        assert 'tracking_videos_' in temp_file.name
        
        # Verify content - should be a JSON array, not an object
        with open(temp_file, 'r') as f:
            data = json.load(f)
        
        assert isinstance(data, list)
        assert len(data) == 2
        assert videos[0] in data
        assert videos[1] in data
        
        # Cleanup
        temp_file.unlink()
    
    def test_tracking_workflow_end_to_end(self, tmp_path):
        """Test complete STEP5 workflow from preparation to temp file creation."""
        # Setup
        projets_dir = tmp_path / "projets_extraits"
        project_dir = projets_dir / "Camille_project"
        project_dir.mkdir(parents=True)
        
        # Create multiple test videos
        for i in range(5):
            video = project_dir / f"camille_video_{i}.mp4"
            video.touch()
        
        # Step 1: Prepare tracking
        videos = WorkflowService.prepare_tracking_step(
            projets_dir,
            keyword="camille",  # Should filter videos
            subdir=""
        )
        
        assert videos is not None
        assert len(videos) > 0
        
        # Step 2: Create temp file
        temp_file = WorkflowService.create_tracking_temp_file(videos)
        
        assert temp_file.exists()
        
        # Step 3: Verify temp file can be read by subprocess
        with open(temp_file, 'r') as f:
            data = json.load(f)
        
        assert isinstance(data, list)
        assert all(isinstance(v, str) for v in data)
        
        # Cleanup
        temp_file.unlink()


class TestWorkflowServiceHelperMethods:
    """Integration tests for WorkflowService helper methods."""
    
    def test_parse_progress_multiple_patterns(self):
        """Test progress parsing with different log patterns."""
        patterns = {
            'total': __import__('re').compile(r'TOTAL_VIDEOS:\s*(\d+)', __import__('re').IGNORECASE),
            'current': __import__('re').compile(r'Processing\s+(\d+)/(\d+):\s*(.*)', __import__('re').IGNORECASE),
        }
        
        def parse_progress_from_log_line(line, patterns, current_total, current_progress):
            """Parse progress information from a log line."""
            total = current_total
            progress = current_progress
            text = None
            
            # Check for total count
            total_match = patterns['total'].search(line)
            if total_match:
                total = int(total_match.group(1))
            
            # Check for current progress
            current_match = patterns['current'].search(line)
            if current_match:
                progress = int(current_match.group(1))
                total = int(current_match.group(2))
                text = current_match.group(3)
            
            return total, progress, text
        
        # Test total pattern
        line_total = "TOTAL_VIDEOS: 10"
        total, current, text = parse_progress_from_log_line(
            line_total, patterns, 0, 0
        )
        assert total == 10
        assert current == 0
        
        # Test current pattern
        line_current = "Processing 5/10: video.mp4"
        total, current, text = parse_progress_from_log_line(
            line_current, patterns, 10, 0
        )
        assert current == 5
        assert text == "video.mp4"
    
    def test_calculate_duration_various_times(self):
        """Test duration calculation for various time spans."""
        import time
        
        # Test short duration (< 60s)
        start = time.time()
        time.sleep(0.1)
        duration = WorkflowService.calculate_step_duration(start)
        assert 's' in duration
        assert 'h' not in duration
        
        # Test with None
        duration_none = WorkflowService.calculate_step_duration(None)
        assert duration_none == "N/A"
        
        # Test with past time (simulate 90 seconds)
        start_90s = time.time() - 90
        duration_90s = WorkflowService.calculate_step_duration(start_90s)
        assert 'm' in duration_90s  # Should show minutes
    
    def test_format_duration_seconds(self):
        """Test duration formatting for different second values."""
        # Seconds
        assert 's' in WorkflowService.format_duration_seconds(45)
        
        # Minutes
        duration_min = WorkflowService.format_duration_seconds(150)  # 2m 30s
        assert 'm' in duration_min
        
        # Hours
        duration_hour = WorkflowService.format_duration_seconds(7200)  # 2h
        assert 'h' in duration_hour
        
        # Negative
        assert WorkflowService.format_duration_seconds(-10) == "N/A"


class TestWorkflowStateIntegration:
    """Integration tests for WorkflowState with concurrent access."""
    
    def test_concurrent_step_updates(self):
        """Test concurrent updates to workflow state."""
        from services.workflow_state import get_workflow_state, reset_workflow_state
        import threading
        
        reset_workflow_state()
        state = get_workflow_state()
        state.initialize_all_steps(['STEP1', 'STEP2', 'STEP3'])
        
        def update_worker(step_key, iterations):
            for i in range(iterations):
                state.update_step_progress(step_key, i, iterations, f'Processing {i}')
                state.append_step_log(step_key, f'Log entry {i}')
        
        # Launch concurrent updates
        threads = [
            threading.Thread(target=update_worker, args=('STEP1', 50)),
            threading.Thread(target=update_worker, args=('STEP2', 50)),
            threading.Thread(target=update_worker, args=('STEP3', 50))
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify state is consistent
        for step in ['STEP1', 'STEP2', 'STEP3']:
            info = state.get_step_info(step)
            assert info['progress_total'] > 0
            assert len(info['log']) > 0
        
        reset_workflow_state()
    
    def test_sequence_management_integration(self):
        """Test sequence management with multiple steps."""
        from services.workflow_state import get_workflow_state, reset_workflow_state
        
        reset_workflow_state()
        state = get_workflow_state()
        state.initialize_all_steps(['STEP1', 'STEP2', 'STEP3'])
        
        # Start sequence
        assert state.start_sequence('Full') is True
        assert state.is_sequence_running() is True
        
        # Cannot start another sequence
        assert state.start_sequence('Custom') is False
        
        # Update steps during sequence
        state.update_step_status('STEP1', 'running')
        assert state.is_step_running('STEP1') is True
        assert state.is_any_step_running() is True
        
        state.update_step_status('STEP1', 'completed')
        state.update_step_status('STEP2', 'running')
        
        # Complete sequence
        state.complete_sequence(success=True, message='All done', sequence_type='Full')
        assert state.is_sequence_running() is False
        
        outcome = state.get_sequence_outcome()
        assert outcome['status'] == 'success'
        assert outcome['type'] == 'Full'
        
        reset_workflow_state()
    
    def test_csv_download_tracking_integration(self):
        """Test CSV download tracking with state management."""
        from services.workflow_state import get_workflow_state, reset_workflow_state
        
        reset_workflow_state()
        state = get_workflow_state()
        
        # Add multiple downloads
        for i in range(5):
            download_info = {
                'filename': f'file{i}.zip',
                'status': 'pending',
                'progress': 0
            }
            state.add_csv_download(f'dl_{i}', download_info)
        
        # Update some downloads
        for i in range(3):
            state.update_csv_download(f'dl_{i}', 'downloading', progress=50)
        
        # Complete some downloads
        for i in range(2):
            state.update_csv_download(f'dl_{i}', 'completed', progress=100)
            state.remove_csv_download(f'dl_{i}', keep_in_history=True)
        
        # Verify status
        status = state.get_csv_downloads_status()
        assert status['total_active'] == 3  # 5 - 2 completed
        assert status['total_kept'] == 2
        
        reset_workflow_state()


class TestEndToEndWorkflow:
    """End-to-end integration tests simulating complete workflows."""
    
    @patch('services.filesystem_service.FilesystemService.find_videos_for_tracking')
    def test_step5_workflow_simulation(self, mock_find_videos, tmp_path):
        """Simulate complete STEP5 workflow."""
        # Mock video discovery
        mock_videos = [
            str(tmp_path / 'video1.mp4'),
            str(tmp_path / 'video2.mp4'),
            str(tmp_path / 'video3.mp4')
        ]
        mock_find_videos.return_value = mock_videos
        
        # Step 1: Prepare
        videos = WorkflowService.prepare_tracking_step(
            tmp_path,
            keyword="test",
            subdir=""
        )
        
        assert videos == mock_videos
        
        # Step 2: Create temp file
        temp_file = WorkflowService.create_tracking_temp_file(videos)
        assert temp_file.exists()
        
        # Step 3: Verify file is valid JSON
        with open(temp_file, 'r') as f:
            data = json.load(f)
        assert data == mock_videos
        
        # Step 4: Cleanup (simulating subprocess completion)
        temp_file.unlink()
        assert not temp_file.exists()
    
    def test_progress_tracking_workflow(self):
        """Test complete progress tracking workflow."""
        from services.workflow_state import get_workflow_state, reset_workflow_state
        import re
        
        reset_workflow_state()
        state = get_workflow_state()
        state.initialize_step('STEP2')
        
        # Simulate progress through various log lines
        patterns = {
            'total': re.compile(r'TOTAL_VIDEOS_TO_PROCESS:\s*(\d+)', re.IGNORECASE),
            'current': re.compile(r'--- Traitement de la vidéo \((\d+)/(\d+)\): (.*?) ---', re.IGNORECASE)
        }
        
        def parse_progress_from_log_line(line, patterns, current_total, current_progress):
            """Parse progress information from a log line."""
            total = current_total
            progress = current_progress
            text = None
            
            # Check for total count
            total_match = patterns['total'].search(line)
            if total_match:
                total = int(total_match.group(1))
            
            # Check for current progress
            current_match = patterns['current'].search(line)
            if current_match:
                progress = int(current_match.group(1))
                total = int(current_match.group(2))
                text = current_match.group(3)
            
            return total, progress, text
        
        log_lines = [
            "TOTAL_VIDEOS_TO_PROCESS: 5",
            "--- Traitement de la vidéo (1/5): video1.mp4 ---",
            "--- Traitement de la vidéo (2/5): video2.mp4 ---",
            "--- Traitement de la vidéo (3/5): video3.mp4 ---",
        ]
        
        current_total = 0
        current_progress = 0
        
        for line in log_lines:
            total, progress, text = parse_progress_from_log_line(
                line, patterns, current_total, current_progress
            )
            
            if total > current_total:
                state.update_step_progress('STEP2', progress, total)
                current_total = total
            
            if progress > current_progress:
                state.update_step_progress('STEP2', progress, total, text or '')
                current_progress = progress
        
        # Verify final state
        info = state.get_step_info('STEP2')
        assert info['progress_total'] == 5
        assert info['progress_current'] == 3
        
        reset_workflow_state()
