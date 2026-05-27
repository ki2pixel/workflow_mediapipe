#!/usr/bin/env python3
"""
Application Startup Validation Script
Validates configuration and startup process for the Flask application.
"""

import sys
import os
import time
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment only")

def validate_environment():
    """Validate environment setup."""
    print("🔍 Validating environment setup...")
    
    issues = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        issues.append(f"Python 3.8+ required, found {sys.version}")
    else:
        print(f"✅ Python version: {sys.version.split()[0]}")
    
    # Check virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment detected")
    else:
        issues.append("Virtual environment not detected")
    
    # Check .env file
    env_file = Path('.env')
    if env_file.exists():
        print("✅ .env file found")
    else:
        issues.append(".env file not found")
    
    return issues

def validate_configuration():
    """Validate application configuration."""
    print("\n🔧 Validating configuration...")
    
    issues = []
    warnings = []
    
    try:
        from config.settings import config
        
        # Validate configuration
        try:
            config.validate(strict=False)
            print("✅ Configuration validation passed")
        except ValueError as e:
            issues.append(f"Configuration validation failed: {e}")
        
        # Check security settings
        if config.DEBUG:
            warnings.append("DEBUG mode is enabled")
        
        is_production = not config.DEBUG
        
        if config.SECRET_KEY.startswith('dev-') or config.SECRET_KEY in ['dev-key-change-in-production', 'dev-secret-key-change-in-production-12345678901234567890']:
            msg = f"Insecure SECRET_KEY in production: {config.SECRET_KEY}" if is_production else "Using development SECRET_KEY"
            if is_production:
                issues.append(msg)
            else:
                warnings.append(msg)
        
        if config.INTERNAL_WORKER_TOKEN.startswith('dev-') or config.INTERNAL_WORKER_TOKEN == 'dev-internal-worker-token':
            msg = f"Insecure INTERNAL_WORKER_TOKEN in production: {config.INTERNAL_WORKER_TOKEN}" if is_production else "Using development INTERNAL_WORKER_TOKEN"
            if is_production:
                issues.append(msg)
            else:
                warnings.append(msg)
                

        
    except Exception as e:
        issues.append(f"Configuration import failed: {e}")
    
    return issues, warnings

def validate_services():
    """Validate service imports and initialization."""
    print("\n🔧 Validating services...")
    
    issues = []
    
    services = [
        ('MonitoringService', 'services.monitoring_service'),
        ('WorkflowService', 'services.workflow_service'),
        ('CacheService', 'services.cache_service'),
        ('PerformanceService', 'services.performance_service'),
        ('CSVService', 'services.csv_service')
    ]
    
    for service_name, module_name in services:
        try:
            module = __import__(module_name, fromlist=[service_name])
            service_class = getattr(module, service_name)
            print(f"✅ {service_name} imported successfully")
        except Exception as e:
            issues.append(f"{service_name} import failed: {e}")
    
    return issues

def validate_flask_app():
    """Validate Flask application startup."""
    print("\n🌐 Validating Flask application...")
    
    issues = []
    
    try:
        from app_new import APP_FLASK
        
        print(f"✅ Flask app created: {APP_FLASK.name}")
        
        # Check blueprints
        blueprints = list(APP_FLASK.blueprints.keys())
        print(f"✅ Blueprints registered: {blueprints}")
        
        # Check routes
        with APP_FLASK.app_context():
            routes = [str(rule) for rule in APP_FLASK.url_map.iter_rules()]
            api_routes = [r for r in routes if r.startswith('/api')]
            workflow_routes = [r for r in routes if not r.startswith('/api') and not r.startswith('/static')]
            
            print(f"✅ Total routes: {len(routes)}")
            print(f"✅ API routes: {len(api_routes)}")
            print(f"✅ Workflow routes: {len(workflow_routes)}")
        
    except Exception as e:
        issues.append(f"Flask app validation failed: {e}")
    
    return issues

def validate_frontend_files():
    """Validate frontend files exist."""
    print("\n🎨 Validating frontend files...")
    
    issues = []
    
    frontend_files = [
        'static/state/AppState.js',
        'static/utils/DOMBatcher.js',
        'static/utils/PerformanceOptimizer.js',
        'static/utils/PerformanceMonitor.js',
        'static/main.js',
        'static/uiUpdater.js'
    ]
    
    for file_path in frontend_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            issues.append(f"Missing frontend file: {file_path}")
    
    return issues

def test_service_functionality():
    """Test basic service functionality."""
    print("\n🧪 Testing service functionality...")
    
    issues = []
    
    try:
        # Test MonitoringService
        from services.monitoring_service import MonitoringService
        cpu_usage = MonitoringService.get_cpu_usage()
        if isinstance(cpu_usage, float) and 0 <= cpu_usage <= 100:
            print("✅ MonitoringService.get_cpu_usage() working")
        else:
            issues.append("MonitoringService.get_cpu_usage() returned invalid data")
        
        # Test CacheService
        from services.cache_service import CacheService
        cache_stats = CacheService.get_cache_stats()
        if isinstance(cache_stats, dict) and 'hits' in cache_stats:
            print("✅ CacheService.get_cache_stats() working")
        else:
            issues.append("CacheService.get_cache_stats() returned invalid data")
        
        # Test PerformanceService
        from services.performance_service import PerformanceService
        perf_metrics = PerformanceService.get_performance_metrics()
        if isinstance(perf_metrics, dict) and 'timestamp' in perf_metrics:
            print("✅ PerformanceService.get_performance_metrics() working")
        else:
            issues.append("PerformanceService.get_performance_metrics() returned invalid data")
        
    except Exception as e:
        issues.append(f"Service functionality test failed: {e}")
    
    return issues

def check_startup_logs():
    """Check for common startup issues in logs."""
    print("\n📋 Checking for common startup issues...")
    
    warnings = []
    
    # This would normally check log files, but for now we'll check for common issues
    
    # Check for duplicate initialization
    import threading
    active_threads = threading.active_count()
    if active_threads > 10:
        warnings.append(f"High thread count detected: {active_threads}")
    
    # Check for circular imports
    import sys
    app_modules = [name for name in sys.modules.keys() if 'app_new' in name or 'services' in name]
    if len(app_modules) > 20:
        warnings.append(f"Many app-related modules loaded: {len(app_modules)}")
    
    return warnings

def main():
    """Main validation function."""
    print("🚀 Workflow MediaPipe Startup Validation")
    print("=" * 50)
    
    all_issues = []
    all_warnings = []
    
    # Run all validations
    issues = validate_environment()
    all_issues.extend(issues)
    
    issues, warnings = validate_configuration()
    all_issues.extend(issues)
    all_warnings.extend(warnings)
    
    issues = validate_services()
    all_issues.extend(issues)
    
    issues = validate_flask_app()
    all_issues.extend(issues)
    
    issues = validate_frontend_files()
    all_issues.extend(issues)
    
    issues = test_service_functionality()
    all_issues.extend(issues)
    
    warnings = check_startup_logs()
    all_warnings.extend(warnings)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    if all_issues:
        print(f"❌ Issues found: {len(all_issues)}")
        for issue in all_issues:
            print(f"   • {issue}")
    else:
        print("✅ No critical issues found")
    
    if all_warnings:
        print(f"\n⚠️  Warnings: {len(all_warnings)}")
        for warning in all_warnings:
            print(f"   • {warning}")
    
    # Recommendations
    print("\n🎯 RECOMMENDATIONS:")
    
    if all_issues:
        print("1. Fix the critical issues listed above")
        print("2. Re-run this validation script")
        print("3. Check application logs for additional details")
    else:
        print("1. Application appears ready to run")
        if all_warnings:
            print("2. Consider addressing the warnings for production use")
        print("3. Monitor application performance after startup")
    
    # Exit code
    exit_code = 1 if all_issues else 0
    print(f"\n🏁 Validation {'FAILED' if exit_code else 'PASSED'}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
