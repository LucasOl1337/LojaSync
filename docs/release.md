# Release

Execute SOMENTE com ordem explicita do dono.

1. Atualize a versao em `pyproject.toml`, `frontend-ts/package.json`, `frontend-ts/package-lock.json` e `app/interfaces/api/http/app.py`.
2. Gere o contrato:

```powershell
python tools/export_openapi.py
```

3. Valide:

```powershell
python -m pytest
cd frontend-ts
npm run test:logic
npm run build
cd ..
git diff --check
```

4. Confirme que `frontend-ts/dist/` corresponde a `frontend-ts/src/` e que `README.md` contem `Release atual: vX.Y.Z`.
5. Revise o diff e os arquivos ignorados antes de criar commit, tag ou GitHub Release.

`tests/test_release_metadata.py` verifica a mesma versao no backend, frontend, OpenAPI e README. `patchatt.bat` atualiza outro checkout com `git pull --ff-only origin main` e recusa arvore suja.
