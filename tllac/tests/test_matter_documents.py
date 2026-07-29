from __future__ import annotations

import asyncio
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tllac"))

from app.main import app
from app.db.db_client import DBClient
from app.routes.auth import get_current_user
from app.services import matter_document_service as mds


def _make_pdf_bytes(text: str) -> bytes:
    escaped_text = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )
    stream = f"BT /F1 18 Tf 72 720 Td ({escaped_text}) Tj ET\n"
    objects = [
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n"
            "endobj\n"
        ),
        (
            f"4 0 obj\n<< /Length {len(stream.encode('latin-1'))} >>\nstream\n"
            f"{stream}endstream\nendobj\n"
        ),
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(output))
        output.extend(obj.encode("latin-1"))

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    output.extend(
        (
            "trailer\n"
            f"<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("latin-1")
    )
    return bytes(output)


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    body = "".join(
        f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>" for paragraph in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr/></w:body>"
        "</w:document>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="xml" ContentType="application/xml"/>'
                "</Types>"
            ),
        )
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


class MatterDocumentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.upload_root = Path(self.tempdir.name) / "uploads"
        self.test_db = DBClient()
        mds.db_client = self.test_db
        os.environ["MATTER_DOCUMENT_UPLOAD_ROOT"] = str(self.upload_root)
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": "user-test",
            "email": "user@example.com",
            "full_name": "Test User",
        }

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.tempdir.cleanup()

    def _request(self, method: str, url: str, **kwargs):
        async def runner():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(runner())

    def test_upload_search_download_archive_and_delete_txt_document(self) -> None:
        upload = io.BytesIO(b"Lease agreement breach notice.\n\nSecond paragraph about payment.")
        response = self._request(
            "POST",
            "/matter-documents/upload",
            data={"matter_id": "matter-1"},
            files={"file": ("notes.txt", upload, "text/plain")},
        )
        self.assertEqual(response.status_code, 200)
        document = response.json()
        document_id = document["document_id"]
        self.assertEqual(document["matter_id"], "matter-1")
        self.assertEqual(document["status"], "active")
        self.assertGreaterEqual(document["chunk_count"], 1)

        list_response = self._request("GET", "/matter-documents", params={"matter_id": "matter-1"})
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        search_response = self._request(
            "GET",
            "/matter-documents/search",
            params={"matter_id": "matter-1", "query": "payment"},
        )
        self.assertEqual(search_response.status_code, 200)
        search_items = search_response.json()["items"]
        self.assertEqual(len(search_items), 1)
        self.assertEqual(search_items[0]["document_id"], document_id)
        self.assertEqual(search_items[0]["chunk_position"], 2)

        download_response = self._request("GET", f"/matter-documents/{document_id}/download")
        self.assertEqual(download_response.status_code, 200)
        self.assertIn(b"payment", download_response.content)

        archive_response = self._request("POST", f"/matter-documents/{document_id}/archive")
        self.assertEqual(archive_response.status_code, 200)
        self.assertEqual(archive_response.json()["status"], "archived")

        search_after_archive = self._request(
            "GET",
            "/matter-documents/search",
            params={"matter_id": "matter-1", "query": "payment"},
        )
        self.assertEqual(search_after_archive.json()["items"], [])

        metadata_response = self._request("GET", f"/matter-documents/{document_id}")
        self.assertEqual(metadata_response.status_code, 200)
        self.assertEqual(metadata_response.json()["status"], "archived")

        delete_response = self._request("DELETE", f"/matter-documents/{document_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["status"], "deleted")

        download_after_delete = self._request("GET", f"/matter-documents/{document_id}/download")
        self.assertEqual(download_after_delete.status_code, 404)

        search_after_delete = self._request(
            "GET",
            "/matter-documents/search",
            params={"matter_id": "matter-1", "query": "payment"},
        )
        self.assertEqual(search_after_delete.json()["items"], [])

    def test_rejects_unsupported_file_type(self) -> None:
        response = self._request(
            "POST",
            "/matter-documents/upload",
            data={"matter_id": "matter-1"},
            files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only PDF, DOCX, and TXT files are supported", response.text)

    def test_pdf_and_docx_extraction_preserve_source_numbers(self) -> None:
        pdf_path = Path(self.tempdir.name) / "sample.pdf"
        pdf_path.write_bytes(_make_pdf_bytes("First page text"))
        pdf_units = mds.extract_document_units(pdf_path, ".pdf")
        self.assertEqual(pdf_units[0]["page_number"], 1)
        self.assertEqual(pdf_units[0]["paragraph_number"], 1)

        docx_path = Path(self.tempdir.name) / "sample.docx"
        docx_path.write_bytes(_make_docx_bytes(["Paragraph one", "Paragraph two"]))
        docx_units = mds.extract_document_units(docx_path, ".docx")
        self.assertEqual(docx_units[0]["paragraph_number"], 1)
        self.assertEqual(docx_units[1]["paragraph_number"], 2)


if __name__ == "__main__":
    unittest.main()
