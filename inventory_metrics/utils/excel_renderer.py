from openpyxl import Workbook
from openpyxl.utils import get_column_letter


def autosize_columns(ws):
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value is not None:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max_length + 2


def render_workbook(workbook_spec: dict) -> Workbook:
    """
    Generic Excel renderer.

    workbook_spec = {
        "Sheet Name": {
            "headers": [...],
            "rows": [[...], [...]]
        }
    }
    """
    wb = Workbook()
    wb.remove(wb.active)

    for sheet_name, spec in workbook_spec.items():
        ws = wb.create_sheet(title=sheet_name)

        headers = spec.get("headers", [])
        rows = spec.get("rows", [])

        if headers:
            ws.append(headers)

        for row in rows:
            ws.append(row)

        autosize_columns(ws)

    return wb
