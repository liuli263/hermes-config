---
name: ocr-and-documents
description: Extract text from PDFs and scanned documents. Use web_extract for remote URLs, pymupdf for local text-based PDFs, marker-pdf for OCR/scanned docs. For DOCX use python-docx, for PPTX see the powerpoint skill.
version: 2.3.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [PDF, Documents, Research, Arxiv, Text-Extraction, OCR]
    related_skills: [powerpoint]
---

# PDF & Document Extraction

For DOCX: use `python-docx` when available (parses actual document structure, far better than OCR). If `python-docx` is unavailable and installing packages is undesirable, use the dependency-free OOXML fallback below.
For PPTX: see the `powerpoint` skill (uses `python-pptx` with full slide/notes support).
This skill covers **PDFs and scanned documents**.

## DOCX fallback without python-docx

DOCX files are ZIP archives containing XML under `word/document.xml`. This fallback is useful for quick contract/document edits when `python-docx` is missing.

**Inspect paragraph text:**
```bash
TMP=$(mktemp -d)
unzip -q input.docx -d "$TMP"
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
root=ET.parse(Path('$TMP')/'word/document.xml').getroot()
for i,p in enumerate(root.findall('.//w:p', ns)):
    text=''.join(t.text or '' for t in p.findall('.//w:t', ns))
    if text.strip(): print(i, text)
PY
```

**Edit paragraph text while preserving formatting as much as possible:**
```python
from pathlib import Path
import zipfile, shutil, tempfile, xml.etree.ElementTree as ET
src=Path('input.docx'); out=Path('output.docx')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
ET.register_namespace('w', ns['w'])
shutil.copy2(src,out)
with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    with zipfile.ZipFile(out) as z: z.extractall(td)
    docxml=td/'word/document.xml'
    tree=ET.parse(docxml); root=tree.getroot()
    def p_text(p): return ''.join(t.text or '' for t in p.findall('.//w:t', ns))
    def set_p_text(p, text):
        ts=p.findall('.//w:t', ns)
        if not ts: return False
        ts[0].text=text
        for t in ts[1:]: t.text=''
        return True
    replacements={'old paragraph text':'new paragraph text'}
    for p in root.findall('.//w:p', ns):
        txt=p_text(p).strip()
        if txt in replacements: set_p_text(p, replacements[txt])
    docxml.write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))
    tmp=out.with_suffix('.tmp.docx')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for f in td.rglob('*'):
            if f.is_file(): z.write(f, f.relative_to(td).as_posix())
    tmp.replace(out)
```

**Verification:** unzip the edited DOCX and assert key strings exist in `word/document.xml` text. For Chinese contract edits, verify exact party names, addresses, clause titles, and updated cooperation-field wording before returning the file.

Limitations: this fallback is best for replacing whole paragraphs or contiguous text runs. It can disturb complex run-level formatting inside a paragraph because it writes the full new text into the first `w:t` and clears remaining runs. For heavily formatted documents or tracked changes, install/use `python-docx` or LibreOffice automation instead.

## Step 1: Remote URL Available?

If the document has a URL, **always try `web_extract` first**:

```
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
web_extract(urls=["https://example.com/report.pdf"])
```

This handles PDF-to-markdown conversion via Firecrawl with no local dependencies.

Only use local extraction when: the file is local, web_extract fails, or you need batch processing.

## Step 2: Choose Local Extractor

| Feature | pymupdf (~25MB) | marker-pdf (~3-5GB) |
|---------|-----------------|---------------------|
| **Text-based PDF** | ✅ | ✅ |
| **Scanned PDF (OCR)** | ❌ | ✅ (90+ languages) |
| **Tables** | ✅ (basic) | ✅ (high accuracy) |
| **Equations / LaTeX** | ❌ | ✅ |
| **Code blocks** | ❌ | ✅ |
| **Forms** | ❌ | ✅ |
| **Headers/footers removal** | ❌ | ✅ |
| **Reading order detection** | ❌ | ✅ |
| **Images extraction** | ✅ (embedded) | ✅ (with context) |
| **Images → text (OCR)** | ❌ | ✅ |
| **EPUB** | ✅ | ✅ |
| **Markdown output** | ✅ (via pymupdf4llm) | ✅ (native, higher quality) |
| **Install size** | ~25MB | ~3-5GB (PyTorch + models) |
| **Speed** | Instant | ~1-14s/page (CPU), ~0.2s/page (GPU) |

**Decision**: Use pymupdf unless you need OCR, equations, forms, or complex layout analysis.

If the user needs marker capabilities but the system lacks ~5GB free disk:
> "This document needs OCR/advanced extraction (marker-pdf), which requires ~5GB for PyTorch and models. Your system has [X]GB free. Options: free up space, provide a URL so I can use web_extract, or I can try pymupdf which works for text-based PDFs but not scanned documents or equations."

---

## pymupdf (lightweight)

```bash
pip install pymupdf pymupdf4llm
```

**Via helper script**:
```bash
python scripts/extract_pymupdf.py document.pdf              # Plain text
python scripts/extract_pymupdf.py document.pdf --markdown    # Markdown
python scripts/extract_pymupdf.py document.pdf --tables      # Tables
python scripts/extract_pymupdf.py document.pdf --images out/ # Extract images
python scripts/extract_pymupdf.py document.pdf --metadata    # Title, author, pages
python scripts/extract_pymupdf.py document.pdf --pages 0-4   # Specific pages
```

**Inline**:
```bash
python3 -c "
import pymupdf
doc = pymupdf.open('document.pdf')
for page in doc:
    print(page.get_text())
"
```

---

## marker-pdf (high-quality OCR)

```bash
# Check disk space first
python scripts/extract_marker.py --check

pip install marker-pdf
```

**Via helper script**:
```bash
python scripts/extract_marker.py document.pdf                # Markdown
python scripts/extract_marker.py document.pdf --json         # JSON with metadata
python scripts/extract_marker.py document.pdf --output_dir out/  # Save images
python scripts/extract_marker.py scanned.pdf                 # Scanned PDF (OCR)
python scripts/extract_marker.py document.pdf --use_llm      # LLM-boosted accuracy
```

**CLI** (installed with marker-pdf):
```bash
marker_single document.pdf --output_dir ./output
marker /path/to/folder --workers 4    # Batch
```

---

## Arxiv Papers

```
# Abstract only (fast)
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Full paper
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])

# Search
web_search(query="arxiv GRPO reinforcement learning 2026")
```

## Split, Merge & Search

pymupdf handles these natively — use `execute_code` or inline Python:

```python
# Split: extract pages 1-5 to a new PDF
import pymupdf
doc = pymupdf.open("report.pdf")
new = pymupdf.open()
for i in range(5):
    new.insert_pdf(doc, from_page=i, to_page=i)
new.save("pages_1-5.pdf")
```

```python
# Merge multiple PDFs
import pymupdf
result = pymupdf.open()
for path in ["a.pdf", "b.pdf", "c.pdf"]:
    result.insert_pdf(pymupdf.open(path))
result.save("merged.pdf")
```

```python
# Search for text across all pages
import pymupdf
doc = pymupdf.open("report.pdf")
for i, page in enumerate(doc):
    results = page.search_for("revenue")
    if results:
        print(f"Page {i+1}: {len(results)} match(es)")
        print(page.get_text("text"))
```

No extra dependencies needed — pymupdf covers split, merge, search, and text extraction in one package.

---

## Notes

- `web_extract` is always first choice for URLs
- pymupdf is the safe default — instant, no models, works everywhere
- marker-pdf is for OCR, scanned docs, equations, complex layouts — install only when needed
- Both helper scripts accept `--help` for full usage
- marker-pdf downloads ~2.5GB of models to `~/.cache/huggingface/` on first use
- For Word docs: `pip install python-docx` (better than OCR — parses actual structure)
- For PowerPoint: see the `powerpoint` skill (uses python-pptx)
