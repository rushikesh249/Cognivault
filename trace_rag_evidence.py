"""Evidence trace for the Document RAG grounding failure (temporary diagnostic script)."""
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from backend.app.services.rag_service import RAGService
from backend.app.multimodal.ocr_service import get_ocr_service

DB = Path("data/app.db")

con = sqlite3.connect(str(DB))
con.row_factory = sqlite3.Row
cur = con.cursor()

print("=" * 80)
print("1. Document tasks in DB (most recent first)")
print("=" * 80)
rows = cur.execute(
    "SELECT task_id, title, task_type, status, prompt FROM tasks WHERE task_type='document' ORDER BY rowid DESC LIMIT 8"
).fetchall()
for r in rows:
    print(f"- [{r['status']}] {r['task_id'][:8]} | {r['title']}")
    print(f"    prompt: {(r['prompt'] or '')[:120]}")

print()
print("=" * 80)
print("2. Files + artifacts for Research Paper Analysis task")
print("=" * 80)
target = cur.execute(
    "SELECT task_id FROM tasks WHERE task_type='document' AND (title LIKE '%Research%' OR prompt LIKE '%research paper%') ORDER BY rowid DESC LIMIT 1"
).fetchone()
if target:
    tid = target["task_id"]
    print(f"task_id: {tid}")
    files = cur.execute("SELECT file_id, filename, storage_path FROM files WHERE task_id=?", (tid,)).fetchall()
    for f in files:
        print(f"  file: {f['filename']} -> {f['storage_path']}")
    arts = cur.execute("SELECT artifact_id, kind, title, storage_path, sources_json FROM artifacts WHERE task_id=?", (tid,)).fetchall()
    for a in arts:
        print(f"  artifact: [{a['kind']}] title={a['title']!r}")
        print(f"            path={a['storage_path']}")
        print(f"            sources={a['sources_json']}")
    if arts:
        docx_path = Path(arts[-1]["storage_path"])
        if docx_path.exists():
            import docx
            doc = docx.Document(str(docx_path))
            text = "\n".join(p.text for p in doc.paragraphs)
            print("  --- generated DOCX first 600 chars ---")
            print(text[:600])
else:
    print("no research paper task found")

print()
print("=" * 80)
print("2b. All recent file rows (check whether upload was linked to the task)")
print("=" * 80)
for f in cur.execute("SELECT file_id, task_id, filename FROM files ORDER BY rowid DESC LIMIT 8").fetchall():
    print(f"  {f['file_id']} | task={f['task_id']} | {f['filename']}")

print()
print("=" * 80)
print("3. OCR extraction of uploaded paper (6.3MB pdf)")
print("=" * 80)
paper = Path("data/uploads/ef7603ad-c9b9-4361-bc77-0225d6190e53.pdf")
if paper.exists():
    res = get_ocr_service().extract(paper)
    print(f"pages={res.total_pages} native={res.native_pages} scanned={res.scanned_pages} text_len={len(res.full_text)}")
    print("first 500 chars:", res.full_text[:500].replace("\n", " "))

print()
print("=" * 80)
print("4. RAG retrieval with HARDCODED query used by tool_selection")
print("=" * 80)
rag = RAGService()
hardcoded_query = "flange corrosion relief valve calibration emergency shutdown"
matches = rag.search(query=hardcoded_query, top_k=4)
print(f"query: {hardcoded_query!r} -> {len(matches)} matches")
for m in matches:
    print(f"  [score={m['score']:.3f}] {m['citation']}")
    print(f"     text: {m['text'][:110]}...")

print()
print("=" * 80)
print("5. RAG retrieval with research-paper-style query (what SHOULD happen)")
print("=" * 80)
matches2 = rag.search(query="multimodal emotion recognition affective computing deep learning benchmark", top_k=4)
print(f"-> {len(matches2)} matches above threshold 0.55 (irrelevant KB chunks correctly dropped)")
for m in matches2:
    print(f"  [score={m['score']:.3f}] {m['citation']}")

con.close()
