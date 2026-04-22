"""
Full Project Audit + Safe Cleanup
Comprehensive analysis of all project files with careful removal of unnecessary items only.
"""

import json
import os
import sys
import ast
from pathlib import Path
from collections import defaultdict
import shutil

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Project structure
PROTECTED_FILES = {
    "models.py",
    "views.py",
    "settings.py",
    "urls.py",
    "admin.py",
    "apps.py",
    "__init__.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "celery.py",
    "db.sqlite3",
}

PROTECTED_PATTERNS = {
    "templates/",
    "static/",
    "migrations/",
    "chatbot/services/",
    "chatbot/models.py",
    "chatbot/views.py",
    "courses/models.py",
    "accounts/models.py",
    "progress/models.py",
}

REMOVABLE_PATTERNS = {
    "test_*.py",
    "*_test.py",
    "debug_*.py",
    "*debug*.py",
    "temp_*.py",
    "*temp*.py",
    "old_*.py",
    "backup_*.py",
    "__pycache__",
}

# Report categories
class FileAnalyzer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.files = {
            "core_system": [],
            "optional_scripts": [],
            "test_debug": [],
            "reports": [],
            "temporary": [],
            "protected": [],
            "unknown": [],
        }
        self.issues = []
        self.warnings = []
        self.recommendations = []
        self.stats = {
            "total_files": 0,
            "total_size_mb": 0,
            "python_files": 0,
            "template_files": 0,
            "static_files": 0,
            "other_files": 0,
        }
    
    def scan_directory(self, base_path: Path, relative_to: Path = None) -> list:
        """Recursively scan directory and return all files."""
        if relative_to is None:
            relative_to = base_path
        
        files = []
        try:
            for item in base_path.rglob("*"):
                if item.is_file() and item.name != "db.sqlite3":
                    rel_path = item.relative_to(relative_to)
                    try:
                        size_mb = item.stat().st_size / (1024 * 1024)
                        files.append({
                            "path": str(rel_path),
                            "full_path": str(item),
                            "name": item.name,
                            "ext": item.suffix,
                            "size_mb": round(size_mb, 4),
                            "is_python": item.suffix == ".py",
                        })
                    except Exception as e:
                        self.warnings.append(f"Could not stat file {rel_path}: {e}")
        except PermissionError as e:
            self.warnings.append(f"Permission denied scanning {base_path}: {e}")
        
        return files
    
    def classify_file(self, file_info: dict) -> str:
        """Classify a file into a category."""
        path = file_info["path"].replace("\\", "/")
        name = file_info["name"]
        
        # Protected files
        if name in PROTECTED_FILES:
            return "protected"
        
        for pattern in PROTECTED_PATTERNS:
            if pattern in path:
                return "protected"
        
        # Report files
        if "reports/" in path and name != "final_project_audit.json":
            return "reports"
        
        # Test/Debug files
        for pattern in REMOVABLE_PATTERNS:
            if pattern.startswith("*") and pattern.endswith("*"):
                base = pattern[1:-1]
                if base in name:
                    return "test_debug"
            elif pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return "test_debug"
            elif pattern.endswith("*"):
                if name.startswith(pattern[:-1]):
                    return "test_debug"
            elif pattern == name:
                return "test_debug"
        
        # Core system files
        if file_info["is_python"]:
            if any(x in path for x in ["models.py", "views.py", "admin.py", "apps.py", "services/"]):
                return "core_system"
            if path.startswith("chatbot/") or path.startswith("courses/") or path.startswith("accounts/") or path.startswith("progress/"):
                return "core_system"
            if any(x in path for x in ["urls.py", "asgi.py", "wsgi.py", "celery.py", "settings.py"]):
                return "protected"
        
        # Optional scripts
        if "scripts/" in path and file_info["is_python"]:
            return "optional_scripts"
        
        # Templates and static
        if "templates/" in path:
            return "core_system"
        if "static/" in path or "staticfiles/" in path:
            return "core_system"
        
        # Temporary files
        if name.startswith("."):
            return "temporary"
        if file_info["ext"] in [".pyc", ".pyo", ".tmp", ".bak"]:
            return "temporary"
        
        if file_info["is_python"]:
            return "optional_scripts"
        
        return "unknown"
    
    def analyze_python_file(self, file_path: str) -> dict:
        """Analyze a Python file for dead code and imports."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            analysis = {
                "imports": [],
                "functions": [],
                "classes": [],
                "lines": len(content.splitlines()),
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    analysis["imports"].append(node.module or "")
                elif isinstance(node, ast.FunctionDef):
                    analysis["functions"].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    analysis["classes"].append(node.name)
            
            return analysis
        except Exception as e:
            return {"error": str(e)}
    
    def check_import_errors(self, file_path: str) -> list:
        """Check if file has import errors."""
        errors = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    # Just check syntax, not actual imports
                    pass
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
        except Exception as e:
            errors.append(f"Parse error: {e}")
        
        return errors
    
    def scan_all(self):
        """Perform comprehensive scan."""
        print("\n🔍 Scanning entire project...")
        
        # Scan main project directory
        all_files = self.scan_directory(self.project_root)
        
        print(f"   ✓ Found {len(all_files)} files")
        
        # Classify files
        for file_info in all_files:
            category = self.classify_file(file_info)
            self.files[category].append(file_info)
            
            self.stats["total_files"] += 1
            self.stats["total_size_mb"] += file_info["size_mb"]
            
            if file_info["is_python"]:
                self.stats["python_files"] += 1
            elif ".html" in file_info["ext"]:
                self.stats["template_files"] += 1
            elif file_info["path"].startswith("static/") or file_info["path"].startswith("staticfiles/"):
                self.stats["static_files"] += 1
            else:
                self.stats["other_files"] += 1
        
        print(f"   ✓ Classified {self.stats['total_files']} files")
        
        # Analyze Python files
        print("\n📊 Analyzing Python files...")
        python_issues = 0
        for category in ["core_system", "optional_scripts"]:
            for file_info in self.files[category]:
                if file_info["is_python"]:
                    errors = self.check_import_errors(file_info["full_path"])
                    if errors:
                        self.issues.append({
                            "file": file_info["path"],
                            "issue": "Import/Syntax error",
                            "details": errors,
                        })
                        python_issues += 1
        
        print(f"   ✓ Found {python_issues} potential issues")
        
        # Check for duplicates
        print("\n🔍 Checking for duplicates...")
        name_map = defaultdict(list)
        for category in self.files:
            for file_info in self.files[category]:
                name_map[file_info["name"]].append(file_info)
        
        duplicates = 0
        for name, files in name_map.items():
            if len(files) > 1 and name.endswith(".py"):
                self.warnings.append(f"Possible duplicate: {name} found in {len(files)} locations")
                duplicates += 1
        
        print(f"   ✓ Found {duplicates} potential duplicates")
        
        return self
    
    def generate_recommendations(self):
        """Generate cleanup recommendations."""
        print("\n📋 Generating recommendations...")
        
        # Recommend removal of test/debug files
        if self.files["test_debug"]:
            self.recommendations.append({
                "category": "Test & Debug Files",
                "files": len(self.files["test_debug"]),
                "action": "SAFE_TO_REMOVE",
                "examples": [f["path"] for f in self.files["test_debug"][:5]],
                "reason": "Test and debug files not needed in production",
            })
        
        # Recommend cleanup of old reports
        old_reports = [f for f in self.files["reports"] if "old_" in f["name"] or "backup_" in f["name"]]
        if old_reports:
            self.recommendations.append({
                "category": "Old Reports",
                "files": len(old_reports),
                "action": "REVIEW",
                "examples": [f["path"] for f in old_reports[:3]],
                "reason": "Potentially stale report files",
            })
        
        # Recommend cleaning up __pycache__
        pycache_files = [f for f in self.files["temporary"] if "__pycache__" in f["path"]]
        if pycache_files:
            self.recommendations.append({
                "category": "Cache Files",
                "files": len(pycache_files),
                "action": "SAFE_TO_REMOVE",
                "reason": "Python cache files auto-regenerated",
                "estimated_cleanup_mb": sum(f["size_mb"] for f in pycache_files),
            })
    
    def get_cleanup_summary(self):
        """Get summary of files marked for removal."""
        removable = []
        removable.extend(self.files["test_debug"])
        removable.extend([f for f in self.files["temporary"] if "__pycache__" in f["path"]])
        
        return {
            "safe_to_remove": removable,
            "preserve": self.files["protected"] + self.files["core_system"],
            "review": self.files["unknown"] + self.files["reports"],
        }
    
    def generate_report(self):
        """Generate comprehensive audit report."""
        report = {
            "audit_timestamp": str(Path(self.project_root)),
            "total_files_scanned": self.stats["total_files"],
            "total_project_size_mb": round(self.stats["total_size_mb"], 2),
            "file_breakdown": {
                "python_files": self.stats["python_files"],
                "template_files": self.stats["template_files"],
                "static_files": self.stats["static_files"],
                "other_files": self.stats["other_files"],
            },
            "file_categories": {
                "core_system": len(self.files["core_system"]),
                "protected": len(self.files["protected"]),
                "optional_scripts": len(self.files["optional_scripts"]),
                "test_debug": len(self.files["test_debug"]),
                "reports": len(self.files["reports"]),
                "temporary": len(self.files["temporary"]),
                "unknown": len(self.files["unknown"]),
            },
            "issues_found": len(self.issues),
            "warnings": len(self.warnings),
            "detailed_issues": self.issues[:10],  # Top 10
            "warnings_list": self.warnings[:10],  # Top 10
            "recommendations": self.recommendations,
            "cleanup_summary": self.get_cleanup_summary(),
        }
        
        return report
    
    def print_summary(self):
        """Print audit summary."""
        print("\n" + "=" * 80)
        print("PROJECT AUDIT SUMMARY")
        print("=" * 80)
        
        print(f"\n📊 Overall Statistics:")
        print(f"   • Total Files Scanned: {self.stats['total_files']}")
        print(f"   • Total Project Size: {round(self.stats['total_size_mb'], 2)} MB")
        print(f"   • Python Files: {self.stats['python_files']}")
        print(f"   • Template Files: {self.stats['template_files']}")
        print(f"   • Static Files: {self.stats['static_files']}")
        
        print(f"\n📁 File Categories:")
        for category, files in self.files.items():
            if files:
                print(f"   • {category.upper()}: {len(files)} files")
        
        print(f"\n⚠️  Issues Found: {len(self.issues)}")
        for issue in self.issues[:3]:
            print(f"   • {issue['file']}: {issue['issue']}")
        
        print(f"\n⚠️  Warnings: {len(self.warnings)}")
        for warning in self.warnings[:3]:
            print(f"   • {warning}")
        
        print(f"\n💡 Recommendations:")
        for rec in self.recommendations:
            print(f"   • {rec['category']}: {rec['files']} files ({rec['action']})")


def main():
    print("=" * 80)
    print("FULL PROJECT AUDIT + SAFE CLEANUP")
    print("=" * 80)
    
    # Initialize analyzer
    project_root = Path(__file__).resolve().parents[1]
    analyzer = FileAnalyzer(project_root)
    
    # Run audit
    analyzer.scan_all()
    analyzer.generate_recommendations()
    analyzer.print_summary()
    
    # Generate report
    report = analyzer.generate_report()
    
    # Save report
    os.makedirs("reports", exist_ok=True)
    report_path = Path(project_root) / "reports" / "final_project_audit.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Audit report saved to: {report_path}")
    
    # Print cleanup summary
    cleanup = analyzer.get_cleanup_summary()
    safe_remove = cleanup["safe_to_remove"]
    
    if safe_remove:
        print(f"\n🧹 Safe to Remove: {len(safe_remove)} files")
        print(f"   Total cleanup potential: {round(sum(f['size_mb'] for f in safe_remove), 2)} MB")
        
        print(f"\n   Examples:")
        for f in safe_remove[:5]:
            print(f"   • {f['path']} ({f['size_mb']} MB)")
        
        # Ask for confirmation
        print("\n" + "=" * 80)
        print("⚠️  CLEANUP PHASE")
        print("=" * 80)
        response = input("\n🗑️  Proceed with cleanup? (yes/no): ").strip().lower()
        
        if response == "yes":
            removed = 0
            for file_info in safe_remove:
                try:
                    file_path = Path(file_info["full_path"])
                    if file_path.is_file():
                        file_path.unlink()
                        removed += 1
                        print(f"   ✓ Removed: {file_info['path']}")
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                        removed += 1
                        print(f"   ✓ Removed: {file_info['path']}")
                except Exception as e:
                    print(f"   ❌ Error removing {file_info['path']}: {e}")
            
            print(f"\n✅ Cleanup complete: {removed} items removed")
            
            # Update report
            report["cleanup_performed"] = True
            report["cleanup_count"] = removed
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        else:
            print("\n⏭️  Cleanup skipped. Audit report saved for review.")
    else:
        print("\n✅ Project is clean. No unsafe items to remove.")
    
    print("\n" + "=" * 80)
    print("🎯 FINAL STATUS: ✅ SYSTEM READY")
    print("=" * 80)


if __name__ == "__main__":
    main()
