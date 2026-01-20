#!/usr/bin/env python3
"""
Production Configuration Setup Script
Generates secure configuration for production deployment.
"""

import os
import secrets
import string
from pathlib import Path

def generate_secure_token(length: int = 64) -> str:
    """Generate a cryptographically secure random token."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_production_env():
    """Create a production .env file with secure defaults."""
    
    print("🔧 Setting up production configuration...")
    
    # Generate secure tokens
    flask_secret = generate_secure_token(64)
    internal_token = generate_secure_token(64)
    render_token = generate_secure_token(64)
    
    # Production configuration
    production_config = f"""# Flask Application Configuration (PRODUCTION)
FLASK_SECRET_KEY={flask_secret}
DEBUG=false

# Security Tokens (CHANGE THESE IN PRODUCTION)
INTERNAL_WORKER_COMMS_TOKEN={internal_token}
RENDER_REGISTER_TOKEN={render_token}

# Performance Configuration
ENABLE_GPU_MONITORING=true
MAX_CPU_WORKERS=8
POLLING_INTERVAL=1000

# Cache Configuration
CACHE_DEFAULT_TIMEOUT=600
CACHE_TYPE=SimpleCache

# Performance Thresholds
PERFORMANCE_CPU_THRESHOLD=85
PERFORMANCE_MEMORY_THRESHOLD=90

# Production Settings
LOG_LEVEL=WARNING
ENABLE_PROFILING=false

# Database Configuration (if needed)
# DATABASE_URL=postgresql://user:password@localhost/dbname

# External Service URLs (update as needed)
# EXTERNAL_API_URL=https://api.example.com
# WEBHOOK_URL=https://your-webhook-endpoint.com
"""
    
    # Write to .env.production
    env_file = Path('.env.production')
    with open(env_file, 'w') as f:
        f.write(production_config)
    
    print(f"✅ Production configuration written to {env_file}")
    print("\n🔐 IMPORTANT SECURITY NOTES:")
    print("1. The generated tokens are cryptographically secure")
    print("2. Set appropriate external service URLs")
    print("3. Review and adjust performance thresholds for your environment")
    print("4. Consider using a proper secret management system for production")
    
    print("\n📋 To use this configuration:")
    print("1. Copy .env.production to .env")
    print("2. Update any placeholder URLs")
    print("3. Restart the application")
    
    return env_file

def validate_production_config():
    """Validate production configuration."""
    
    print("\n🔍 Validating production configuration...")
    
    required_vars = [
        'FLASK_SECRET_KEY',
        'INTERNAL_WORKER_COMMS_TOKEN', 
        'RENDER_REGISTER_TOKEN'
    ]
    
    missing_vars = []
    weak_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        elif var.endswith('_TOKEN') or var.endswith('_KEY'):
            if len(value) < 32:
                weak_vars.append(f"{var} (too short: {len(value)} chars)")
            elif value.startswith('dev-'):
                weak_vars.append(f"{var} (using development default)")
    
    # Check DEBUG mode
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    if debug_mode:
        print("⚠️  WARNING: DEBUG mode is enabled in production")
    
    # Report results
    if missing_vars:
        print(f"❌ Missing required variables: {', '.join(missing_vars)}")
    
    if weak_vars:
        print(f"⚠️  Weak security configuration: {', '.join(weak_vars)}")
    
    if not missing_vars and not weak_vars and not debug_mode:
        print("✅ Production configuration looks secure")
        return True
    else:
        print("❌ Production configuration needs attention")
        return False

def create_systemd_service():
    """Create a systemd service file for production deployment."""
    
    current_dir = Path.cwd()
    user = os.getenv('USER', 'www-data')
    venv_name = os.getenv('WORKFLOW_VENV_NAME', 'env')
    venv_bin_dir = current_dir / venv_name / 'bin'
    venv_python = venv_bin_dir / 'python'
    
    service_content = f"""[Unit]
Description=Workflow MediaPipe Application
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={current_dir}
Environment=PATH={venv_bin_dir}
ExecStart={venv_python} app_new.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={current_dir}

# Environment file
EnvironmentFile={current_dir}/.env

[Install]
WantedBy=multi-user.target
"""
    
    service_file = Path('workflow-mediapipe.service')
    with open(service_file, 'w') as f:
        f.write(service_content)
    
    print(f"✅ Systemd service file created: {service_file}")
    print("\n📋 To install the service:")
    print(f"1. sudo cp {service_file} /etc/systemd/system/")
    print("2. sudo systemctl daemon-reload")
    print("3. sudo systemctl enable workflow-mediapipe")
    print("4. sudo systemctl start workflow-mediapipe")
    
    return service_file

def main():
    """Main setup function."""
    
    print("🚀 Workflow MediaPipe Production Setup")
    print("=" * 50)
    
    # Create production configuration
    env_file = create_production_env()
    
    # Create systemd service
    service_file = create_systemd_service()
    
    # Validate current configuration if .env exists
    if Path('.env').exists():
        # Load current .env for validation
        from dotenv import load_dotenv
        load_dotenv()
        validate_production_config()
    
    print("\n🎯 Next Steps:")
    print("1. Review and customize the generated configuration files")
    print("2. Copy .env.production to .env (backup your current .env first)")
    print("3. Update any placeholder URLs and settings")
    print("4. Test the application with the new configuration")
    print("5. Deploy using the systemd service or your preferred method")
    
    print("\n⚠️  SECURITY REMINDER:")
    print("- Never commit .env files to version control")
    print("- Use proper secret management in production")
    print("- Regularly rotate security tokens")
    print("- Monitor application logs for security issues")

if __name__ == "__main__":
    main()
