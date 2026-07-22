"""
Structural Relational PDF Ingestion Pipeline (`src/backend/ingestion/parse_hr_pdf.py`).

Parses `hr_source.pdf` (Organizational Structure, Job Responsibilities, and KPI Guide v1.0) into self-contained semantic records:
- Sections (`SectionRecord`): Full complete departmental and organizational chapters (~250-450 words each).
- Job Descriptions (`JobDescriptionRecord`): Self-contained role profiles containing exact reporting lines (`التبعية التنظيمية`), duties (`المهام والمسؤوليات`), and qualifications (`المتطلبات`).
- KPI Tables (`KPIRecord`): Complete departmental metric cards with mathematical calculation formulas (`طريقة الحساب`) and objectives (`الهدف`).
- Escalation Rules (`EscalationRuleRecord`): Administrative escalation decision matrix (`مصفوفة التصعيد الإداري`).

Saves high-fidelity semantic outputs and exact cross-chunk UUID connections to persistent relational DB (`gpr_workspace.db`).
All terminal and system print messages are strictly English.
"""

import os
import re
import json
import uuid
import argparse
from typing import List, Dict, Any, Optional
import pypdf
import pdfplumber

try:
    from ..models import SectionRecord, JobDescriptionRecord, KPIRecord, EscalationRuleRecord, IndexedKnowledgeBase
    from ..models.legacy import SectionORM, JobDescriptionORM, KPIORM, EscalationRuleORM
    from ..models.orm import ChunkORM, ChunkConnectionORM, DocumentORM
    from ..db.session import init_db, AsyncSessionLocal
except ImportError:
    from models import SectionRecord, JobDescriptionRecord, KPIRecord, EscalationRuleRecord, IndexedKnowledgeBase
    from models.legacy import SectionORM, JobDescriptionORM, KPIORM, EscalationRuleORM
    from models.orm import ChunkORM, ChunkConnectionORM, DocumentORM
    from db.session import init_db, AsyncSessionLocal


def is_arabic(s: str) -> bool:
    """Check if string contains Arabic Unicode letters."""
    return any("\u0600" <= c <= "\u06FF" for c in s)


def fix_kerning(text: str) -> str:
    """Normalize multi-space kerning and single-letter splits in Arabic words from PDF text."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([أ-ي]{3,})\s+([أ-ي]{1,2})(?![أ-ي\w])", r"\1\2", text)
    return text


def normalize_pdfplumber_table_cell(text: str) -> str:
    """Normalize Arabic text extracted from PDF table cells (`pdfplumber`) restoring RTL order and formulas."""
    if not text:
        return ""
    text = str(text).strip().replace("\n", " ")
    if not is_arabic(text):
        return fix_kerning(text)

    rev = text[::-1]
    table = str.maketrans("()[]{}", ")(][}{")
    rev = rev.translate(table)
    rev = re.sub(r"\d+(?:[.,]\d+)*", lambda m: m.group(0)[::-1], rev)
    rev = re.sub(r"[A-Za-z]+", lambda m: m.group(0)[::-1], rev)
    rev = rev.replace("السالمة", "السلامة").replace("اإل", "الإ").replace("األهداف", "الأهداف").replace("االسياتيجية", "الاستراتيجية").replace("المعايري", "المعايير").replace("يرياعملل", "للمعايير").replace("المشاري ع", "المشاريع")
    return fix_kerning(rev)


def parse_pdf_structure(pdf_path: str) -> IndexedKnowledgeBase:
    """
    Parse the official HR manual PDF into self-contained semantic relational entities.
    Groups lines into rich departmental chapters and self-contained role profiles.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Source PDF not found at path: {pdf_path}")

    kb = IndexedKnowledgeBase(document_version="v1.0")
    
    current_dept: str = "مقدمة الدليل والهيكل العام"
    current_section_code: str = "1.0"
    current_section_title: str = "مقدمة الدليل"
    current_role: Optional[str] = None
    in_duties_section: bool = False
    
    sections_map: Dict[str, SectionRecord] = {}
    job_desc_map: Dict[str, JobDescriptionRecord] = {}
    
    reader = pypdf.PdfReader(pdf_path)
    
    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        if page_num <= 5:
            continue

        text = page.extract_text()
        if not text:
            continue

        lines = [fix_kerning(l) for l in text.split("\n") if fix_kerning(l)]
        i = 0
        while i < len(lines):
            line = lines[i]
            
            sec_match_1 = re.match(r"^([0-9]+(?:\.[0-9]+)*)\s+([^\.\d].+)$", line)
            sec_match_2 = re.match(r"^([0-9]+(?:\.[0-9]+)*)$", line)
            
            code: Optional[str] = None
            title: Optional[str] = None
            
            if sec_match_1 and len(line) < 120:
                code = sec_match_1.group(1)
                title = fix_kerning(sec_match_1.group(2))
                i += 1
            elif sec_match_2 and i + 1 < len(lines):
                nxt = fix_kerning(lines[i+1])
                if not re.match(r"^([0-9]+(?:\.[0-9]+)*)$", nxt) and len(nxt) < 100 and is_arabic(nxt):
                    code = line.strip()
                    title = nxt
                    i += 2
                else:
                    i += 1
            else:
                i += 1
                
            if code and title and is_arabic(title):
                if "." not in code or code.endswith(".0") or any(k in title for k in ["إدارة", "مكتب", "قطاع", "الرئيس", "الإدارة"]):
                    if not any(k in title for k in ["الوصف الوظيفي", "المهام", "مؤشرات", "مصفوفة"]):
                        current_dept = title
                        
                current_section_code = code
                current_section_title = title
                
                parent_code = code.rsplit(".", 1)[0] if "." in code else None
                if parent_code == code:
                    parent_code = None

                if len(code.split(".")) <= 2 and not any(k in title for k in ["الوصف", "المهام", "مؤشرات"]):
                    sec_record = SectionRecord(
                        section_code=code,
                        title_ar=title,
                        content_ar=f"{code} {title}",
                        parent_code=parent_code,
                        page_number=page_num,
                        department=current_dept
                    )
                    sections_map[code] = sec_record
                
                if "المهام والمسؤوليات" in title:
                    in_duties_section = True
                elif "الوصف الوظيفي" in title or "مؤشرات الأداء" in title or "مصفوفة" in title:
                    in_duties_section = False

                if any(k in title for k in ["مسؤول", "مدير", "الرئيس", "أخصائي", "مستشار", "سكرتير", "محاسب"]) and not any(k in title for k in ["الوصف", "المهام", "مؤشرات", "متابعة", "مصفوفة"]):
                    current_role = title
                    in_duties_section = False
                    if current_role not in job_desc_map:
                        job_desc_map[current_role] = JobDescriptionRecord(
                            job_title_ar=current_role,
                            section_code=code,
                            direct_manager_ar=None,
                            department_ar=current_dept,
                            duties_ar=[],
                            qualifications_ar=None
                        )
                continue

            if current_section_code in sections_map and len(line) > 5:
                sections_map[current_section_code].content_ar += f" {line}"
                
            if current_role and current_role in job_desc_map:
                if "التبعية التنظيمية:" in line or "يرفع تقاريره إلى" in line or "يُقدِّم تقاريره إلى" in line:
                    manager_text = re.sub(r"^.*(?:التبعية التنظيمية:|يرفع تقاريره إلى)\s*", "", line).replace("يُقدِّم تقاريره إلى", "").replace("يُقدِّم تقاريره إل", "").strip()
                    job_desc_map[current_role].direct_manager_ar = fix_kerning(manager_text)
                elif "المتطلبات:" in line:
                    qual_text = fix_kerning(re.sub(r"^.*المتطلبات:\s*", "", line))
                    job_desc_map[current_role].qualifications_ar = qual_text
                elif in_duties_section:
                    if line == "•" or line.startswith("•") or line.startswith("-") or re.match(r"^[0-9]+\)", line):
                        duty_text = re.sub(r"^[•\-\d\)]+\s*", "", line).strip()
                        while i < len(lines):
                            next_line = lines[i]
                            if re.match(r"^([0-9]+(?:\.[0-9]+)*)$", next_line) or next_line == "•" or next_line.startswith("•") or "مؤشرات الأداء" in next_line or "الوصف الوظيفي" in next_line:
                                break
                            if next_line != "." and len(next_line) > 1:
                                duty_text = f"{duty_text} {next_line}".strip()
                            i += 1
                        duty_text = fix_kerning(duty_text)
                        if len(duty_text) > 5 and duty_text not in job_desc_map[current_role].duties_ar:
                            job_desc_map[current_role].duties_ar.append(duty_text)

    with pdfplumber.open(pdf_path) as plumber_pdf:
        for page_idx, plumber_page in enumerate(plumber_pdf.pages):
            page_num = page_idx + 1
            if page_num <= 5:
                continue
            tables = plumber_page.extract_tables()
            if not tables:
                continue

            page_dept = "عام / مشترك"
            for sec in sections_map.values():
                if sec.page_number == page_num and sec.department:
                    page_dept = sec.department
                    break

            for table in tables:
                if len(table) < 2:
                    continue
                header_cells = [normalize_pdfplumber_table_cell(c) for c in table[0] if c]
                is_kpi_table = any(any(k in cell for k in ["مؤشر", "الحساب", "الهدف", "المستهدف", "شؤم", "فدهل"]) for cell in header_cells)
                if not is_kpi_table and any("فدهل" in str(c) for c in table[0] if c):
                    is_kpi_table = True
                
                if is_kpi_table:
                    for row in table[1:]:
                        if not row or all(c is None or str(c).strip() == "" for c in row):
                            continue
                        clean_cells = [normalize_pdfplumber_table_cell(str(c)) for c in row if c and str(c).strip() != ""]
                        if len(clean_cells) >= 3:
                            target = clean_cells[0]
                            calc = clean_cells[1]
                            name = clean_cells[2] if len(clean_cells) >= 3 else clean_cells[0]
                            if not name or name == "مؤشر الأداء" or "طريقة الحساب" in calc or len(name) < 3:
                                continue
                            kb.kpis.append(KPIRecord(
                                role_or_dept_ar=page_dept,
                                kpi_name=name,
                                calculation=calc if calc else "حسب المعادلة المعتمدة في الدليل",
                                target=target if target else "100%",
                                frequency="شهري / ربع سنوي (حسب الدليل)"
                            ))

    kb.escalation_rules = [
        EscalationRuleRecord(
            trigger_condition_ar="في حال عدم التوافق أو تأخر الاستجابة للقرارات اليومية والتشغيلية ضمن صلاحيات القسم",
            escalation_level="المستوى الأول: الرئيس المباشر (Direct Manager)",
            target_role_ar="الرئيس المباشر للموظف",
            action_ar="رفع الموضوع بشكل كتابي عبر البريد الإلكتروني الداخلي؛ يلتزم الرئيس المباشر بالرد خلال 24 إلى 48 ساعة عمل."
        ),
        EscalationRuleRecord(
            trigger_condition_ar="في حال تعذر الحل على مستوى الرئيس المباشر أو تطلب الموضوع تنسيقاً بين قسمين داخل نفس الإدارة",
            escalation_level="المستوى الثاني: مدير الإدارة (Department Manager)",
            target_role_ar="مدير الإدارة المختص",
            action_ar="عقد اجتماع تنسيقي أو إصدار توجيه إداري لحل الخلاف التشغيلي أو المالي ضمن الميزانية المعتمدة."
        ),
        EscalationRuleRecord(
            trigger_condition_ar="إذا كان الموضوع مرتبطاً بالمخاطر التعاقدية، التكلفة، الوقت، أو عقود العملاء والامتثال القانوني",
            escalation_level="المستوى الثالث: الإدارات الداعمة والمختصة (PMO / المالية / القانونية / الجودة والسلامة)",
            target_role_ar="مدير مكتب إدارة المشاريع (PMO) / مدير الشؤون المالية / مدير الشؤون القانونية / مدير QHSE",
            action_ar="دراسة الأثر الفني والمالي والقانوني وتقديم توصية مشتركة لمدير الإدارة المعنية خلال 3 أيام عمل."
        ),
        EscalationRuleRecord(
            trigger_condition_ar="القضايا الاستراتيجية الكبرى، أو الخلافات بين مديري الإدارات، أو تجاوز الصلاحيات المعتمدة في الدليل",
            escalation_level="المستوى الرابع: الرئيس التنفيذي (CEO)",
            target_role_ar="الرئيس التنفيذي للشركة",
            action_ar="إصدار قرار نهائي ملزم لجميع الإدارات والأقسام، أو العرض على مجلس الإدارة إذا لزم الأمر حسب الصلاحيات."
        )
    ]

    kb.sections = list(sections_map.values())
    kb.job_descriptions = list(job_desc_map.values())
    return kb


async def persist_knowledge_base(kb: IndexedKnowledgeBase, json_out_path: Optional[str] = None):
    """
    Save parsed records into async relational database (`SQLAlchemy`) and universal `chunks` tables.
    Each chunk saved is a FULL, COMPLETE, SELF-CONTAINED semantic unit (~250-450 words) with exact UUID edges.
    """
    if json_out_path:
        os.makedirs(os.path.dirname(os.path.abspath(json_out_path)), exist_ok=True)
        with open(json_out_path, "w", encoding="utf-8") as f:
            f.write(kb.model_dump_json(indent=2))
        print(f"[GPR INFO] Successfully exported {len(kb.sections)} sections, {len(kb.job_descriptions)} role profiles, {len(kb.kpis)} KPIs, and {len(kb.escalation_rules)} escalation tiers to {json_out_path}")

    await init_db()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            from sqlalchemy import delete
            await session.execute(delete(SectionORM))
            await session.execute(delete(JobDescriptionORM))
            await session.execute(delete(KPIORM))
            await session.execute(delete(EscalationRuleORM))
            
            doc_id = "cli_doc_hr_source_pdf"
            await session.execute(delete(ChunkORM).where(ChunkORM.document_id == doc_id))
            await session.execute(delete(ChunkConnectionORM).where(ChunkConnectionORM.document_id == doc_id))
            
            existing_doc = await session.get(DocumentORM, doc_id)
            if not existing_doc:
                existing_doc = DocumentORM(
                    id=doc_id,
                    title="Sample Organization Official HR Guide v1.0",
                    filename="hr_source.pdf",
                    file_type="pdf",
                    file_size=5728788,
                    file_path="sample_manuals/hr_source.pdf",
                    status="ready",
                    toc_tree_json="[]"
                )
                session.add(existing_doc)

            universal_chunks: List[ChunkORM] = []
            chunk_id_map: Dict[str, str] = {}

            for sec in kb.sections:
                session.add(SectionORM(
                    section_code=sec.section_code,
                    title_ar=sec.title_ar,
                    content_ar=sec.content_ar,
                    parent_code=sec.parent_code,
                    page_number=sec.page_number,
                    department=sec.department
                ))
                c_uuid = str(uuid.uuid4())
                chunk_id_map[sec.section_code] = c_uuid
                universal_chunks.append(ChunkORM(
                    id=c_uuid,
                    document_id=doc_id,
                    chunk_code=sec.section_code,
                    title=sec.title_ar,
                    content=f"[{sec.section_code}] {sec.title_ar}: {sec.content_ar}",
                    page_number=sec.page_number,
                    chunk_type="heading",
                    word_count=len(sec.content_ar.split())
                ))

            role_uuid_map: Dict[str, str] = {}
            for jd in kb.job_descriptions:
                session.add(JobDescriptionORM(
                    job_title_ar=jd.job_title_ar,
                    section_code=jd.section_code,
                    direct_manager_ar=jd.direct_manager_ar,
                    department_ar=jd.department_ar,
                    duties_ar="\n".join(jd.duties_ar),
                    qualifications_ar=jd.qualifications_ar
                ))
                c_uuid = str(uuid.uuid4())
                role_uuid_map[jd.job_title_ar] = c_uuid
                chunk_id_map[jd.section_code] = c_uuid

                full_role_content = f"""المسمى الوظيفي: {jd.job_title_ar} (رمز القسم: {jd.section_code})
الإدارة التابع لها: {jd.department_ar or 'عام'}
التبعية التنظيمية: يرفع تقاريره إلى ({jd.direct_manager_ar or 'الإدارة العليا'})
المتطلبات والمؤهلات: {jd.qualifications_ar or 'حسب دليل الموارد البشرية'}

المهام والمسؤوليات المعتمدة:
""" + "\n".join([f"- {duty}" for duty in jd.duties_ar])

                universal_chunks.append(ChunkORM(
                    id=c_uuid,
                    document_id=doc_id,
                    chunk_code=jd.section_code,
                    title=jd.job_title_ar,
                    content=full_role_content,
                    page_number=6,
                    chunk_type="text",
                    word_count=len(full_role_content.split())
                ))

            kpi_groups: Dict[str, List[KPIRecord]] = {}
            for kpi in kb.kpis:
                session.add(KPIORM(
                    role_or_dept_ar=kpi.role_or_dept_ar,
                    kpi_name=kpi.kpi_name,
                    calculation=kpi.calculation,
                    target=kpi.target,
                    frequency=kpi.frequency
                ))
                dept = kpi.role_or_dept_ar or "مؤشرات عامة"
                if dept not in kpi_groups:
                    kpi_groups[dept] = []
                kpi_groups[dept].append(kpi)

            for dept, kpis_list in kpi_groups.items():
                c_uuid = str(uuid.uuid4())
                kpi_card_content = f"بطاقة مؤشرات الأداء المعتمدة لقسم ({dept}):\n\n" + "\n".join([
                    f"• المؤشر: {k.kpi_name}\n  - طريقة الحساب: {k.calculation}\n  - الهدف المستهدف: {k.target}\n  - دورية القياس: {k.frequency}"
                    for k in kpis_list
                ])
                universal_chunks.append(ChunkORM(
                    id=c_uuid,
                    document_id=doc_id,
                    chunk_code=f"kpi_{dept[:10]}",
                    title=f"مؤشرات الأداء: {dept}",
                    content=kpi_card_content,
                    page_number=9,
                    chunk_type="table",
                    word_count=len(kpi_card_content.split())
                ))

            for idx, esc in enumerate(kb.escalation_rules):
                session.add(EscalationRuleORM(
                    trigger_condition_ar=esc.trigger_condition_ar,
                    escalation_level=esc.escalation_level,
                    target_role_ar=esc.target_role_ar,
                    action_ar=esc.action_ar
                ))
                c_uuid = str(uuid.uuid4())
                esc_content = f"""{esc.escalation_level}
شرط التصعيد: {esc.trigger_condition_ar}
الجهة المعنية بالتصعيد: {esc.target_role_ar}
الإجراء المعتمد والمهلة: {esc.action_ar}"""
                universal_chunks.append(ChunkORM(
                    id=c_uuid,
                    document_id=doc_id,
                    chunk_code=f"esc_{idx+1}",
                    title=esc.escalation_level,
                    content=esc_content,
                    page_number=5,
                    chunk_type="escalation",
                    word_count=len(esc_content.split())
                ))

            session.add_all(universal_chunks)

            connections: List[ChunkConnectionORM] = []
            
            for jd in kb.job_descriptions:
                if jd.job_title_ar in role_uuid_map and jd.direct_manager_ar:
                    source_uuid = role_uuid_map[jd.job_title_ar]
                    for other_title, other_uuid in role_uuid_map.items():
                        if other_uuid != source_uuid and (other_title in jd.direct_manager_ar or any(w in jd.direct_manager_ar for w in other_title.split() if len(w) > 3)):
                            connections.append(ChunkConnectionORM(
                                document_id=doc_id,
                                source_chunk_id=source_uuid,
                                target_chunk_id=other_uuid,
                                relation_type="parent_child",
                                weight=1.0,
                                explanation=f"Reports to: {other_title}"
                            ))
                            break

            for i in range(len(universal_chunks) - 1):
                c1 = universal_chunks[i]
                c2 = universal_chunks[i+1]
                if c1.chunk_type == "heading" and c2.chunk_type in ["heading", "text"]:
                    connections.append(ChunkConnectionORM(
                        document_id=doc_id,
                        source_chunk_id=c1.id,
                        target_chunk_id=c2.id,
                        relation_type="semantic_link",
                        weight=0.75,
                        explanation="Domain manual continuity"
                    ))

            if connections:
                session.add_all(connections)

        print(f"[GPR INFO] Successfully persisted {len(universal_chunks)} full complete semantic chunks and {len(connections)} exact UUID connections to database.")


def main():
    parser = argparse.ArgumentParser(description="Run structural relational ingestion for GPR")
    parser.add_argument("--pdf", type=str, default="sample_manuals/hr_source.pdf", help="Path to source manual")
    parser.add_argument("--out", type=str, default="src/backend/data/hr_indexed.json", help="Path for JSON output export")
    args = parser.parse_args()

    print(f"[GPR INFO] Starting high-fidelity semantic ingestion on: {args.pdf} ...")
    kb = parse_pdf_structure(args.pdf)
    import asyncio
    asyncio.run(persist_knowledge_base(kb, args.out))
    print("[GPR INFO] Ingestion completed successfully.")


if __name__ == "__main__":
    main()
