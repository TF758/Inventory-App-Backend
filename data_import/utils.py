import os
import uuid

from django.core.files.storage import default_storage


def store_import_upload(uploaded_file) -> str:
    ext = os.path.splitext(uploaded_file.name)[1].lower() or ".csv"
    path = f"imports/source/{uuid.uuid4().hex}{ext}"
    stored_path = default_storage.save(path, uploaded_file)
    return stored_path