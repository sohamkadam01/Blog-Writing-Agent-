# Blog Writing Agent Frontend

Install and run from this folder:

```powershell
npm install
npm run dev
```

Start the backend first from the project root:

```powershell
python -m uvicorn Backend.api:app --reload --host 127.0.0.1 --port 8010
```

The app expects the backend API at `http://127.0.0.1:8010` by default.
