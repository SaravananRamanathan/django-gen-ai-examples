"""
Service for processing Google Calendar event attachments.
Usage:
    from chat_bot.services.attachment_service import attachment_service
    extracted_text, method = attachment_service.process_attachment(attachment_data, google_token, refresh_token)
"""

import io
import logging
from typing import Optional, Tuple

import docx
import PyPDF2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from chat_bot.const import GoogleOAuth2

logger = logging.getLogger(__name__)


class AttachmentProcessingService:
    """
    Service for downloading and extracting text from calendar event attachments.
    """

    def __init__(self):
        self.supported_mime_types = {
            "application/pdf": self._extract_pdf_text,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": self._extract_docx_text,
            "application/msword": self._extract_doc_text,
            "text/plain": self._extract_plain_text,
            "application/vnd.google-apps.document": self._extract_google_doc_text,
            "application/vnd.google-apps.presentation": self._extract_google_slides_text,
            "application/vnd.google-apps.spreadsheet": self._extract_google_sheets_text,
        }

    def process_attachment(
        self, attachment_data: dict, google_token: str, refresh_token: str
    ) -> Tuple[Optional[str], str]:
        """
        Process a single attachment and extract text content.

        Args:
            attachment_data: Attachment metadata from Google Calendar API
            google_token: Google OAuth access token
            refresh_token: Google OAuth refresh token

        Returns:
            Tuple of (extracted_text, extraction_method)
        """
        file_id = attachment_data.get("fileId")
        mime_type = attachment_data.get("mimeType", "")
        title = attachment_data.get("title", "Unknown")

        logger.info(f"Processing attachment: {title} (type: {mime_type})")

        if not file_id:
            logger.warning(f"No file ID found for attachment: {title}")
            return None, "no_file_id"

        if mime_type not in self.supported_mime_types:
            logger.warning(f"Unsupported mime type {mime_type} for attachment: {title}")
            return None, "unsupported_type"

        try:
            # Download the file content
            file_content = self._download_file(file_id, mime_type, google_token, refresh_token)
            if not file_content:
                return None, "download_failed"

            # Extract text based on mime type
            extractor = self.supported_mime_types[mime_type]
            extracted_text = extractor(file_content, mime_type)

            if extracted_text:
                logger.info(f"Successfully extracted {len(extracted_text)} characters from {title}")
                return extracted_text, self._get_extraction_method(mime_type)
            else:
                logger.warning(f"No text extracted from {title}")
                return None, "extraction_failed"

        except Exception as e:
            logger.error(f"Error processing attachment {title}: {e}")
            return None, "processing_error"

    def _download_file(self, file_id: str, mime_type: str, google_token: str, refresh_token: str) -> Optional[bytes]:
        """Download file content from Google Drive."""
        try:
            credentials = GoogleOAuth2.get_credentials(token=google_token, refresh_token=refresh_token)
            drive_service = build("drive", "v3", credentials=credentials)

            # For Google Workspace files, export to appropriate format
            if mime_type.startswith("application/vnd.google-apps"):
                export_mime_type = self._get_export_mime_type(mime_type)
                if export_mime_type:
                    request = drive_service.files().export_media(fileId=file_id, mimeType=export_mime_type)
                else:
                    logger.error(f"No export format available for {mime_type}")
                    return None
            else:
                request = drive_service.files().get_media(fileId=file_id)

            file_content = request.execute()
            return file_content

        except HttpError as e:
            logger.error(f"Google Drive API error downloading file {file_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return None

    def _get_export_mime_type(self, google_mime_type: str) -> Optional[str]:
        """Get appropriate export mime type for Google Workspace files."""
        export_map = {
            "application/vnd.google-apps.document": "text/plain",
            "application/vnd.google-apps.presentation": "text/plain",
            "application/vnd.google-apps.spreadsheet": "text/csv",
        }
        return export_map.get(google_mime_type)

    def _extract_pdf_text(self, file_content: bytes, mime_type: str) -> Optional[str]:
        """Extract text from PDF files."""
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text_parts = []
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())

            return "\n".join(text_parts).strip()

        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return None

    def _extract_docx_text(self, file_content: bytes, mime_type: str) -> Optional[str]:
        """Extract text from DOCX files."""
        try:
            doc_file = io.BytesIO(file_content)
            doc = docx.Document(doc_file)

            text_parts = []
            for paragraph in doc.paragraphs:
                text_parts.append(paragraph.text)

            return "\n".join(text_parts).strip()

        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return None

    def _extract_doc_text(self, file_content: bytes, mime_type: str) -> Optional[str]:
        """Extract text from legacy DOC files."""
        # Note: This would require python-docx2txt or similar library
        # For now, return None and log
        logger.warning("Legacy DOC file extraction not implemented")
        return None

    def _extract_plain_text(self, file_content: bytes, mime_type: str) -> Optional[str]:
        """Extract text from plain text files."""
        try:
            return file_content.decode("utf-8").strip()
        except UnicodeDecodeError:
            try:
                return file_content.decode("latin-1").strip()
            except Exception as e:
                logger.error(f"Error decoding plain text: {e}")
                return None

    def _extract_google_doc_text(self, file_content: bytes, mime_type: str) -> Optional[str]:
        """Extract text from Google Docs (exported as plain text)."""
        return self._extract_plain_text(file_content, mime_type)

    def _extract_google_slides_text(self, file_content: bytes, mime_type: str) -> Optional[str]:
        """Extract text from Google Slides (exported as plain text)."""
        return self._extract_plain_text(file_content, mime_type)

    def _extract_google_sheets_text(self, file_content: bytes, mime_type: str) -> Optional[str]:
        """Extract text from Google Sheets (exported as CSV)."""
        try:
            csv_content = file_content.decode("utf-8")
            # Convert CSV to readable text format
            lines = csv_content.strip().split("\n")
            formatted_lines = []

            for line in lines:
                # Simple CSV parsing - replace commas with tabs for readability
                formatted_line = line.replace(",", "\t")
                formatted_lines.append(formatted_line)

            return "\n".join(formatted_lines)

        except Exception as e:
            logger.error(f"Error extracting Google Sheets text: {e}")
            return None

    def _get_extraction_method(self, mime_type: str) -> str:
        """Get extraction method name for a given mime type."""
        method_map = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/msword": "doc",
            "text/plain": "text",
            "application/vnd.google-apps.document": "google_doc",
            "application/vnd.google-apps.presentation": "google_slides",
            "application/vnd.google-apps.spreadsheet": "google_sheets",
        }
        return method_map.get(mime_type, "unknown")


# import attachment_service to use in other modules.
attachment_service = AttachmentProcessingService()
