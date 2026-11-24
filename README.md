# MorphSnos — 2D-анимация мессенджера (2:3)

Анимация сценария: приходит сообщение «жди докс» → переход в список чатов → чат с ботом
**MorphSnos** → отправка `@doxer123` → «выполняю...» (пауза 3 с) → «готово» → профиль доксера
становится «Удалённый аккаунт».

## Результат (`out/`)
| файл | разрешение | размер |
|---|---|---|
| `morphsnos_1200x1800_60fps.mp4` | 1200×1800 (2:3), 60 fps, 20.6 с | 2.4 МБ |
| `morphsnos_800x1200_60fps.mp4` | 800×1200 | 1.1 МБ |
| `morphsnos_400x600.gif` | 400×600, 15 fps | 2.8 МБ |

## Как устроено
* `src/scene.html` — сцена на HTML/CSS/JS. Вся анимация — чистая функция `window.__render(t)`,
  где `t` — время в секундах: никаких CSS-переходов, поэтому кадры воспроизводимы покадрово.
  Тайминг сцен задаётся объектом `T` в начале скрипта.
* `src/render.js` — покадровый захват через Playwright (Chromium).

## Перерендер
```bash
npm i playwright            # если нет
node src/render.js --fps 60 --scale 3 --frames /tmp/frames
ffmpeg -framerate 60 -i /tmp/frames/%05d.png -c:v libx264 -crf 17 -pix_fmt yuv420p \
       -movflags +faststart out/morphsnos_1200x1800_60fps.mp4
```
Отдельные кадры для проверки: `node src/render.js --preview "2.6,9.0,13.6" --frames /tmp/prev --scale 2`
