"""Read uploaded images in memory only: never a temporary file on disk.

FastAPI's UploadFile would copy files over 1 MB to a temporary file on disk:
the body is read here instead, with a size limit, and the parser is told to
keep everything in memory.
"""

from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.requests import Request

MAX_PARTS = 20  # safety: more files than this is not a normal request


class UploadRejected(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


async def read_files(request: Request, field: str, max_files: int, max_request_bytes: int,
                     missing: str, too_large: str, too_many: str) -> list[bytes]:
    """The files sent in `field` (1 to max_files), as bytes."""
    if not request.headers.get("content-type", "").startswith("multipart/form-data"):
        raise UploadRejected(400, "photo_manquante", missing)
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > max_request_bytes:
        raise UploadRejected(413, "trop_lourde", too_large)

    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > max_request_bytes:
            raise UploadRejected(413, "trop_lourde", too_large)

    async def stream():
        yield bytes(body)

    parser = MultiPartParser(request.headers, stream(), max_files=MAX_PARTS, max_fields=10)
    parser.spool_max_size = max_request_bytes  # never roll over to a file on disk
    try:
        form = await parser.parse()
    except MultiPartException:
        raise UploadRejected(400, "photo_manquante", missing) from None
    try:
        uploads = [u for u in form.getlist(field) if not isinstance(u, str)]
        if not uploads:
            raise UploadRejected(400, "photo_manquante", missing)
        if len(uploads) > max_files:
            raise UploadRejected(413, "trop_de_pages", too_many)
        return [await upload.read() for upload in uploads]
    finally:
        await form.close()
