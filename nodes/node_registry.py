"""Registry manifest for the standalone Silent Film node package."""

from dataclasses import dataclass

# Эти class_type регистрирует только самостоятельный пакет Silent Film.
ENABLE_NODE_LOADING = True

@dataclass(frozen=True)
class NodeSpec:
    """Describe one ComfyUI node class provided by this package."""

    type_name: str
    display_name: str
    module_import: str
    class_name: str


NODE_SPECS = (
    NodeSpec("VideoSilentFilmCadence", "Silent Film Cadence", ".video_silent_film_cadence", "VideoSilentFilmCadence"),
    NodeSpec("VideoSilentFilmFinish", "Silent Film Finish", ".video_silent_film_finish", "VideoSilentFilmFinish"),
    NodeSpec("VideoFrameSelect", "Select Video Frames", ".video_frame_select", "VideoFrameSelect"),
    NodeSpec("VideoPreviewFrame", "Preview Middle Frame (ALEXZ)", ".video_preview", "VideoPreviewFrame"),
    NodeSpec("VideoLoadSource", "Load Source Video (ALEXZ)", ".video_io", "VideoLoadSource"),
    NodeSpec("VideoSaveFinal", "Save Final Video (ALEXZ)", ".video_io", "VideoSaveFinal"),
    NodeSpec("VideoSilentFilmCamera", "Silent Film Camera", ".video_silent_film_pipeline", "VideoSilentFilmCamera"),
    NodeSpec("VideoSilentFilmNegative", "Silent Film Negative", ".video_silent_film_pipeline", "VideoSilentFilmNegative"),
    NodeSpec("VideoSilentFilmPrint", "Silent Film Print", ".video_silent_film_pipeline", "VideoSilentFilmPrint"),
    NodeSpec("VideoSilentFilmProjector", "Silent Film Projector", ".video_silent_film_pipeline", "VideoSilentFilmProjector"),
    NodeSpec("VideoSilentFilmCaptureDirt", "Silent Film Capture Dirt", ".video_silent_film_defects", "VideoSilentFilmCaptureDirt"),
    NodeSpec("VideoSilentFilmNegativeDevelopment", "Silent Film Negative Development", ".video_silent_film_defects", "VideoSilentFilmNegativeDevelopment"),
    NodeSpec("VideoSilentFilmNegativeDamage", "Silent Film Negative Damage", ".video_silent_film_defects", "VideoSilentFilmNegativeDamage"),
    NodeSpec("VideoSilentFilmPrintingDirt", "Silent Film Printing Dirt", ".video_silent_film_defects", "VideoSilentFilmPrintingDirt"),
    NodeSpec("VideoSilentFilmPositiveDevelopment", "Silent Film Positive Development", ".video_silent_film_defects", "VideoSilentFilmPositiveDevelopment"),
    NodeSpec("VideoSilentFilmPositiveDamage", "Silent Film Positive Damage", ".video_silent_film_defects", "VideoSilentFilmPositiveDamage"),
    NodeSpec("VideoSilentFilmProjectorDirt", "Silent Film Projector Dirt", ".video_silent_film_defects", "VideoSilentFilmProjectorDirt"),
)

NODE_UI_METADATA = {
    "VideoSilentFilmCadence": {
        "description": "Имитирует 16-20 fps немой пленочный каденс, сохраняя выходной батч на 25 fps.",
        "output_tooltips": ["Стилизованный батч кадров.", "JSON с реальным effective fps, размерами hold-групп и параметрами blur."],
        "search_aliases": ["video", "silent film", "cadence", "fps", "motion blur", "1920s"],
    },
    "VideoSilentFilmFinish": {
        "description": "Добавляет финальный silent-film finish: ЧБ/тонировка, flicker, gate weave, мягкость и зерно.",
        "output_tooltips": ["Стилизованный батч кадров.", "JSON с параметрами finish, preview drift/flicker и seed."],
        "search_aliases": ["video", "silent film", "finish", "flicker", "gate weave", "grain", "1920s"],
    },
    "VideoFrameSelect": {
        "description": "Выбирает весь ролик, отдельный кадр или диапазон включительно; показывает исходное и выбранное число кадров.",
        "output_tooltips": ["Выбранные кадры для Camera или другой обработки.", "Общее число кадров входного батча.", "Число выбранных кадров.", "Границы выбора и номер среднего исходного кадра."],
        "search_aliases": ["video", "frame", "select", "trim", "range", "кадр", "отрезок"],
    },
    "VideoPreviewFrame": {
        "description": "Показывает один средний кадр видео; передаёт весь входной батч дальше. Безопасное превью при bypass этапов Silent Film.",
        "output_tooltips": ["Весь исходный IMAGE-батч без обрезки; в интерфейсе показан только средний кадр."],
        "search_aliases": ["preview", "video", "middle", "кадр", "превью"],
    },
    "VideoLoadSource": {
        "description": "Потоковый загрузчик FFmpeg, включая MOV/ProRes: выбор всего видео, одного кадра или диапазона; информация о файле до запуска пайплайна.",
        "output_tooltips": ["Выбранные кадры RGB/RGBA float32 без предварительного перевода в 8 бит.", "Средняя частота исходного файла. Компенсация рапида задаётся отдельно в Camera.", "Полное число кадров исходника.", "Число выбранных кадров.", "Кодек, размеры, fps и исходные границы выбора.", "Средний кадр выбранного отрезка."],
        "search_aliases": ["video", "load", "prores", "mov", "ffmpeg", "загрузить", "видео"],
    },
    "VideoSaveFinal": {
        "description": "Записывает кадры порциями в ProRes MOV или H.264 MP4; создаёт браузерное MP4-превью ProRes.",
        "output_tooltips": ["Полный путь к сохранённому мастер-файлу.", "Формат, размеры, число кадров, fps, длительность и путь превью."],
        "search_aliases": ["video", "save", "prores", "mov", "ffmpeg", "сохранить", "видео"],
    },
    "VideoSilentFilmCamera": {
        "description": "Чёрно-белый съёмочный аппарат: ручной каденс, синхронная выдержке экспозиция, движение камеры и съёмочная оптика.",
        "output_tooltips": ["Нейтральное ЧБ после съёмки: три одинаковых RGB-канала, исходная альфа сохранена.", "Метаданные этапа camera и виртуальных кадров.", "Один средний обработанный ЧБ-кадр для Preview Image; для ускорения выберите кадр или короткий отрезок в загрузчике."],
        "search_aliases": ["silent film", "pipeline", "camera"],
    },
    "VideoSilentFilmNegative": {
        "description": "Экспонирование, halation и проявка ЧБ-негатива: нейтральная плёнка, контраст, сжатие теней и светов, вуаль и зерно.",
        "output_tooltips": ["Фактическое пропускание проявленного негатива в линейных единицах; подключайте к Print.image.", "Паспорт negative: модель материала, кодирование входа и история обработки.", "Один средний кадр негатива как пропускание плёнки.", "Тот же негатив через эталонную нейтральную печать: показывает экспозицию, проявку и зерно Negative без художественных настроек Print. Альфа сохранена; автоконтраста нет. Подключайте к Preview Image; для ускорения выберите один кадр в загрузчике."],
        "search_aliases": ["silent film", "pipeline", "negative"],
    },
    "VideoSilentFilmPrint": {
        "description": "Экспонирование позитивной плёнки через негатив, её halation и проявка; нейтральная пара сохраняет шкалу исходника.",
        "output_tooltips": ["Позитив после фиксированной калибровки просмотра, в кодировании output_transfer; готов для Projector и обычных IMAGE-нод.", "Паспорт print с параметрами проявки, моделью и кодированием выхода.", "Один средний кадр позитивной копии; для ускорения выберите один кадр в загрузчике."],
        "search_aliases": ["silent film", "pipeline", "print"],
    },
    "VideoSilentFilmProjector": {
        "description": "Показ позитивной копии: кадровое окно, отдельные расфокус и glow проекционной оптики, лампа и частота показа.",
        "output_tooltips": ["Проекция позитивной копии.", "Подключите к frame_rate в Video Combine.", "Метаданные этапа projector.", "Один средний обработанный кадр для Preview Image; для ускорения выберите кадр или короткий отрезок через Select Video Frames перед Camera."],
        "search_aliases": ["silent film", "pipeline", "projector"],
    },
    "VideoSilentFilmCaptureDirt": {
        "description": "Самостоятельное загрязнение кадрового окна съёмки: после Camera, перед Negative. Пыль затеняет линейную экспозицию; исходные ноды не меняются.",
        "output_tooltips": ["Полный батч после загрязнения съёмки.", "Паспорт без смены основного этапа; без входного паспорта пустая строка.", "Один средний обработанный кадр.", "Маска силы дефектов среднего кадра; чёрная при strength=0."],
        "search_aliases": ["silent film", "dust", "hair", "пыль", "съёмка"],
    },
    "VideoSilentFilmNegativeDevelopment": {
        "description": "Неравномерность проявки после Negative: связанные пятна, полосы и локальная добавочная плотность. Самостоятельная нода.",
        "output_tooltips": ["Пропускание негатива с дефектами проявки.", "Исходный этап и история дефектов.", "Средний кадр негатива.", "Модуль изменения плотности среднего кадра.", "Эталонная нейтральная печать среднего повреждённого негатива."],
        "search_aliases": ["silent film", "development", "проявка", "пятна"],
    },
    "VideoSilentFilmNegativeDamage": {
        "description": "Пыль, царапины и пятна на проявленном негативе перед Print. Утрата эмульсии и непрозрачная грязь имеют разную полярность после печати.",
        "output_tooltips": ["Повреждённый негатив для Print.", "Исходный этап и история дефектов.", "Средний кадр негатива.", "Маска повреждений среднего кадра.", "Эталонная нейтральная печать повреждённого негатива."],
        "search_aliases": ["silent film", "scratches", "negative", "царапины"],
    },
    "VideoSilentFilmPrintingDirt": {
        "description": "Пыль и волоски при печати: перед Print, отдельно от постоянных повреждений негатива. Ослабление печатной экспозиции даёт светлые следы на позитиве.",
        "output_tooltips": ["Негатив с затенением печатного света.", "Исходный этап и история дефектов.", "Средний кадр перед печатью.", "Маска загрязнения среднего кадра.", "Контроль эффекта через эталонную печать."],
        "search_aliases": ["silent film", "printing", "dust", "печать"],
    },
    "VideoSilentFilmPositiveDevelopment": {
        "description": "Приближение пятнистой проявки позитива после Print в линейном свете. Не восстанавливает плотность эмульсии, уже потерянную при экранном преобразовании.",
        "output_tooltips": ["Позитив с неравномерностью проявки.", "Исходный этап и история дефектов.", "Один средний обработанный кадр.", "Модуль изменения условной плотности среднего кадра."],
        "search_aliases": ["silent film", "development", "positive", "проявка"],
    },
    "VideoSilentFilmPositiveDamage": {
        "description": "Износ копии между Print и Projector: царапины, пыль, пятна. Приближение по готовому позитиву; затем проходит движение и оптику Projector.",
        "output_tooltips": ["Повреждённая позитивная копия.", "Исходный этап и история дефектов.", "Один средний обработанный кадр.", "Маска повреждений среднего кадра."],
        "search_aliases": ["silent film", "scratches", "positive", "износ"],
    },
    "VideoSilentFilmProjectorDirt": {
        "description": "Приближение пыли окна после Projector: неподвижная тень с отдельной мягкостью. Умножает уже освещённое изображение без повторного мерцания или glow.",
        "output_tooltips": ["Проекция с загрязнением окна для Save Final Video.", "Исходный этап projector и история дефектов.", "Один средний кадр.", "Маска тени среднего кадра."],
        "search_aliases": ["silent film", "projector", "dust", "проектор"],
    },
}
