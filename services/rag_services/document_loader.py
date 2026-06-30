from pypdf import PdfReader
from typing import Tuple

DOC_RUNNING_HEADER = "Promotion Profiles" 
DOCUMENT_PATH = "documents/promotion_profiles.pdf"
def _isPageFooter(line: str):
    l = line.strip()
    return l.startswith("Page ") and l[len("Page "):].isdigit()

def _load_pdf() -> str:
    reader = PdfReader(DOCUMENT_PATH)
    pages = [page.extract_text() for page in reader.pages] 
    full_text = " \n".join(pages)
    
    lines = full_text.split("\n")
    clean_text = [
        l for l in lines
        if l.strip() != DOC_RUNNING_HEADER and not _isPageFooter(l)
    ]
    return "\n".join(clean_text) 

def _parse_promotion_details(line: str) -> Tuple[int, str, str, str] | None:
    # Promotion ID 10 · Percentage Off · 2025-11-05 to 2025-11-20
    if not line.startswith("Promotion ID "):
        return None

    rest = line[len("Promotion ID "):]
    promotion_data = rest.split(" · ")
    if len(promotion_data) != 3:
        return None
    promo_id, disc_type, time_span = promotion_data 

    if " to " not in time_span:
        return None
    
    if not promo_id.isdigit():
        return None
    
    star_date, end_date = time_span.split(" to ")
    return int(promo_id), disc_type.strip(), star_date.strip(), end_date.strip()

def _chunk_by_heading(doc: str) -> list[dict]:
    lines = doc.split("\n")
    anchors = []
    for idx, line in enumerate(lines):
        parsed = _parse_promotion_details(line)
        if parsed is not None:
            anchors.append((idx, *parsed))
    
    chunks = []
    for idx, (line_idx, promo_id, promo_type, start_date, end_date) in enumerate(anchors):
        title = None 
        for i in range(line_idx-1, -1, -1):
            if lines[i].strip():
                title = lines[i].strip()
                break
        
        body_start_idx = line_idx + 1
        body_end_idx = None
        line_hit_count = 0
        if idx == len(anchors) -1:
            body_end_idx = len(lines)
        else:
            for i in range(anchors[idx + 1][0]-1, -1, -1):
                if lines[i].strip():
                    line_hit_count += 1
                    if line_hit_count > 1:
                        body_end_idx = i+1
                        break
        
        body = " ".join(lines[body_start_idx:body_end_idx]) 
        chunks.append({
            "id": promo_id,
            "text": f"{title}.{body}",
            "meta_data": {
                "promo_id": promo_id,
                "promo_title": title,
                "promo_type": promo_type,
                "promo_start_date": start_date,
                "promo_end_date": end_date
            }
        })

    return chunks

def load_document_as_chunks() -> list[dict]:
    docs = _load_pdf()
    return _chunk_by_heading(docs)
    