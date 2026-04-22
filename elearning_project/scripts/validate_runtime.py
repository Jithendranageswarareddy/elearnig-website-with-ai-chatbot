import os
import sys
import traceback

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning_project.settings')

results = {
    'model_integrity': False,
    'relationship_integrity': False,
    'strict_chat_enforcement': False,
    'permission_enforcement': False,
    'template_integrity': False,
}

try:
    import django
    django.setup()
    from django.db import transaction
    from django.test import Client
    from django.contrib.auth import get_user_model
    from django.urls import reverse

    # STEP 1 - Model Integrity
    try:
        from courses.models import Semester, Subject
        from chatbot.models import ReferencePDF, PDFPageChunk
        s_count = Semester.objects.count()
        sub_count = Subject.objects.count()
        pdf_count = ReferencePDF.objects.count()
        chunk_count = PDFPageChunk.objects.count()
        print('Semester.objects.count()', s_count)
        print('Subject.objects.count()', sub_count)
        print('ReferencePDF.objects.count()', pdf_count)
        print('PDFPageChunk.objects.count()', chunk_count)
        results['model_integrity'] = True
    except Exception as e:
        print("ERROR:", str(e))
        print('Model integrity check failed:')
        traceback.print_exc()
        results['model_integrity'] = False

    # STEP 2 - Relationship Validation
    rel_ok = True
    try:
        first_pdf = ReferencePDF.objects.first()
        if not first_pdf:
            print('No ReferencePDF rows to test relationships')
            rel_ok = False
        else:
            # attributes
            for attr in ('subject', 'uploaded_by', 'status', 'is_syllabus_reference'):
                if not hasattr(first_pdf, attr):
                    print(f'ReferencePDF missing attribute: {attr}')
                    rel_ok = False
            first_chunk = PDFPageChunk.objects.first()
            if not first_chunk:
                print('No PDFPageChunk rows to test')
                rel_ok = False
            else:
                if not hasattr(first_chunk, 'reference_pdf'):
                    print('PDFPageChunk missing reference_pdf')
                    rel_ok = False
                else:
                    if not hasattr(first_chunk.reference_pdf, 'subject'):
                        print('chunk.reference_pdf missing subject')
                        rel_ok = False
    except Exception as e:
        print("ERROR:", str(e))
        print('Relationship validation exception:')
        traceback.print_exc()
        rel_ok = False
    results['relationship_integrity'] = rel_ok
    print('Relationship integrity:', rel_ok)

    # STEP 3 - Strict Chat Test
    strict_ok = True
    try:
        from chatbot.services.search_service import search_chunks
        # Case A: query unlikely to match
        res_a = search_chunks('zxqv_nonexistent_term_12345')
        print('Case A result count (expect 0):', len(res_a) if res_a is not None else 'None')
        if res_a:
            strict_ok = False
            print('Case A failed: unexpected results returned')
        # Case B: pick text from an existing approved chunk
        approved_chunk = PDFPageChunk.objects.filter(
            reference_pdf__status=ReferencePDF.Status.APPROVED,
            reference_pdf__is_syllabus_reference=True,
        ).first()
        if not approved_chunk:
            print('No approved syllabus ReferencePDF chunks found for Case B - strict mode tests cannot fully validate')
            # attempt to use any chunk
            any_chunk = PDFPageChunk.objects.first()
            if not any_chunk:
                strict_ok = False
            else:
                query = any_chunk.text_content.split()[:5]
                query = ' '.join(query) if query else 'test'
                res_b = search_chunks(query)
                # ensure none of results are from unapproved PDFs
                for c in res_b or []:
                    if c.reference_pdf.status != ReferencePDF.Status.APPROVED:
                        print('Case B failed: returned chunk from unapproved PDF')
                        strict_ok = False
        else:
            query = ' '.join(approved_chunk.text_content.split()[:6])
            res_b = search_chunks(query)
            print('Case B result count (expect >=1):', len(res_b) if res_b is not None else 'None')
            if not res_b:
                print('Case B failed: no results for query from approved chunk')
                strict_ok = False
            else:
                # ensure all returned chunks are from approved syllabus PDFs
                for c in res_b:
                    if not (
                        c.reference_pdf.status == ReferencePDF.Status.APPROVED
                        and c.reference_pdf.is_syllabus_reference
                    ):
                        print('Case B failed: returned chunk from non-approved or non-syllabus PDF')
                        strict_ok = False
        # Case C: filter by a specific ReferencePDF
        ref_pdf = ReferencePDF.objects.filter(
            status=ReferencePDF.Status.APPROVED,
            is_syllabus_reference=True,
        ).first()
        if ref_pdf:
            # use first 5 words from one of its chunks
            rchunk = PDFPageChunk.objects.filter(reference_pdf=ref_pdf).first()
            if rchunk:
                q = ' '.join(rchunk.text_content.split()[:6])
                res_c = search_chunks(q, reference_pdf=ref_pdf)
                print('Case C result count (expect >=1 from same PDF):', len(res_c) if res_c is not None else 'None')
                for c in res_c or []:
                    if c.reference_pdf_id != ref_pdf.id:
                        print('Case C failed: returned chunk from different PDF', c.reference_pdf_id)
                        strict_ok = False
            else:
                print('Case C skipped: no chunk for selected approved ReferencePDF')
        else:
            print('Case C skipped: no approved ReferencePDF available')
    except Exception as e:
        print("ERROR:", str(e))
        print('Strict chat test failed with exception:')
        traceback.print_exc()
        strict_ok = False
    results['strict_chat_enforcement'] = strict_ok
    print('Strict chat enforcement:', strict_ok)

    # STEP 4 - Permission Test
    perm_ok = True
    try:
        # Read upload_pdf view decorators by inspecting source
        import inspect
        from chatbot import views as chatbot_views
        src = inspect.getsource(chatbot_views)
        if 'def upload_pdf' not in src:
            print('upload_pdf view not found in chatbot.views')
            perm_ok = False
        else:
            # ensure decorators include login_required and faculty_required in either order
            lines = src.splitlines()
            deco_lines = []
            for l in lines:
                if l.strip().startswith('@'):
                    deco_lines.append(l.strip())
                if l.strip().startswith('def upload_pdf'):
                    break
            if '@login_required' not in ' '.join(deco_lines) or '@faculty_required' not in ' '.join(deco_lines):
                print('upload_pdf missing required decorators:', deco_lines)
                perm_ok = False
        # Use Django test client to ensure non-staff cannot access
        User = get_user_model()
        # create or get a non-staff user; fields may vary so use create_user if available
        try:
            u = User.objects.filter(is_staff=False).first()
            if u is None:
                # try to use manager create_user
                if hasattr(User.objects, 'create_user'):
                    u = User.objects.create_user(email='student@example.com', password='testpass', is_staff=False)
                else:
                    u = User.objects.create(is_staff=False)
        except Exception as e:
            print("ERROR:", str(e))
            u = User.objects.create(is_staff=False)
        client = Client()
        # force login irrespective of credentials
        client.force_login(u)
        # find upload url
        try:
            upload_url = reverse('upload_pdf')
        except Exception as e:
            print("ERROR:", str(e))
            # fallback common path
            upload_url = '/chatbot/upload_pdf/'
        resp = client.get(upload_url)
        # expect redirect or forbidden
        if resp.status_code in (200,):
            print('Permission test failed: non-staff user accessed upload page (status 200)')
            perm_ok = False
        else:
            print('Permission test response status for non-staff user:', resp.status_code)
        # Verify unapproved PDFs not returned by search when strict=True
        unapproved = ReferencePDF.objects.exclude(status=ReferencePDF.Status.APPROVED).filter(
            is_syllabus_reference=True
        ).first()
        if unapproved:
            uchunk = PDFPageChunk.objects.filter(reference_pdf=unapproved).first()
            if uchunk:
                q = ' '.join(uchunk.text_content.split()[:6])
                r = search_chunks(q)
                # ensure none of returned chunks belong to unapproved pdf
                for c in r or []:
                    if c.reference_pdf_id == unapproved.id:
                        print('Permission test failed: search returned chunk from unapproved PDF')
                        perm_ok = False
        results['permission_enforcement'] = perm_ok
    except Exception as e:
        print("ERROR:", str(e))
        print('Permission tests raised exception:')
        traceback.print_exc()
        perm_ok = False
        results['permission_enforcement'] = False
    print('Permission enforcement:', perm_ok)

    # STEP 5 - Template Validation
    template_ok = True
    try:
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        missing_extends = []
        missing_blocks = []
        hardcoded_links = []
        for root, dirs, files in os.walk(templates_dir):
            for fn in files:
                if not fn.endswith('.html'):
                    continue
                path = os.path.join(root, fn)
                if os.path.basename(path) == 'base.html':
                    continue
                with open(path, 'r', encoding='utf-8') as f:
                    txt = f.read()
                if "{% extends 'base.html' %}" not in txt and '{% extends "base.html" %}' not in txt:
                    missing_extends.append(path)
                if '{% block content %}' not in txt or '{% endblock %}' not in txt:
                    missing_blocks.append(path)
                # naive hardcoded url check
                if 'href="/' in txt or "action='/'" in txt or 'href=\"/' in txt:
                    hardcoded_links.append(path)
        if missing_extends:
            print('Templates missing base.html extend (examples):', missing_extends[:5])
            template_ok = False
        if missing_blocks:
            print('Templates missing content block (examples):', missing_blocks[:5])
            template_ok = False
        if not missing_extends and not missing_blocks:
            print('All templates extend base.html and contain content block')
        if hardcoded_links:
            print('Templates with potential hardcoded absolute URLs (examples):', hardcoded_links[:5])
        results['template_integrity'] = template_ok
    except Exception as e:
        print("ERROR:", str(e))
        print('Template validation failed:')
        traceback.print_exc()
        results['template_integrity'] = False

    # Final aggregation
    print('\nFINAL SUMMARY')
    print('Model Integrity:', 'PASS' if results['model_integrity'] else 'FAIL')
    print('Relationship Integrity:', 'PASS' if results['relationship_integrity'] else 'FAIL')
    print('Strict Chat Enforcement:', 'PASS' if results['strict_chat_enforcement'] else 'FAIL')
    print('Permission Enforcement:', 'PASS' if results['permission_enforcement'] else 'FAIL')
    print('Template Integrity:', 'PASS' if results['template_integrity'] else 'FAIL')

    overall = 'STABLE' if all(results.values()) else 'UNSTABLE'
    print('Overall System Status:', overall)
    # Completion % heuristic: proportion of PASS items
    pass_count = sum(1 for v in results.values() if v)
    total = len(results)
    completion_pct = int((pass_count/total)*100)
    print('Real Completion %:', f'{completion_pct}%')
    # Technical score heuristic
    tech_score = int((pass_count/total)*9) + 1
    print('Technical Score (1-10):', tech_score)
    vision = 'YES' if all(results.values()) else 'NO'
    print('Academic vision satisfied?', vision)

except Exception as e:
    print("ERROR:", str(e))
    print('Unexpected error during validation runner:')
    traceback.print_exc()
    sys.exit(1)
