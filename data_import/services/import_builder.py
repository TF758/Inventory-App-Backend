


from data_import.factory import get_asset_importer


def build_asset_import(
    *,
    asset_type: str,
    stored_file_name: str,
    generated_by=None,
    job=None,
) -> dict:
    importer = get_asset_importer(
        asset_type,
        user=generated_by,
        job=job,
    )

    return importer.run(stored_file_name=stored_file_name)