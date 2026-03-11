# LojaSync Engine

## Active Runtime

- `webapp/` - Main web application (frontend + FastAPI backend + automation APIs).
- `LLM3/` - LLM service used by romaneio and grade extraction flows.
- `modules/automation/` - ByteEmpresa automation routines.
- `modules/core/` - Shared core utilities used by the web runtime.
- `modules/config/` - Constants and theme settings used by automation/core.
- `modules/parsers/parser_grades.py` - Grade extraction parser used by backend.
- `data/` - Shared calibration/margin files used by automation (`targets.json`, `margem.json`).

## Legacy and Historical Files

- `legacy/desktop_gui/` - Old desktop Tkinter application modules and parser managers.
- `legacy/artifacts/webapp/` - Historical PyInstaller build/dist outputs.

## WebApp Internal Organization

- `webapp/docs/` - Documentation moved out of root.
- `webapp/packaging/` - Packaging scripts for executables.
- `webapp/build_package.bat` and `webapp/build_executor.bat` - Compatibility wrappers that call `webapp/packaging/`.

## Run (Development)

From `engine/webapp`:

```bat
python launcher.py
```

Default services:
- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8800`
- LLM3: `http://127.0.0.1:8002`
- LLM Monitor: `http://127.0.0.1:5174`

## Notes

- Main runtime entrypoint is `webapp/launcher.py`.
- Legacy code is preserved for reference and does not participate in current web runtime imports.
