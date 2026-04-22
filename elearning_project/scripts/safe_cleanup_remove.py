"""
Safe Cleanup - Remove identified unnecessary files
Runs automatically without user input
"""

import json
import os
import shutil
from pathlib import Path

def main():
    project_root = Path(__file__).resolve().parents[1]
    audit_file = project_root / "reports" / "final_project_audit.json"
    
    if not audit_file.exists():
        print("❌ Audit report not found. Run full_project_audit_cleanup.py first.")
        return
    
    print("=" * 80)
    print("AUTOMATED CLEANUP - SAFE FILE REMOVAL")
    print("=" * 80)
    
    # Load audit report
    with open(audit_file, "r", encoding="utf-8") as f:
        report = json.load(f)
    
    safe_to_remove = report.get("cleanup_summary", {}).get("safe_to_remove", [])
    
    print(f"\n🧹 Removing {len(safe_to_remove)} identified files...")
    
    removed = 0
    errors = []
    
    for file_info in safe_to_remove:
        file_path = Path(file_info["full_path"])
        try:
            if file_path.is_file():
                file_path.unlink()
                print(f"   ✓ Removed: {file_info['path']}")
                removed += 1
            elif file_path.is_dir():
                shutil.rmtree(file_path)
                print(f"   ✓ Removed: {file_info['path']}/")
                removed += 1
        except Exception as e:
            error_msg = f"Error removing {file_info['path']}: {e}"
            errors.append(error_msg)
            print(f"   ❌ {error_msg}")
    
    print(f"\n✅ Cleanup Complete!")
    print(f"   • Files removed: {removed}")
    print(f"   • Errors: {len(errors)}")
    
    if errors:
        print(f"\n⚠️  Cleanup Errors:")
        for err in errors:
            print(f"   • {err}")
    
    # Update audit report
    report["cleanup_performed"] = True
    report["cleanup_count"] = removed
    report["cleanup_errors"] = len(errors)
    
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Audit report updated: {audit_file}")
    
    print("\n" + "=" * 80)
    print("🎯 CLEANUP STATUS: ✅ COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
