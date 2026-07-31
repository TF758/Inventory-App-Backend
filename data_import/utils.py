import csv
import io
import os
import uuid

import pandas as pd
from django.core.files.storage import default_storage


def store_import_upload(uploaded_file) -> str:
    ext = os.path.splitext(uploaded_file.name)[1].lower() or ".csv"
    path = f"imports/source/{uuid.uuid4().hex}{ext}"
    stored_path = default_storage.save(path, uploaded_file)
    return stored_path


def delete_import_upload(stored_file_name: str) -> bool:
    if not stored_file_name:
        return False
    if not default_storage.exists(stored_file_name):
        return False
    default_storage.delete(stored_file_name)
    return True


def load_and_normalize_csv(file_obj):
    file_obj.seek(0)

    # Django storage backends normally return a binary stream for ``rb``.
    # Pandas' Python CSV engine delegates delimiter detection to csv.Sniffer,
    # which expects text and raises TypeError when it receives bytes. Wrap the
    # storage stream without taking ownership of it so the caller can close it.
    text_stream = file_obj
    detach_text_wrapper = False

    if isinstance(file_obj.read(0), (bytes, bytearray)):
        text_stream = io.TextIOWrapper(
            file_obj,
            encoding="utf-8-sig",
            newline="",
        )
        detach_text_wrapper = True

    try:
        # Restrict delimiter detection to supported CSV separators. Unbounded
        # Sniffer detection can incorrectly choose a letter as the delimiter
        # for valid one-column files. Default to comma when no separator is
        # present in the sample.
        sample = text_stream.read(8192)
        text_stream.seek(0)

        try:
            delimiter = csv.Sniffer().sniff(
                sample,
                delimiters=",;\t|",
            ).delimiter
        except csv.Error:
            delimiter = ","

        df = pd.read_csv(
            text_stream,
            dtype=str,
            sep=delimiter,
            engine="python",
            skip_blank_lines=True,
            keep_default_na=False,
        )
    finally:
        if detach_text_wrapper:
            text_stream.detach()

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