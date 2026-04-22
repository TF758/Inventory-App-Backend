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

    file_obj.seek(0)

    df = pd.read_csv(
        file_obj,
        dtype=str,
        encoding="utf-8-sig",     # removes BOM
        sep=None,                 # auto-detect delimiter
        engine="python",
        skip_blank_lines=True,
        keep_default_na=False,
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

    # Trim whitespace in cells
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    # Remove fully blank rows
    df = df[df.apply(lambda row: any(str(v).strip() for v in row), axis=1)]

    return df