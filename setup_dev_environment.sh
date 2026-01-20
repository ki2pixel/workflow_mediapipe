#!/bin/bash

# This script sets up the development environment according to DEVELOPMENT_GUIDELINES.md

set -e  # Exit on any error

echo "=========================================="
echo "  MediaPipe Workflow Development Setup"
echo "=========================================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_python() {
    print_status "Checking Python version..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        print_status "Found Python $PYTHON_VERSION"
        
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
            print_status "Python version is compatible"
        else
            print_error "Python 3.8+ is required. Current version: $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
}

check_system_dependencies() {
    print_status "Checking system dependencies..."
    
    if ! command -v ffmpeg &> /dev/null; then
        print_warning "FFmpeg not found. Please install it:"
        echo "  Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg"
        echo "  macOS: brew install ffmpeg"
        echo "  Windows: Download from https://ffmpeg.org/download.html"
    else
        print_status "FFmpeg found"
    fi
    
    if ! command -v git &> /dev/null; then
        print_error "Git is required but not installed"
        exit 1
    else
        print_status "Git found"
    fi
}

setup_virtual_environments() {
    print_status "Setting up virtual environments..."
    
    if [ ! -d "env" ]; then
        print_status "Creating main virtual environment..."
        python3 -m venv env
    else
        print_status "Main virtual environment already exists"
    fi
    
    if [ ! -d "audio_env" ]; then
        print_status "Creating audio processing environment..."
        python3 -m venv audio_env
    else
        print_status "Audio environment already exists"
    fi
    
    if [ ! -d "tracking_env" ]; then
        print_status "Creating tracking environment..."
        python3 -m venv tracking_env
    else
        print_status "Tracking environment already exists"
    fi
    
    if [ ! -d "transnet_env" ]; then
        print_status "Creating TransNet environment..."
        python3 -m venv transnet_env
    else
        print_status "TransNet environment already exists"
    fi
}

install_dependencies() {
    print_status "Installing Python dependencies..."
    
    source env/bin/activate
    pip install --upgrade pip
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_status "Main dependencies installed"
    else
        print_warning "requirements.txt not found, installing basic dependencies"
        pip install flask flask-caching opencv-python mediapipe numpy psutil requests
    fi
    
    deactivate
}

create_directories() {
    print_status "Creating project directories..."
    
    mkdir -p logs/{step1,step2,step3,step4,step5,step6}
    
    mkdir -p projets_extraits
    
    mkdir -p config
    
    print_status "Directory structure created"
}

setup_git_hooks() {
    if [ -d ".git" ]; then
        print_status "Setting up git hooks..."
        
        cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for code quality checks

if command -v black &> /dev/null; then
    echo "Running black formatter..."
    black --check --diff .
    if [ $? -ne 0 ]; then
        echo "Code formatting issues found. Run 'black .' to fix them."
        exit 1
    fi
fi

if command -v flake8 &> /dev/null; then
    echo "Running flake8 linter..."
    flake8 .
    if [ $? -ne 0 ]; then
        echo "Linting issues found. Please fix them before committing."
        exit 1
    fi
fi

echo "Pre-commit checks passed!"
EOF
        
        chmod +x .git/hooks/pre-commit
        print_status "Git hooks configured"
    else
        print_warning "Not a git repository, skipping git hooks setup"
    fi
}

create_env_file() {
    if [ ! -f ".env" ]; then
        print_status "Creating environment configuration file..."
        
        cat > .env << 'EOF'
# Flask Configuration
FLASK_PORT=5000
DEBUG_MODE=false
FLASK_SECRET_KEY=change-this-in-production

# Worker Communication Tokens (change these!)
INTERNAL_WORKER_COMMS_TOKEN=your-secure-token-here
RENDER_REGISTER_TOKEN=your-render-token-here

# Remote Service Configuration
REMOTE_TRIGGER_URL=https://render-signal-server.onrender.com/api/check_trigger
REMOTE_POLLING_INTERVAL=15

# Logging Configuration
LOGS_BASE_DIR=./logs

# Processing Configuration
MAX_CPU_WORKERS=15
POLLING_INTERVAL=500
EOF
        
        print_warning "Created .env file with default values. Please update the tokens!"
        print_warning "Never commit the .env file to version control!"
    else
        print_status ".env file already exists"
    fi
}

make_scripts_executable() {
    print_status "Making scripts executable..."
    
    chmod +x start_workflow.sh
    chmod +x make_executable.sh
    chmod +x setup_dev_environment.sh
    
    find workflow_scripts -name "*.py" -exec chmod +x {} \;
    
    print_status "Scripts are now executable"
}

main() {
    print_status "Starting development environment setup..."
    
    check_python
    check_system_dependencies
    setup_virtual_environments
    install_dependencies
    create_directories
    create_env_file
    make_scripts_executable
    setup_git_hooks
    
    echo ""
    echo "=========================================="
    print_status "Setup completed successfully!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Update the tokens in .env file"
    echo "2. Review DEVELOPMENT_GUIDELINES.md"
    echo "3. Run ./start_workflow.sh to test the application"
    echo ""
    print_warning "Remember to activate the virtual environment:"
    echo "  source env/bin/activate"
    echo ""
}

main "$@"
