# Платформенная совместимость и установка на Windows

## Статус

SilentFilm использует Python, PyTorch, NumPy, OpenCV и FFmpeg. Работа нод не требует Linux, Bash, Conda или Make. Ускорение реализовано для CUDA; при отсутствии подходящего CUDA-устройства используется CPU. Это также относится к устройствам macOS/MPS и Windows/DirectML: отдельного ускоренного backend для них в этом проекте нет.

До этой доработки Linux-установка прошла Python/JS/TS-проверки и короткий рендер ProRes. Изменения для Windows пока не проверены запуском: ни новые тесты на Linux, ни полный цикл на Windows агент не запускал. Наличие переносимого кода не заменяет проверку на целевой Windows-машине.

## Результат просмотра проекта

| Область | Решение и ограничения |
|---|---|
| Пути | `pathlib` и аргументы subprocess без shell; абсолютные пути Windows с диском, пробелами и кириллицей передаются отдельными аргументами. Путь относится к машине сервера ComfyUI, а не браузера |
| FFmpeg | Поиск в PATH процесса; отдельные пути `ALEXZ_FFMPEG` и `ALEXZ_FFPROBE`. На Windows вспомогательные процессы запускаются без отдельных консольных окон |
| Загрузка видео и MP4-превью | На Windows готовый временный файл публикуется через `os.rename`, который отказывает при занятом имени. Hard links не нужны. На POSIX сохранена публикация через `os.link` без перезаписи |
| Имена загружаемых файлов | Проверяются Windows-имена устройств, запрещённые символы, завершающие точки/пробелы и выход из папки. Имена выходного файла обрабатывает установленный `folder_paths` ComfyUI; не используйте для них `CON`, `NUL`, `COM1` и подобные имена |
| Дисковый кэш | `mmap.ACCESS_WRITE`; временный файл остаётся открытым до освобождения mapping. Закрытие выполняется в порядке mapping → файл, включая tensor views. На Windows имя временного файла может быть видно во время обработки |
| Резервирование диска | При отсутствии `posix_fallocate` используются порционные записи с проверкой отмены. Это может быть медленнее, но не требует POSIX API |
| Освобождение страниц | `madvise` вызывается только при наличии. На Windows принудительное вытеснение страниц этим API недоступно; кэшем страниц управляет ОС. Запись и точность данных сохраняются |
| Тесты и workflow | JSON читается явно как UTF-8. Проверки не предполагают отсутствие `posix_fallocate` или невидимость временного файла на Windows |
| Зависимости | `requirements.txt` для Python среды ComfyUI; frontend bundles уже включены в Git. npm нужен только разработчику |
| Исполнитель ComfyUI | Выборочный кэш использует внутренний интерфейс локального ComfyUI, а не API ОС. Совместимость зависит также от версии ComfyUI; после его обновления повторите проверку жизненного цикла кэша |

Старые workflow могут содержать сохранённые пути Linux и сведения о прежних превью. Заново выберите исходник и выполните workflow на Windows. Сами файлы workflow при этой доработке не переписывались. Рекомендуется короткий путь установки, например `D:\ComfyUI`, чтобы не упираться в ограничения длинных путей Windows и конкретной сборки FFmpeg.

## Обычный ComfyUI с Python/venv на Windows

В PowerShell из `custom_nodes` вашей установки:

```powershell
git clone https://github.com/AlexZ1967/ComfyUI_ALEXZ_SilentFilm.git
cd .\ComfyUI_ALEXZ_SilentFilm
python -m pip install -r requirements.txt
```

Сначала активируйте venv ComfyUI либо вместо `python` укажите полный путь к его `python.exe`. Не устанавливайте зависимости в случайный системный Python. PyTorch/CUDA остаются теми, которые установлены для ComfyUI.

## ComfyUI Portable на Windows

Из корня Portable-установки, где находятся `python_embeded` и `ComfyUI`:

```powershell
git clone https://github.com/AlexZ1967/ComfyUI_ALEXZ_SilentFilm.git .\ComfyUI\custom_nodes\ComfyUI_ALEXZ_SilentFilm
.\python_embeded\python.exe -m pip install -r .\ComfyUI\custom_nodes\ComfyUI_ALEXZ_SilentFilm\requirements.txt
```

После установки используйте свой штатный запуск Portable. ALEXZ_tools устанавливается отдельно, если нужны его Node Picker и Save Workflow. Старый двухнодовый пример может дополнительно требовать VideoHelperSuite и WAS; у собственного загрузчика и сборщика SilentFilm этих зависимостей нет.

## FFmpeg и SSD-кэш

Используйте сборку FFmpeg с `ffprobe`, `prores_ks` и `libx264`. NVIDIA NVENC необязателен: H.264 имеет CPU-вариант, а ProRes кодируется на CPU. Готовые сборки для Windows доступны по ссылкам на [официальной странице FFmpeg](https://ffmpeg.org/download.html).

Если инструменты уже доступны в PATH, дополнительных настроек не требуется. Иначе задайте пути в том же PowerShell, из которого будете запускать ComfyUI:

```powershell
$env:ALEXZ_FFMPEG = 'D:\Tools\ffmpeg\bin\ffmpeg.exe'
$env:ALEXZ_FFPROBE = 'D:\Tools\ffmpeg\bin\ffprobe.exe'
$env:ALEXZ_VIDEO_CACHE_DIR = 'D:\SilentFilmCache'
```

Для `.bat` запуска добавьте перед существующей командой запуска:

```bat
set "ALEXZ_FFMPEG=D:\Tools\ffmpeg\bin\ffmpeg.exe"
set "ALEXZ_FFPROBE=D:\Tools\ffmpeg\bin\ffprobe.exe"
set "ALEXZ_VIDEO_CACHE_DIR=D:\SilentFilmCache"
```

Эти значения — примеры; замените их своими путями. Переменные PowerShell действуют только в текущем процессе и его дочерних процессах. Запуск ярлыком из другого окна их не унаследует. Не создавайте вторую копию кэша во время рендера; он удаляется после освобождения последнего владельца, в том числе при завершении процесса.

Выборочное хранение Load Source Video/Camera и порядок VRAM → RAM → диск сохраняются. Новый путь не заставляет выгружать данные на диск, если памяти достаточно. На Windows по умолчанию используется системная временная папка; для большого видео лучше задать SSD-каталог явно. Во время работы Windows не удаляйте открытые `frames-*` вручную.

## Проверки разработчика без Make

Команды выполняются из каталога проекта в активном окружении ComfyUI. Для Portable используйте полный путь к `python_embeded\python.exe` вместо `python`. Это команды для ручного запуска пользователем:

```powershell
python -m pip install pytest pytest-subtests aiohttp
python -m pytest -q tests
python tests/check_video_cache_lifecycle.py
npm ci
node scripts/check_js_syntax.mjs web
node tests/test_silent_film_preview.mjs
node tests/test_silent_film_emulsion.mjs
node tests/test_silent_film_cadence_visibility.mjs
node tests/test_video_io.mjs
node tests/test_video_frame_select.mjs
npm run ts-check
npm run frontend-build
```

JS-тест emulsion запускает `python` из PATH: для него активируйте правильное окружение и убедитесь, что это Python ComfyUI. Для Portable можно добавить `python_embeded` в PATH текущего PowerShell. Conda environment с именем `p313-torch214-cu132` нужен только для принятых локальных проверок на Linux-машине разработчика; на другой машине используйте её окружение ComfyUI. Без Node.js/npm можно работать с уже включёнными runtime bundles, но нельзя запускать JS/TS-проверки и пересобирать их.

## Ручная проверка на Windows

1. Запустите ComfyUI, откройте `http://127.0.0.1:8188` (либо свой порт). Проверьте наличие нод SilentFilm и отсутствие ошибок импорта.
2. Загрузите MOV/ProRes с пробелами и кириллицей в имени через кнопку выбора; повторите загрузку того же файла. Существующий файл должен сохраниться, новый получить номер. Затем укажите абсолютный путь Windows к существующему файлу без копирования.
3. Выберите 4–8 кадров и проведите их через Camera → Negative → Print → Projector. Проверьте средние превью и bypass этапов.
4. Запишите ProRes с MP4-превью и H.264 отдельно. Повторный запуск не должен перезаписать первый результат.
5. Воспроизведите дисковую ветку синтетической проверкой `check_video_cache_lifecycle.py`. Она проверяет mmap, освобождение ссылок и выборочное кэширование без большого реального видео. Не доводите систему до OOM ради этой проверки.
6. Прервите реальный расчёт через Queue/Interrupt. После завершения отмены и освобождения ссылок кэш не должен оставаться занят. Повторите короткий запуск.
7. Для browser smoke используйте [GUIDE_BROWSER_SMOKE.md](GUIDE_BROWSER_SMOKE.md); порт в сценарии по умолчанию 8188.

Различия порядка округлений CPU/CUDA, алгоритмов управления памятью ОС и сборок FFmpeg допустимы: побитовая одинаковость видео между платформами не обещается.

## Источники платформенных правил

- [Python 3.13: tempfile](https://docs.python.org/3.13/library/tempfile.html) — видимость и удаление временных файлов на разных ОС.
- [Python 3.13: mmap](https://docs.python.org/3.13/library/mmap.html) — доступ, выравнивание и платформенные методы mapping.
- [Python 3.13: os.rename](https://docs.python.org/3.13/library/os.html#os.rename) — отказ при существующем destination на Windows; на Unix возможна замена.
