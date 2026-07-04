#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Common Types and Enums
"""

from enum import Enum

class StepKey(str, Enum):
    STEP1 = "STEP1"
    STEP2 = "STEP2"
    STEP3 = "STEP3"
    STEP4 = "STEP4"
    STEP5 = "STEP5"
    STEP6 = "STEP6"
    STEP7 = "STEP7"
    STEP8 = "STEP8"

class StepStatus(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CSVDownloadStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
