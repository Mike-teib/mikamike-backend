"""pdf_fixture.py — Génère un PDF minimal (texte latin-1) lisible par pypdf, pour les tests."""

from __future__ import annotations

from typing import List


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(pages: List[str]) -> bytes:
    """Un PDF d'une page par chaîne ; les sauts de ligne produisent des lignes distinctes."""
    objs: List[bytes] = []  # objets 1..N, dans l'ordre
    n_pages = len(pages)
    font_num = 3
    page_nums = [4 + 2 * i for i in range(n_pages)]
    kids = " ".join(f"{p} 0 R" for p in page_nums)
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode("latin-1"))
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for i, text in enumerate(pages):
        lines = text.split("\n")
        ops = ["BT", "/F1 11 Tf", "14 TL", "40 780 Td"]
        for k, line in enumerate(lines):
            if k:
                ops.append("T*")
            ops.append(f"({_escape(line)}) Tj")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_num} 0 R >> >> /Contents {page_nums[i] + 1} 0 R >>".encode("latin-1")
        )
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for num, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{num} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
