"""
Final System Validation & Health Check
Verify chatbot, database, and core functionality after cleanup
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django
django.setup()

from django.db import connection
from django.test import Client
from django.contrib.auth import get_user_model
from courses.models import Subject, Unit, Lesson
from chatbot.models import PDFPageChunk, ReferencePDF
from chatbot.models import ChatQuery

def check_database():
    """Check database integrity and content."""
    print("\n📊 Database Health Check:")
    checks = {
        "subjects": 0,
        "units": 0,
        "lessons": 0,
        "reference_pdfs": 0,
        "pdf_chunks": 0,
        "chat_queries": 0,
        "active_pdfs": 0,
    }
    
    try:
        checks["subjects"] = Subject.objects.filter(is_active=True).count()
        checks["units"] = Unit.objects.filter(is_active=True).count()
        checks["lessons"] = Lesson.objects.filter(is_active=True).count()
        checks["reference_pdfs"] = ReferencePDF.objects.count()
        checks["pdf_chunks"] = PDFPageChunk.objects.count()
        checks["chat_queries"] = ChatQuery.objects.count()
        checks["active_pdfs"] = ReferencePDF.objects.filter(is_active=True).count()
        
        print(f"   ✅ Subjects (active): {checks['subjects']}")
        print(f"   ✅ Units (active): {checks['units']}")
        print(f"   ✅ Lessons (active): {checks['lessons']}")
        print(f"   ✅ Reference PDFs: {checks['reference_pdfs']}")
        print(f"   ✅ Active PDFs: {checks['active_pdfs']}")
        print(f"   ✅ PDF Chunks: {checks['pdf_chunks']}")
        print(f"   ✅ Chat Queries: {checks['chat_queries']}")
        
        # Check for critical content
        if checks["subjects"] == 0:
            return {"status": "CRITICAL", "message": "No subjects found", "details": checks}
        if checks["pdf_chunks"] == 0:
            return {"status": "WARNING", "message": "No PDF chunks found", "details": checks}
        
        return {"status": "OK", "message": "Database healthy", "details": checks}
    except Exception as e:
        return {"status": "ERROR", "message": str(e), "details": None}


def check_core_files():
    """Verify core project files exist."""
    print("\n📁 Core Files Verification:")
    
    core_files = [
        "chatbot/models.py",
        "chatbot/views.py",
        "chatbot/services/search_service.py",
        "chatbot/services/answer_service.py",
        "chatbot/services/pdf_processor.py",
        "courses/models.py",
        "accounts/models.py",
        "progress/models.py",
        "elearning_project/settings.py",
        "elearning_project/urls.py",
        "manage.py",
    ]
    
    missing = []
    for file_path in core_files:
        full_path = BASE_DIR / file_path
        if full_path.exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - MISSING")
            missing.append(file_path)
    
    if missing:
        return {"status": "ERROR", "message": "Core files missing", "files": missing}
    return {"status": "OK", "message": "All core files present"}


def check_chatbot_api():
    """Test chatbot API endpoint."""
    print("\n🤖 Chatbot API Test:")
    
    try:
        User = get_user_model()
        user = User.objects.filter(is_active=True).first()
        
        if not user:
            return {"status": "WARNING", "message": "No active user for testing"}
        
        client = Client()
        client.force_login(user)
        
        # Test simple question
        response = client.post("/chat/stream/", data={
            "question": "What is cloud computing?",
            "scope": "global",
        }, secure=True)
        
        if response.status_code == 200:
            print(f"   ✅ Endpoint responds (HTTP 200)")
            print(f"   ✅ User authenticated")
            return {"status": "OK", "message": "Chatbot API functional", "http_status": 200}
        else:
            print(f"   ❌ Unexpected HTTP {response.status_code}")
            return {"status": "ERROR", "message": f"HTTP {response.status_code}", "http_status": response.status_code}
    except Exception as e:
        print(f"   ❌ Error testing API: {e}")
        return {"status": "ERROR", "message": str(e)}


def check_pdf_pipeline():
    """Verify PDF ingestion pipeline."""
    print("\n📄 PDF Pipeline Check:")
    
    try:
        active_pdfs = ReferencePDF.objects.filter(is_active=True).count()
        total_pdfs = ReferencePDF.objects.count()
        chunks = PDFPageChunk.objects.count()
        broken_pdfs = ReferencePDF.objects.filter(
            processing_status="FAILED"
        ).count()
        
        print(f"   ✅ Active PDFs: {active_pdfs}")
        print(f"   ✅ Total PDFs: {total_pdfs}")
        print(f"   ✅ PDF Chunks: {chunks}")
        print(f"   ✅ Failed PDFs: {broken_pdfs}")
        
        if chunks == 0:
            return {"status": "WARNING", "message": "No PDF chunks indexed"}
        
        return {
            "status": "OK",
            "message": "PDF pipeline operational",
            "active_pdfs": active_pdfs,
            "total_pdfs": total_pdfs,
            "chunks": chunks,
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


def check_templates_static():
    """Verify templates and static files."""
    print("\n🎨 Templates & Static Files:")
    
    template_dir = BASE_DIR / "templates"
    static_dir = BASE_DIR / "static"
    staticfiles_dir = BASE_DIR / "staticfiles"
    
    checks = {
        "templates": len(list(template_dir.glob("*.html"))) if template_dir.exists() else 0,
        "static": len(list(static_dir.rglob("*"))) if static_dir.exists() else 0,
        "staticfiles": len(list(staticfiles_dir.rglob("*"))) if staticfiles_dir.exists() else 0,
    }
    
    print(f"   ✅ Template files: {checks['templates']}")
    print(f"   ✅ Static assets: {checks['static']}")
    print(f"   ✅ Collected static files: {checks['staticfiles']}")
    
    return {
        "status": "OK" if checks["templates"] > 0 else "WARNING",
        "message": "Templates and static files verified",
        "details": checks,
    }


def check_scripts():
    """List available scripts."""
    print("\n🔧 Available Scripts:")
    
    scripts_dir = BASE_DIR / "scripts"
    scripts = []
    
    if scripts_dir.exists():
        for script in scripts_dir.glob("*.py"):
            if not script.name.startswith("__"):
                scripts.append(script.name)
                if len(scripts) <= 10:
                    print(f"   • {script.name}")
        
        if len(scripts) > 10:
            print(f"   ... and {len(scripts) - 10} more")
    
    return {"status": "OK", "script_count": len(scripts)}


def check_audit_reports():
    """List available reports."""
    print("\n📈 Available Reports:")
    
    reports_dir = BASE_DIR / "reports"
    reports = []
    
    if reports_dir.exists():
        for report in reports_dir.glob("*.json"):
            reports.append(report.name)
            size_mb = report.stat().st_size / (1024 * 1024)
            print(f"   • {report.name} ({round(size_mb, 2)} MB)")
    
    return {"status": "OK", "report_count": len(reports), "reports": reports}


def main():
    print("=" * 80)
    print("FINAL SYSTEM VALIDATION & HEALTH CHECK")
    print("=" * 80)
    
    results = {
        "timestamp": str(Path(BASE_DIR).stat().st_mtime),
        "checks": {},
        "overall_status": "UNKNOWN",
        "issues": [],
    }
    
    # Run all checks
    print("\n🔍 Running comprehensive health checks...\n")
    
    checks = [
        ("Core Files", check_core_files),
        ("Database", check_database),
        ("Chatbot API", check_chatbot_api),
        ("PDF Pipeline", check_pdf_pipeline),
        ("Templates & Static", check_templates_static),
        ("Scripts", check_scripts),
        ("Reports", check_audit_reports),
    ]
    
    all_ok = True
    for check_name, check_func in checks:
        try:
            result = check_func()
            results["checks"][check_name] = result
            
            if result.get("status") == "ERROR":
                all_ok = False
                results["issues"].append(f"{check_name}: {result.get('message')}")
            elif result.get("status") == "WARNING":
                results["issues"].append(f"{check_name}: {result.get('message')}")
        except Exception as e:
            results["checks"][check_name] = {"status": "ERROR", "message": str(e)}
            all_ok = False
            results["issues"].append(f"{check_name}: {str(e)}")
    
    # Determine overall status
    if all_ok:
        results["overall_status"] = "✅ CLEAN & STABLE"
    elif any(c.get("status") == "ERROR" for c in results["checks"].values()):
        results["overall_status"] = "⚠️  ISSUES FOUND"
    else:
        results["overall_status"] = "⚠️  WARNINGS"
    
    # Save results
    os.makedirs("reports", exist_ok=True)
    results_file = Path(BASE_DIR) / "reports" / "system_health_check.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 80)
    print("🎯 SYSTEM STATUS")
    print("=" * 80)
    print(f"\n{results['overall_status']}")
    
    if results["issues"]:
        print(f"\n⚠️  Issues Found:")
        for issue in results["issues"]:
            print(f"   • {issue}")
    else:
        print(f"\n✨ System is healthy and ready for production!")
    
    print(f"\n📋 Full report saved to: {results_file}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
