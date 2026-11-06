# Browser smoke Silent Film

Сценарий проверяет загрузку пяти frontend-расширений и наличие 17 backend-ноды через read-only `GET /object_info`. Он не ставит ноды в workflow и не запускает рендер. Запросы к prompt/queue/install/update и загрузке видео блокируются.

Запускайте после перезапуска ComfyUI с обоими пакетами (`ComfyUI_ALEXZ_tools` и `ComfyUI_ALEXZ_SilentFilm`). В Playwright MCP используйте `browser_run_code_unsafe` с параметром `filename`:

```text
tests/browser/silent_film_smoke.js
```

Ожидаемый результат — `PASS` для загрузки ComfyUI, frontend extensions и всех 17 нод. Ошибки сторонних расширений учитывайте отдельно от URL и стека, указывающих на `ComfyUI_ALEXZ_SilentFilm`.
