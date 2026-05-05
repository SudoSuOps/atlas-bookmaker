#!/usr/bin/env python3
"""
agent/tools/pdf_parse.py · PDF → markdown via Docling + Granite-Vision.

Per Plan agent's IBM ref findings: Granite-Docling-258M and Granite-Vision-4.1-4B
are NOT chained directly. Docling-258M emits DocTags directly · Vision-4.1-4B
plugs into the Docling library as the table-structure backend.

Reference: https://github.com/docling-project/docling/blob/v2.90.0/docs/examples/granite_vision_table_structure.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Convert a PDF to structured markdown + table dataframes."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        GraniteVisionTableStructureOptions,
        PdfPipelineOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions()
    opts.do_table_structure = True
    opts.table_structure_options = GraniteVisionTableStructureOptions()

    conv = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)},
    )
    res = conv.convert(str(pdf_path))

    tables = []
    for t in res.document.tables:
        try:
            df = t.export_to_dataframe(doc=res.document)
            tables.append({"markdown": df.to_markdown(), "json": df.to_dict(orient="records")})
        except Exception as e:
            tables.append({"error": str(e)[:200]})

    return {
        "markdown": res.document.export_to_markdown(),
        "tables": tables,
        "page_count": len(res.document.pages),
    }


class PdfParseTool:
    name = "pdf_parse"
    description = (
        "Parse a PDF (rent roll · T-12 · STNL lease · survey) into structured "
        "markdown + table dataframes using Docling + Granite-Vision. Returns dict "
        "with 'markdown', 'tables', 'page_count'."
    )

    def run(self, pdf_path: str) -> dict[str, Any]:
        return parse_pdf(pdf_path)
