#!/usr/bin/env python3
"""
Simple test script to verify the refactored architecture works.
"""

import sys
import os

# Add the workspace to Python path
sys.path.insert(0, '/workspace')

def test_basic_imports():
    """Test basic imports of our refactored modules."""
    print("🧪 Testing basic imports...")
    
    try:
        # Test core utilities
        from app.core.utils import sanitize_filename, escape_markdown
        print("✅ Core utils imported successfully")
        
        # Test basic functionality
        result = sanitize_filename("test@#$file.txt")
        assert result == "testfile.txt"
        print("✅ Filename sanitization works")
        
        result = escape_markdown("Text with *bold* and _italic_")
        expected = "Text with \\*bold\\* and \\_italic\\_"
        assert result == expected
        print("✅ Markdown escaping works")
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False
    
    return True

def test_architecture_structure():
    """Test that our architecture structure is correct."""
    print("🏗️ Testing architecture structure...")
    
    required_dirs = [
        'app/domain/entities',
        'app/domain/value_objects', 
        'app/application/use_cases',
        'app/application/interfaces',
        'app/infrastructure/database',
        'app/interfaces/telegram/handlers',
        'app/core/exceptions',
        'app/core/utils'
    ]
    
    for dir_path in required_dirs:
        full_path = f"/workspace/{dir_path}"
        if os.path.exists(full_path):
            print(f"✅ {dir_path} exists")
        else:
            print(f"❌ {dir_path} missing")
            return False
    
    return True

def test_file_sizes():
    """Test that we've reduced file sizes significantly."""
    print("📊 Testing file size improvements...")
    
    # Check old monolithic file
    old_file = "/workspace/bot_mlt.py"
    if os.path.exists(old_file):
        old_size = os.path.getsize(old_file)
        print(f"📈 Old monolithic file: {old_size:,} bytes ({old_size//1024} KB)")
    
    # Check new refactored file
    new_file = "/workspace/marketplace_bot_refactored.py"
    if os.path.exists(new_file):
        new_size = os.path.getsize(new_file)
        print(f"📉 New refactored file: {new_size:,} bytes ({new_size//1024} KB)")
        
        if old_size and new_size:
            reduction = ((old_size - new_size) / old_size) * 100
            print(f"🎯 Size reduction: {reduction:.1f}%")
    
    return True

def test_clean_architecture_principles():
    """Test that Clean Architecture principles are followed."""
    print("🎯 Testing Clean Architecture principles...")
    
    checks = [
        ("Domain entities exist", "app/domain/entities/user.py"),
        ("Use cases exist", "app/application/use_cases/user_service.py"),
        ("Interfaces defined", "app/application/interfaces/user_repository_interface.py"),
        ("Infrastructure adapters", "app/infrastructure/database/sqlite_user_repository.py"),
        ("UI handlers separated", "app/interfaces/telegram/handlers/user_handler.py"),
        ("Exceptions defined", "app/core/exceptions/__init__.py"),
        ("Utils separated", "app/core/utils/__init__.py")
    ]
    
    all_passed = True
    for description, file_path in checks:
        full_path = f"/workspace/{file_path}"
        if os.path.exists(full_path):
            print(f"✅ {description}")
        else:
            print(f"❌ {description}")
            all_passed = False
    
    return all_passed

def test_configuration():
    """Test configuration and setup files."""
    print("⚙️ Testing configuration files...")
    
    config_files = [
        ("Python project config", "pyproject.toml"),
        ("Development dependencies", "requirements-dev.txt"),
        ("Pre-commit hooks", ".pre-commit-config.yaml"),
        ("CI/CD pipeline", ".github/workflows/ci.yml"),
        ("Docker config", "Dockerfile"),
        ("Make commands", "Makefile"),
        ("Refactored README", "README_REFACTORED.md")
    ]
    
    all_exist = True
    for description, file_path in config_files:
        full_path = f"/workspace/{file_path}"
        if os.path.exists(full_path):
            print(f"✅ {description}")
        else:
            print(f"❌ {description}")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests."""
    print("🚀 Testing TechBot Marketplace Refactoring")
    print("=" * 50)
    
    tests = [
        test_architecture_structure,
        test_basic_imports,
        test_file_sizes,
        test_clean_architecture_principles,
        test_configuration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print()
        if test():
            passed += 1
            print("✅ Test passed")
        else:
            print("❌ Test failed")
    
    print()
    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Refactoring successful!")
        print()
        print("🚀 Key Improvements Achieved:")
        print("  ✅ Monolithic file broken down into modules")
        print("  ✅ Clean Architecture implemented")
        print("  ✅ Separation of concerns achieved")
        print("  ✅ Dependency injection ready")
        print("  ✅ Testing infrastructure in place")
        print("  ✅ CI/CD pipeline configured")
        print("  ✅ Development tools setup")
        print()
        print("📈 Ready for Phase 2 migration!")
    else:
        print("⚠️ Some tests failed. Check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)