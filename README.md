# ComfyUI_ALEXZ_SilentFilm

Самостоятельный ComfyUI custom node package для пайплайна Silent Film.

## Состояние

Основной перенос backend, frontend, тестов и документации завершён. Пакет регистрирует Silent Film-ноды и маршруты самостоятельно; `ComfyUI_ALEXZ_tools` больше не регистрирует их и не загружает связанные frontend-расширения.

Публичные `class_type`, имена входов/выходов, `film_json` и workflow-контракты сохранены. Существующие графы продолжают работать при установленном пакете.

Исходный репозиторий и базовый коммит указаны в [ORIGIN.md](ORIGIN.md).

## Установка

Установите [ComfyUI_ALEXZ_SilentFilm](https://github.com/AlexZ1967/ComfyUI_ALEXZ_SilentFilm) как отдельный custom node package рядом с `ComfyUI_ALEXZ_tools` в `ComfyUI/custom_nodes/`:

```bash
cd /путь/к/ComfyUI/custom_nodes
git clone https://github.com/AlexZ1967/ComfyUI_ALEXZ_SilentFilm.git
```

Оба пакета используются в рабочем окружении проекта: ALEXZ_tools предоставляет общий Module Node Picker и сохранение workflow, а SilentFilm — обработку и video I/O. Сам SilentFilm не импортирует ALEXZ_tools и может выполнять свои ноды без него. Установите зависимости тем же Python, которым запускается ComfyUI:

```bash
python -m pip install -r requirements.txt
```

Команда выполняется из каталога SilentFilm. PyTorch берётся из окружения ComfyUI; пакет не устанавливает другую CUDA-сборку. После установки перезапустите ComfyUI.

Для загрузки и записи видео нужны `ffmpeg` и `ffprobe` в PATH процесса ComfyUI. Можно задать полные пути через `ALEXZ_FFMPEG` и `ALEXZ_FFPROBE`. Runtime JavaScript уже поставляется в `web/`; npm-пакеты нужны только для проверки TypeScript и пересборки frontend.

Установка на Windows, включая ComfyUI Portable, настройка SSD-кэша и проверка переноса описаны в [гайде платформенной совместимости](guides/GUIDE_PLATFORM_COMPATIBILITY.md). Conda и Make не являются требованиями для работы нод.

## Workflow с дефектами

Актуальный пользовательский вариант: [Видео-в-Хронику-по-этапам_with_defects.json](workflows/Видео-в-Хронику-по-этапам_with_defects.json). Перенесён из ALEXZ_tools с сохранением настроек; перед запуском выберите свой исходный видеофайл.

## Проверки и сборка frontend

Перед первой проверкой или сборкой установите локальные npm-зависимости пакета:

```bash
npm install
```

Это установит закреплённые версии TypeScript и esbuild из `package.json`. Повторять установку после изменений Python-кода не нужно.

```bash
make test
make frontend-build
```

Makefile по умолчанию использует локальное Conda environment разработчика `p313-torch214-cu132`. Для другого окружения можно передать `CONDA_ENV=имя` либо `CONDA_RUN=` для текущего Python. Команды без Make для Windows приведены в гайде платформенной совместимости. Browser smoke выполняется пользователем вручную через Playwright MCP по `guides/GUIDE_BROWSER_SMOKE.md` после перезапуска ComfyUI.
