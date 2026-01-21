# Architecture Audit - Project Structure

**Date**: 2026-01-21  
**Auditor**: AI Assistant  
**Scope**: Complete project structure analysis  
**Technologies**: Flask 3.0.0, MediaPipe 0.10.7, OpenCV 4.8.1.78, PyTorch 2.1.0, Transformers 4.35.0, Node.js (ESM), FFmpeg, MySQL, Airtable

## Project Overview

Multi-step video processing pipeline with face tracking, audio analysis, and computer vision capabilities. Features include workflow orchestration, real-time monitoring, and comprehensive testing infrastructure.

---

## Rules Applied

### Standard Rules
- Empty files or folders
- Duplicate files
- Large files (>1MB)
- Overly nested folders (>8 levels deep)
- Overloaded folders (>25 items)
- Inefficient project structure
- Inconsistent naming conventions
- Files in wrong directory
- Missing separation of concerns

### Project-Specific Rules 🆕
- Security configuration issues
- Dependency management inconsistencies
- Test coverage gaps
- Environment configuration sprawl
- Documentation organization issues
- Frontend-backend coupling violations

---

## Issues Identified

## 🚨 Empty Files and Folders

**Issue**: Empty files and lock files create maintenance overhead and indicate incomplete setup.

**Affected files/folders**:
- `/home/kidpixel/workflow_mediapipe/ort` (0 bytes)
- `/home/kidpixel/workflow_mediapipe/workflow_scripts/step5/models/blendshapes/opencv/pyfeat_models/.locks/models--py-feat--mp_blendshapes/a79dc7684c908023f0f07d17eac8a815c0b8dffb613f18369178d4fd779fc22b.lock`
- `/home/kidpixel/workflow_mediapipe/workflow_scripts/step5/models/blendshapes/opencv/pyfeat_models/pyfeat/.locks/models--py-feat--mp_blendshapes/a79dc7684c908023f0f07d17eac8a815c0b8dffb613f18369178d4fd779fc22b.lock`
- `/home/kidpixel/workflow_mediapipe/projets_extraits/` (empty directory)
- `/home/kidpixel/workflow_mediapipe/_finalized_output/` (empty directory)
- `/home/kidpixel/workflow_mediapipe/csv_downloads/` (empty directory)
- `/home/kidpixel/workflow_mediapipe/envs/` (empty directory)

**Explanation**: Empty directories suggest incomplete setup or abandoned features. Lock files indicate interrupted model downloads that should be cleaned up.

**Recommendations**: 
- Remove the empty `ort` file
- Clean up lock files and implement proper download retry mechanisms
- Remove or document purpose of empty directories
- Add `.gitkeep` files for intentional empty directories

**Example Fix**:
```bash
# Clean up lock files
find . -name "*.lock" -delete
# Add .gitkeep for intentional empty dirs
touch projets_extraits/.gitkeep
```

---

## 📦 Large Files in Repository

**Issue**: Large binary files in version control increase repository size and clone times.

**Affected files**:
- `/home/kidpixel/workflow_mediapipe/assets/face_landmarker_v2_with_blendshapes.task`
- `/home/kidpixel/workflow_mediapipe/assets/EfficientDet-Lite2-32.tflite`
- `/home/kidpixel/workflow_mediapipe/assets/transnetv2-pytorch-weights.pth`
- Multiple duplicate model files in `workflow_scripts/step5/models/`

**Explanation**: Model files (>1MB) should not be stored in Git. They bloat the repository and are better managed via download scripts or Git LFS.

**Recommendations**:
- Move model files to external storage or use Git LFS
- Implement download scripts for model acquisition
- Add model files to `.gitignore`
- Create model registry in configuration

**Example Fix**:
```python
# config/model_registry.py
MODEL_REGISTRY = {
    'face_landmarker': {
        'url': 'https://storage.googleapis.com/mediapipe-models/face_landmarker.task',
        'checksum': 'sha256:abc123...',
        'local_path': 'models/face_landmarker.task'
    }
}
```

---

## 📁 Overloaded Static Directory

**Issue**: The static directory contains too many files (25+), making navigation difficult.

**Affected directory**: `/home/kidpixel/workflow_mediapipe/static/` (25+ files)

**Explanation**: Flat structure with many files reduces maintainability and makes finding specific components difficult.

**Recommendations**:
- Organize static files into subdirectories: `js/`, `css/`, `utils/`, `components/`
- Group related files (e.g., all timeline components together)
- Use consistent naming conventions

**Example Structure**:
```
static/
├── js/
│   ├── components/
│   ├── services/
│   └── main.js
├── css/
├── utils/
└── assets/
```

---

## 🔧 Configuration Sprawl

**Issue**: Multiple configuration files and environment variables create maintenance complexity.

**Affected files**:
- `.env` (9830 bytes)
- `.env.mysql.example`
- `config/settings.py`
- `config/workflow_commands.py`
- `requirements.txt`, `requirements-dev.txt`, `requirements_tracking_env.txt`

**Explanation**: Configuration is scattered across multiple files, making it hard to understand the complete configuration landscape.

**Recommendations**:
- Consolidate environment-specific configurations
- Create configuration schema documentation
- Implement configuration validation at startup
- Use configuration management patterns

**Example Fix**:
```python
# config/environments.py
class DevelopmentConfig(Config):
    DEBUG = True
    DATABASE_URI = 'sqlite:///dev.db'

class ProductionConfig(Config):
    DEBUG = False
    DATABASE_URI = os.getenv('DATABASE_URL')
```

---

## 🧪 Test Organization Issues

**Issue**: Tests are spread across multiple directories with inconsistent organization.

**Affected directories**:
- `tests/unit/`
- `tests/integration/`
- `tests/legacy/`
- `tests/frontend/`

**Explanation**: Mixed test organization and legacy tests create confusion about test coverage and responsibilities.

**Recommendations**:
- Archive or remove legacy tests
- Standardize test directory structure
- Implement test coverage reporting
- Separate unit, integration, and E2E tests clearly

**Example Structure**:
```
tests/
├── unit/
├── integration/
├── e2e/
├── frontend/
└── fixtures/
```

---

## 🔄 Duplicate Model Files

**Issue**: Same model files exist in multiple locations, wasting storage and creating confusion.

**Affected files**:
- `assets/face_landmarker_v2_with_blendshapes.task`
- `workflow_scripts/step5/models/face_detectors/mediapipe/face_landmarker_v2_with_blendshapes.task`
- Multiple blendshape models in different locations

**Explanation**: Duplicates create maintenance overhead and risk of using different versions.

**Recommendations**:
- Establish single source of truth for models
- Use symbolic links or model registry
- Implement model versioning strategy
- Clean up duplicate files

**Example Fix**:
```bash
# Create central models directory
mkdir -p models/mediapipe
# Use symlinks for access
ln -s models/mediapipe/face_landmarker.task assets/face_landmarker.task
```

---

## 🏗️ Service Layer Violations

**Issue**: Some services may be doing too much, violating single responsibility principle.

**Affected files**:
- `services/report_service.py` (1222 lines)
- `services/csv_service.py` (1015 lines)
- `services/lemonfox_audio_service.py` (805 lines)

**Explanation**: Large service files suggest multiple responsibilities and potential coupling issues.

**Recommendations**:
- Split large services into focused components
- Extract common functionality into utilities
- Implement proper dependency injection
- Add service interfaces

**Example Refactoring**:
```python
# Split report_service.py into:
# - report_generator.py
# - report_formatter.py  
# - report_exporter.py
# - templates/
```

---

## 📱 Frontend-Backend Coupling

**Issue**: Frontend JavaScript files lack proper organization and may be tightly coupled.

**Affected files**:
- 33+ JavaScript files in `static/` directory
- Mixed utility files, components, and application logic

**Explanation**: Flat structure and potential coupling between frontend and backend concerns.

**Recommendations**:
- Implement proper frontend architecture (MVC/MVVM)
- Separate utilities from components
- Create proper module boundaries
- Consider frontend build process

**Example Structure**:
```
static/
├── js/
│   ├── components/
│   │   ├── Timeline.js
│   │   └── StepDetails.js
│   ├── services/
│   │   └── ApiService.js
│   └── utils/
│       └── DOMBatcher.js
```

---

## 🔒 Security Configuration Issues

**Issue**: Security configurations may be scattered and inconsistent.

**Affected files**:
- `config/security.py`
- `.env` with potential secrets
- Environment variable handling in `app_new.py`

**Explanation**: Security configuration should be centralized and properly managed.

**Recommendations**:
- Centralize security configuration
- Implement proper secret management
- Add security headers and CORS configuration
- Create security audit checklist

**Example Fix**:
```python
# config/security.py
class SecurityConfig:
    SECRET_KEY = os.getenv('SECRET_KEY')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')
    RATE_LIMIT = os.getenv('RATE_LIMIT', '100/hour')
```

---

## 📊 Dependency Management Issues

**Issue**: Multiple requirements files suggest dependency management complexity.

**Affected files**:
- `requirements.txt`
- `requirements-dev.txt`
- `requirements_tracking_env.txt`

**Explanation**: Multiple requirements files can lead to dependency conflicts and confusion.

**Recommendations**:
- Consolidate requirements files
- Use dependency groups (Poetry/PDM)
- Implement dependency scanning
- Create dependency update strategy

**Example Fix**:
```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.9"
flask = "^3.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^23.7.0"

[tool.poetry.group.tracking.dependencies]
opencv-python = "^4.8.0"
```

---

## Summary Statistics

- **Total Python files**: 60
- **Total JavaScript files**: 33
- **Large files (>1MB)**: 10+ model files
- **Empty directories**: 7
- **Max file size**: `face_engines.py` (1720 lines)
- **Static files**: 25+ in flat structure

## Priority Recommendations

### High Priority (Immediate Action)
1. Remove duplicate model files and implement model registry
2. Clean up lock files and empty directories
3. Move large model files out of Git (use Git LFS or download scripts)

### Medium Priority (Next Sprint)
4. Reorganize static directory structure
5. Refactor large service files
6. Consolidate configuration management

### Low Priority (Future Iteration)
7. Implement frontend build process
8. Standardize test organization
9. Enhance security configuration management

---

**Next Steps**: Choose one of the following options:
1) Continue audit with additional rules
2) Re-audit dismissing corrected points
3) Re-upload updated project structure
4) Continue audit for new issues
