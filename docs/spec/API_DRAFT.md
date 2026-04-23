# API DRAFT (Round 2)

## Response Envelope

Success:

```json
{
  "success": true,
  "message": "ok",
  "data": {}
}
```

Error:

```json
{
  "success": false,
  "message": "not implemented yet",
  "error_code": "NOT_IMPLEMENTED"
}
```

## Endpoints

- `GET /api/v1/health`
- `POST /api/v1/system/start`
- `POST /api/v1/system/stop`
- `POST /api/v1/tasks/ingest`
- `GET /api/v1/runs`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/events`
- `GET /api/v1/runs/{run_id}/timeline`
- `GET /api/v1/runs/{run_id}/graph`
- `GET /api/v1/runs/{run_id}/report`

Bridge placeholders:

- `POST /api/v1/bridge/opencaw/tool-call`
- `POST /api/v1/bridge/opencaw/tool-result`
