# app/routes/reports.py
from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

router = APIRouter(prefix="/reports", tags=["reports"])

def _minimal_pdf_bytes(text: str) -> bytes:
    # Tiny valid PDF with `text` drawn at (50, 750)
    # Source: minimal PDF objects + /F1 Helvetica
    escaped = text.replace("(", r"\(").replace(")", r"\)")
    pdf = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length 54>>stream
BT
/F1 24 Tf
50 750 Td
({escaped}) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000115 00000 n 
0000000264 00000 n 
0000000333 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
410
%%EOF
"""
    return pdf.encode("latin-1")

@router.get("/latest")
def latest_report():
    now = datetime.now(timezone.utc).isoformat()
    return JSONResponse(
        {
            "generated_at": now,
            "summary": {
                "unread_senders": 0,
                "labels_created": 0,
                "unsubscribe_candidates": 0,
            },
            "status": "stub",
        }
    )

@router.get("/latest.pdf")
def latest_report_pdf():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    content = _minimal_pdf_bytes(f"Gmail Inbox Cleaner — Report ({now})")
    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="latest.pdf"'},
    )
