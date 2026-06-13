# Application Architecture

The application now starts through `app/main.py`. `Quote.py` remains a small
compatibility launcher so existing shortcuts and PyInstaller commands continue
to work.

## Layers

- `app/ui`: PyQt widgets and the main window. Widgets call application APIs and
  do not execute SQL.
- `app/models`: Typed customer, quotation, invoice, and line-item data.
- `app/repositories`: Focused SQLite persistence operations.
- `app/database`: Database lifecycle, compatibility facade, and ordered schema
  migrations.
- `app/services`: Quotation/invoice workflows and shared Decimal-based tax,
  discount, and rounding rules.
- `app/pdf`: Document-generation infrastructure.
- `app/container.py`: Creates and wires dependencies in one place.

## Compatibility Boundary

`quotation_tool.py` remains temporarily as the proven implementation for older
quotation, invoice, and PDF workflows. New modules adapt it behind clear layer
boundaries. This keeps current documents and database behavior stable while
allowing those remaining implementations to be extracted incrementally.

The large widgets currently live in `app/ui/legacy.py` and are exported through
focused modules such as `customers_tab.py` and `invoices_tab.py`. Future UI
changes can move one class at a time without changing imports elsewhere.

## Running

```powershell
.\.venv\Scripts\python.exe Quote.py
```

The package entry point is also available:

```powershell
.\.venv\Scripts\python.exe -m app.main
```

## Verification

```powershell
.\.venv\Scripts\python.exe test_before_build.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
