import os
import uuid
from django.core.files.storage import default_storage


def store_import_upload(uploaded_file) -> str:
    ext = os.path.splitext(uploaded_file.name)[1].lower() or ".csv"
    path = f"imports/source/{uuid.uuid4().hex}{ext}"
    stored_path = default_storage.save(path, uploaded_file)
    return stored_path


import pandas as pd


def load_and_normalize_csv(file_obj):

    # Always start with a clean pointer
    file_obj.seek(0)

    # First attempt: normal comma CSV
    df = pd.read_csv(
        file_obj,
        dtype=str,
        sep=",",
        encoding="utf-8-sig",
        skip_blank_lines=True,
    )
    df = df.fillna("")

    # If pandas treated the first row as header incorrectly
    required = {"name", "brand", "model", "serial_number", "status", "room"}

    detected_headers = {c.lower().strip() for c in df.columns}

    if not required.issubset(detected_headers):

        # Reset file pointer and force header detection
        file_obj.seek(0)

        df = pd.read_csv(
            file_obj,
            dtype=str,
            sep=",",
            encoding="utf-8-sig",
            header=0,
            skip_blank_lines=True,
        )

    if df.empty:
        raise ValueError("CSV file must include a header row.")

    # Normalize headers
    df.columns = (
        df.columns
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
        .str.lower()
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
    )

    # Remove Excel junk columns
    df = df.loc[:, ~df.columns.str.contains("^unnamed", case=False)]

    # Trim whitespace
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    # Remove empty rows
    df = df.dropna(how="all")

    # print("Detected columns:", df.columns.tolist())

    return df