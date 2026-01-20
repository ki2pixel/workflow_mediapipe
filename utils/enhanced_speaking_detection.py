#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Speaking Detection System
Implements multi-source validation for speaking detection using:
1. Face blendshapes (jaw movement)
2. Audio diarization data
3. CSV segment analysis
4. Temporal consistency validation
"""

import json
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SegmentInfo:
    """Information about a video segment from CSV data."""
    segment_id: int
    frame_start: int
    frame_end: int
    timecode_start: str
    timecode_end: str

@dataclass
class AudioInfo:
    """Audio analysis information for a frame."""
    is_speech_present: bool
    num_speakers: int
    active_speakers: List[str]
    timecode_sec: float

@dataclass
class SpeakingDetectionResult:
    """Result of enhanced speaking detection."""
    is_speaking: bool
    confidence: float
    sources: Dict[str, Any]  # Evidence from different sources
    method: str  # Primary detection method used

class EnhancedSpeakingDetector:
    """Enhanced speaking detection using multiple data sources."""
    
    def __init__(self, video_path: str, jaw_threshold: float = 0.08):
        """
        Initialize the enhanced speaking detector.
        
        Args:
            video_path: Path to the video file
            jaw_threshold: Threshold for jaw movement detection
        """
        self.video_path = Path(video_path)
        self.jaw_threshold = jaw_threshold
        
        # Load auxiliary data
        self.segments = self._load_csv_segments()
        self.audio_data = self._load_audio_analysis()
        
        # Detection parameters
        self.audio_weight = 0.6  # Weight for audio evidence
        self.visual_weight = 0.4  # Weight for visual evidence
        self.min_confidence_threshold = 0.3
        
        logger.info(f"Enhanced speaking detector initialized for {self.video_path.name}")
        logger.info(f"Loaded {len(self.segments)} segments, audio data: {self.audio_data is not None}")
    
    def _load_csv_segments(self) -> List[SegmentInfo]:
        """Load CSV segmentation data."""
        csv_path = self.video_path.with_suffix('.csv')
        segments = []

        if not csv_path.exists():
            logger.warning(f"CSV file not found: {csv_path}")
            return segments

        try:
            zero_duration_count = 0
            invalid_duration_count = 0
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    frame_start = int(row['Frame In'])
                    frame_end = int(row['Frame Out'])
                    duration = frame_end - frame_start

                    # Check for problematic segments
                    if duration == 0:
                        zero_duration_count += 1
                        logger.warning(f"Zero-duration segment detected: ID {row['No']}, frame {frame_start}")
                    elif duration < 0:
                        invalid_duration_count += 1
                        logger.warning(f"Invalid segment with negative duration: ID {row['No']}, frames {frame_start}-{frame_end}")

                    segment = SegmentInfo(
                        segment_id=int(row['No']),
                        frame_start=frame_start,
                        frame_end=frame_end,
                        timecode_start=row['Timecode In'],
                        timecode_end=row['Timecode Out']
                    )
                    segments.append(segment)

            logger.info(f"Loaded {len(segments)} segments from {csv_path.name}")
            if zero_duration_count > 0:
                logger.warning(f"Found {zero_duration_count} zero-duration segments that will be handled safely")
            if invalid_duration_count > 0:
                logger.warning(f"Found {invalid_duration_count} segments with invalid negative durations that will be handled safely")

        except Exception as e:
            logger.error(f"Error loading CSV segments: {e}")

        return segments
    
    def _load_audio_analysis(self) -> Optional[Dict[int, AudioInfo]]:
        """Load audio analysis data."""
        # Construct audio JSON path: video_name_audio.json
        video_stem = self.video_path.stem  # e.g., "AMERICAINES"
        audio_json_path = self.video_path.parent / f"{video_stem}_audio.json"
        
        if not audio_json_path.exists():
            logger.warning(f"Audio analysis file not found: {audio_json_path}")
            return None
        
        try:
            with open(audio_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            audio_data = {}
            warned_schema_once = False
            for frame_data in data.get('frames_analysis', []):
                try:
                    frame_num = frame_data.get('frame')
                    audio_info = frame_data.get('audio_info', {}) or {}

                    # Fallbacks for schema differences
                    is_speech_present = bool(audio_info.get('is_speech_present', False))
                    if 'num_distinct_speakers_audio' in audio_info:
                        num_speakers = int(audio_info.get('num_distinct_speakers_audio', 0) or 0)
                    elif 'num_speakers' in audio_info:
                        num_speakers = int(audio_info.get('num_speakers', 0) or 0)
                    else:
                        # derive from list length if available
                        num_speakers = len(audio_info.get('active_speaker_labels', []) or [])
                        if not warned_schema_once:
                            logger.debug("Audio schema using simplified format (active_speaker_labels only); deriving num_speakers from list length")
                            warned_schema_once = True

                    active_speakers = list(audio_info.get('active_speaker_labels', []) or [])
                    timecode_sec = float(audio_info.get('timecode_sec', 0.0) or 0.0)

                    if frame_num is None:
                        continue

                    audio_data[int(frame_num)] = AudioInfo(
                        is_speech_present=is_speech_present,
                        num_speakers=num_speakers,
                        active_speakers=active_speakers,
                        timecode_sec=timecode_sec
                    )
                except Exception as e:
                    logger.warning(f"Skipping malformed audio frame entry: {e}")

            logger.info(f"Loaded audio data for {len(audio_data)} frames")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error loading audio analysis: {e}")
            return None
    
    def get_segment_for_frame(self, frame_num: int) -> Optional[SegmentInfo]:
        """Get the segment that contains the given frame."""
        for segment in self.segments:
            if segment.frame_start <= frame_num <= segment.frame_end:
                return segment
        return None
    
    def detect_speaking(self, frame_num: int, blendshapes: Optional[Dict[str, float]] = None,
                       source_detector: str = "face_landmarker") -> SpeakingDetectionResult:
        """
        Enhanced speaking detection using multiple sources.
        
        Args:
            frame_num: Frame number (1-based)
            blendshapes: Face blendshapes data (if available)
            source_detector: Source of detection ("face_landmarker" or "object_detector")
            
        Returns:
            SpeakingDetectionResult with confidence and evidence
        """
        sources = {}
        confidence_scores = []
        
        # 1. Audio-based detection (primary source)
        audio_confidence = 0.0
        if self.audio_data and frame_num in self.audio_data:
            audio_info = self.audio_data[frame_num]
            if audio_info.is_speech_present:
                # Higher confidence with more speakers
                audio_confidence = min(0.8 + (audio_info.num_speakers * 0.1), 1.0)
            sources['audio'] = {
                'is_speech_present': audio_info.is_speech_present,
                'num_speakers': audio_info.num_speakers,
                'active_speakers': audio_info.active_speakers,
                'confidence': audio_confidence
            }
            confidence_scores.append(audio_confidence * self.audio_weight)
        
        # 2. Visual-based detection (blendshapes)
        visual_confidence = 0.0
        if source_detector == "face_landmarker" and blendshapes and "jawOpen" in blendshapes:
            jaw_open = blendshapes["jawOpen"]
            
            # Enhanced jaw movement analysis
            if jaw_open > self.jaw_threshold:
                # Scale confidence based on jaw opening amount
                visual_confidence = min(jaw_open / self.jaw_threshold * 0.7, 1.0)
                
                # Additional blendshape analysis for better accuracy
                mouth_indicators = [
                    blendshapes.get("mouthOpen", 0.0),
                    blendshapes.get("mouthShrugUpper", 0.0),
                    blendshapes.get("mouthShrugLower", 0.0)
                ]
                mouth_activity = sum(mouth_indicators) / len(mouth_indicators)
                visual_confidence = min(visual_confidence + mouth_activity * 0.2, 1.0)
            
            sources['visual'] = {
                'jaw_open': jaw_open,
                'jaw_threshold': self.jaw_threshold,
                'mouth_activity': mouth_activity if 'mouth_activity' in locals() else 0.0,
                'confidence': visual_confidence
            }
            confidence_scores.append(visual_confidence * self.visual_weight)
        
        # 3. Segment-based context
        segment = self.get_segment_for_frame(frame_num)
        if segment:
            # Calculate frame position safely, handling zero-duration segments
            segment_duration = segment.frame_end - segment.frame_start
            if segment_duration > 0:
                frame_position = (frame_num - segment.frame_start) / segment_duration
            elif segment_duration == 0:
                # Zero-duration segment: frame is at the single point
                frame_position = 0.0
                logger.debug(f"Zero-duration segment {segment.segment_id} at frame {frame_num}, using position 0.0")
            else:
                # Negative duration (invalid segment): treat as zero-duration
                frame_position = 0.0
                logger.warning(f"Invalid segment {segment.segment_id} with negative duration {segment_duration}, using position 0.0")

            sources['segment'] = {
                'segment_id': segment.segment_id,
                'frame_position': frame_position,
                'segment_duration': segment_duration,
                'is_zero_duration': segment_duration == 0
            }
        
        # 4. Calculate final result
        if confidence_scores:
            final_confidence = sum(confidence_scores)
        else:
            final_confidence = 0.0
        
        # Determine speaking status and method
        is_speaking = final_confidence > self.min_confidence_threshold
        
        # Determine primary method
        if audio_confidence > visual_confidence:
            method = "audio_primary"
        elif visual_confidence > 0:
            method = "visual_primary"
        elif source_detector == "object_detector":
            method = "object_detection_fallback"
        else:
            method = "no_detection"
        
        return SpeakingDetectionResult(
            is_speaking=is_speaking,
            confidence=final_confidence,
            sources=sources,
            method=method
        )
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get statistics about available detection sources."""
        return {
            'segments_available': len(self.segments) > 0,
            'audio_data_available': self.audio_data is not None,
            'total_segments': len(self.segments),
            'total_audio_frames': len(self.audio_data) if self.audio_data else 0,
            'jaw_threshold': self.jaw_threshold,
            'audio_weight': self.audio_weight,
            'visual_weight': self.visual_weight
        }
