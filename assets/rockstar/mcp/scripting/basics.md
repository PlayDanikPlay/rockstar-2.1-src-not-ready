# Скрипты для чит-клиента Rockstar (Minecraft)

## Что это за система

- **Язык — Python 3** (исполняется через Jep внутри клиента). **Lua в клиенте НЕТ** (папка `docs/lua-scripts` — легаси-название, не обращай на него внимания). Java-API скриптов лежит в пакете `pyrock`.
- Скрипт — один файл `<gameDir>/scripts/*.py`. Имя скрипта = имя файла без `.py`.
- Тело файла выполняется **один раз при загрузке** — это «конструктор»: тут создают модули, настройки, HUD и подписываются на события.
- **Глобалы инжектятся автоматически. Их НЕЛЬЗЯ и НЕ НУЖНО импортировать** — никакого `from rockstar import ...`. `Module`, `events`, `client`, `mc`, `hud`, `world` и прочее просто есть в неймспейсе.
- Выгрузка скрипта откатывает всё, что он создал через API (модули, настройки, HUD, обработчики). Файл watch'ится: сохранил — скрипт перезагрузился сам.
- `print(...)` пишет в лог клиента (latest.log), **не в чат**. Для чата — `client.msg(...)`.
- Стандартная библиотека Python доступна целиком. Внешние пакеты — `.py install <пакет>` (pip во встроенный runtime).

Команды в чате: `.py list | load <имя> | unload <имя> | toggle <имя> | reload | save <имя> | delete <имя> | install <пакет> | dir | sync` (алиасы команды: `.script`, `.python`).

## Канонический скелет скрипта

```python
# Модуль + настройки + события — 90% скриптов выглядят так.

mod = Module("MyModule", "Combat")        # категории: Combat|Movement|Visuals|Player|Other
mod.setDesc("Что делает модуль")

enabled = Checkbox(mod, "Show text")
speed   = Slider(mod, "Speed").min(1).max(10).step(0.5).set(5)   # ПОРЯДОК: min→max→step→set
target  = Mode(mod, "Target").add("Head").add("Body")            # первый add уже выбран

@events.tick
def on_tick(event):
    if not mod.isEnabled():               # ВАЖНО: on_enable/on_disable у модуля НЕТ
        return
    if target.get() == "Head":            # Mode сравниваем СТРОКОЙ (метод is() из Python не вызвать)
        client.overlay("speed=%.1f" % speed.get())

@events.attack
def on_attack(event):
    ent = event.getEntity()               # объект Minecraft из события готов к работе
    client.msg("Бью " + str(ent.getNameForScoreboard()))

@events.render_2d
def on_render(event):
    if not mod.isEnabled() or not enabled.get():
        return
    ctx = event.getContext()
    white = Color(255, 255, 255)
    ctx.drawRoundedRect(90, 90, 160, 24, border(6), Color(0, 0, 0, 180))
    ctx.drawText(font("medium", 8), "Rockstar", 98, 98, white)

print("MyModule загружен")                # в лог клиента
```

## Шпаргалка по неймспейсу

| Имя | Что это |
|---|---|
| `Module(name, category)` | создать модуль чита |
| `Checkbox / Slider / Mode / Select / Button / Range / ColorSetting` | настройки: `Checkbox(mod, "Name")` |
| `Bind / TextSetting / TimeSetting / Gradient / PositionSetting / Bezier / Blocks / Info` | остальные настройки: клавиша, поле ввода, время (в секундах), градиент, точка, кривая плавности, сетка блоков, подпись |
| `Color(r,g,b[,a])`, `Color.from_hex("#fff")`, `ColorRGBA.WHITE` | цвета |
| `border(r)`, `border4(tl,tr,br,bl)` | скругления |
| `font("medium", 8)` | шрифт (веса: `noto`, `bold`, `medium`, `regular`, `semibold`, `roundbold`) |
| `events.<name>` | подписка на событие (декоратор) |
| `client` | `msg/warn/error/overlay`, `find(...)`, `modules`, `gameDir()` (= папка клиента `.minecraft/Rockstar`), `menu_opened()`, `cursor(...)`, `font_width/height` |
| `client.modules` | `all() find(n) require(n) enabled(n) enable/disable/toggle(n)` — `find` вернёт `None`, если модуля нет; `require` (и `enable/disable/toggle`) бросит `ValueError` |
| `Hud` / `hud` | HUD-элемент: `Hud("Имя", width=..., height=...)`; строчный `hud` — менеджер (`all/find/remove`) и списки в стиле клиента (`hud.list(...)` + `rows`) |
| `IslandStatus(...)` | создать статус Dynamic Island (как `Module(...)`) |
| `island` | менеджер статусов Dynamic Island: `find(n) all() mine() remove(n)` |
| `screen(title, w, h)` / `raw_screen(...)` | декораторы экранов/меню |
| `ui` | внутри layout/screen — билдер виджетов |
| `render3d` | 3D-рендер: `box`, `filled_box`, `line`, `ring`, `target`, `text`, ... |
| `music` | что играет на компьютере: `current()`, `current_lyric()`, `progress()`, `toggle()`, ... |
| `sound` / `audio` | свои звуки wav/mp3/ogg: `play(path, volume=..)`, `once(...)` для наложения, `loop(...)`, у звука `stop/pause/volume/position` |
| `container` / `chest` | открытое чужое меню: `open`, `title`, `items()`, `find(q)`, `click(slot)`, `shift_click(slot)`, `close()` |
| `Shader` / `shader` | свои шейдеры GLSL: `Shader(name, glsl)`, дальше `rect(ctx, ...)` / `fullscreen(e)` / `quad3d(e, ...)` |
| `world` | `ingame() self() entities() living() players() nearest_player() target() time()` |
| `newton` | ходит за тебя: `goto(...)`, `fly_to(...)`, `mine(block)`, `excavate/fill`, `cancel()`, `path()`, `status()` |
| `Command` / `command` / `commands` | своя команда чата: `@Command("hello")`, подкоманды `@cmd.sub("add")`, `commands.run/exists/all` |
| `notify` | уведомления клиента: `island(text, type)`, `crosshair(title, desc)`, `item(...)`, `sound()` |
| `inventory` / `inv` | инвентарь: `find/total/empty/items`, `select/swap/move/quick_move/to_offhand/to_armor`, `with_slot`, `durability/enchant` |
| `effects` / `buffs` | баффы и дебаффы: `list()`, `has/get/level/duration/time`, `info(id)`, `of(entity)`; иконка — `ctx.effect(...)`, `ui.effect(...)`, `render3d.effect(...)` |
| `theme` / `colors` | цвета темы вне лейаута: `accent()`, `text()`, `background()`, `color(name)`, `readable(bg)` |
| `profile` / `account` / `user` | аккаунт игрока: `username`, `uid`, `role`, `staff`, `subscription`, `days_left`, `avatar`, `avatar_of(n)` (свойства, без скобок) |
| `menu` | меню клиента: `opened`, `type`, `progress`, `alpha`, `scale`, `panels`, `panel(n)` (свойства, без скобок); слои вокруг него — события `menu_render` / `post_menu_render` |
| `keys` | коды и состояние клавиш: `keys.G`, `code(name)`, `name(code)`, `down(key)`, `mouse(btn)`, `x() y() cursor()` |
| `skins` / `skin` | скин, плащ и элитра глазами клиента: `me(...)`, `set(target, ...)`, `skin/cape/elytra/model`, `all(...)`, `reset/clear` |
| `lang` / `tr` | переводы скрипта: `lang.load({"ru_ru": {...}})`, `lang("key", *args)`, `load_file(path)`, `current()`, `has()`, `plural(n, ...)` |
| `Esp` / `esp` | свои элементы ESP: `Esp(name, targets, enable)`, декораторы `@el.render` / `@el.render_all` / `@el.filter`, `el.enable_for()`, `esp.to_screen(x, y, z)` |
| `target` | цель правилами клиента: `best(**настройки)`, `all(...)`, `current()`, приоритетные ники |
| `funtime` / `ft` | данные FunTime: `events/mines/copper_dungeons/warden_cities/system_info`, `fetch_*(колбэк)` |
| `mc` | обёртка над MinecraftClient: `mc.player`, `mc.world`, `mc.options`, `mc.getCurrentFps()` |
| `aura` / `rotations` | свои режимы ротации Aura / ротации вне Aura |
| `Storage` / `storage` | JSON-хранилище: `Storage("myscript")` |
| `Timer`, `vec` | таймер, 3D-математика |
| `assets` / `image(path)` / `paths` | картинки, шрифты, пути |
| `jimport("net.minecraft...")` | импорт Java-класса |

## ТОП-правила и грабли (читай ВСЕГДА)

Правила 1–4 — про **ремап**: тут легко написать код, который работает в dev-сборке и ломается у пользователя в релизе. Правила 5–10 — тихие баги, где скрипт «работает», но виджет/статус/бокс просто ничего не делает. Проверяй их в каждом скрипте.

1. **Объекты Minecraft из API готовы к работе, `wrap(...)` звать не нужно**: `e.getEntity().getX()` работает и в dev, и в релизе, как и всё из `mc.*`, `world.*`, `inventory.stack()`. Старый `wrap(...)` в чужом коде не ошибка (обёртка идемпотентна), просто лишний вызов.
2. **Тип пакета/сущности — `is_instance(obj, "named.Fqn")`** (глобал, импортировать нечего). `isinstance` и `getClass().getName()` в релизе молча не сработают (обфускация).
3. **`PlayerMoveC2SPacket`: читай ПОЛЯ, а не геттеры.** `p = e.getPacket()` → `p.x, p.y, p.z, p.yaw, p.pitch, p.onGround`. `p.getX()` упадёт (у метода argc=1, а перегрузки резолвятся по числу аргументов).
4. **Имя сущности бери через `ent.getNameForScoreboard()`**, а не `getName().getString()`: одна строка вместо возни с `Text`.
5. **`ui.switch(get, set)` и `ui.toggle(label, get, set)`: сеттер получает НОВОЕ ЗНАЧЕНИЕ** → `lambda v: s.boolSet(v)`. Лямбда без параметра молча ломается. КОНТРАСТ: у `ui.toggle_c(get, on_click, ...)` второй колбэк — клик **без аргументов** (`lambda: s.boolToggle()`); у `slider_bar`/`slider_c` сеттер принимает значение (`lambda v: ...`).
6. **`on_click` НЕ работает на `ui.text` / `ui.image` / `ui.swatch`** (они создаются с `interactive(false)`). Клик вешают на обёртку: `with ui.row(cursor="hand", on_click=fn): ui.text(...)`. `ui.icon` и `ui.button` мышь ловят.
7. **`IslandStatus(...)` без `.selected(True)` не рисуется** — свежий статус не выбран, и Dynamic Island его отфильтровывает.
8. **`Slider`: строгий порядок `.min().max().step().set()`** — `set()` клампится по ТЕКУЩЕМУ шагу (дефолт 1), поэтому `.set(3.5).step(0.1)` даст `4.0`. У `Mode` первый `add(...)` уже выбран, `select()` нужен только чтобы выбрать другой.
9. **`client.find(...)` / `modules.find(...)` возвращают `None`, если модуля нет** — `try/except` вокруг них НЕ нужен, хватит `if aura is None: return`. КОНТРАСТ: `modules.require(name)` бросает `ValueError` при отсутствии модуля, и через него работают `enable` / `disable` / `toggle` — значит, они тоже бросят `ValueError`. `modules.enabled(name)` на неизвестном имени просто вернёт `False`.
10. **`render3d.marker` / `render3d.line` принимают ТОЛЬКО точки `[x, y, z]`** (сущность в `marker` падает в релизе). Сущность/Box принимают `box`, `filled_box`, `glowing_box`, `ring`, `target`. Для бокса по координатам — `box_at` / `filled_box_at` (список координат в `box` молча ничего не нарисует). **Каждый одиночный вызов — отдельный draw call**, поэтому сотни фигур (частицы, сетки, следы) рисуй пачкой: `render3d.billboards(event, texture, data, True)` — плоский список по 8 чисел на частицу (`x, y, z, size, r, g, b, a`), `render3d.lines(event, segments, True)` — по 10 на отрезок (`x1, y1, z1, x2, y2, z2, r, g, b, a`). Цвет там числами 0..255, `Color` не нужен. **Текст в мире — `render3d.text(event, text, pos, size, color)`**, где `size` это высота заглавной буквы **в блоках** (0.25 это четверть блока), а не кегль экрана; мерить строку надо `render3d.text_width` (тоже в блоках), а не `font(...).width(...)`. Много надписей — `render3d.texts(event, items)` одним draw call. **Сквозь стены видно всё нарисованное**; чтобы фигуры прятались за блоками, вызови `render3d.depth(True)` — режим держится до следующего вызова, а флаг `through=False` делает то же самое у одного вызова.
11. **Горячая клавиша: сначала настройка `Bind`, а не разбор кодов руками.** `hotkey = Bind(mod, "Hotkey").set("G")`, дальше в событии `key`: `if event.isPress() and hotkey.isKey(event.getKey()):`. Клавишу так выбирает игрок в меню, а клиент её запоминает. Альтернативы: бинд самого модуля `mod.setKey(glfw_code)` + событие `module_toggled` (модуль-кнопка) либо `Button(mod, "Run").action(fn)`. События ввода есть: `key`, `char_typed`, `mouse`, `scroll`, `mouse_move` — коды клавиш в глобале `keys`.
12. **`on_enable` / `on_disable` у модуля НЕТ.** Проверяй `mod.isEnabled()` в обработчике события или подписывайся на `module_toggled` и сравнивай `e.getModule().getName()`.
13. **С чужого потока НЕЛЬЗЯ трогать `mc`, модули, HUD.** Тяжёлое (сеть, CV, боты) — в отдельный поток, результат — в `queue.Queue`, разбор — в `@events.tick` (главный поток). Шаблон гашения потока при reload — в `script_api section=recipes`.
14. **Ошибка в обработчике выгружает скрипт**, пишет `[Python Error]` в чат (без трейсбека — он в `latest.log`) **и убивает слежение за файлом**: после падения сохранение файла уже НЕ перезагрузит скрипт, нужен `.py load <имя>`. Оборачивай рискованное в `try/except`, проверяй `world.ingame()` / `mc.player is None`.
15. **Новый скрипт создаёт `.py create <имя>`** (алиас `add`), и на занятом имени он откажется. `.py save` не пишет ничего — только напоминает, что скрипт правят прямо в файле `<gameDir>/scripts/`. Потерять код этими командами нельзя.
16. **Перегрузка ищется сперва по числу аргументов, потом по типам.** Передавай ровно столько аргументов, сколько у нужной перегрузки; из нескольких с одинаковым числом мост возьмёт ту, чьи типы подходят (а при `None` в аргументе — первую попавшуюся).
17. **У `Mode` Java-метод `is(name)` из Python НЕВЫЗЫВАЕМ** — `is` это ключевое слово Python (SyntaxError). Сравнивай строкой: `if style.get() == "Head":`. У `Bind` по той же причине сравнение называется `isKey(key)`.
18. **Не затеняй глобальные имена** своими переменными: `module`, `color`, `border`, `select`, `mode`, `slider`, `button`, `checkbox`, `bind`, `info`, `gradient`, `bezier`, `blocks`, `settings`, `image`, `texture`, `font`, `fonts`, `world`, `screen`, `storage`, `vec`, `ui`, `hud`, `client`, `events`, `mc`, `assets`, `paths`, `modules`, `messages`, `island`, `music`, `sound`, `audio`, `container`, `chest`, `aura`, `newton`, `command`, `commands`, `notify`, `inventory`, `inv`, `effects`, `buffs`, `theme`, `colors`, `profile`, `account`, `user`, `menu`, `keys`, `skins`, `skin`, `lang`, `tr`, `esp`, `Esp`, `Hud`, `Storage`, `Shader`, `Command`, `target`, `funtime`, `ft`, `rotations`, `wrap`. Builtins (`range`, `len`, `print`) не затенены — в неймспейсе только `Range` с большой буквы.
19. **В замыканиях внутри циклов связывай переменные через дефолтные аргументы**: `lambda ps=ps: ps.boolGet()` — иначе все лямбды схватят последнее значение (критично для `ui`-билдера, где всё реактивно).
20. **`ui`-стили принимают callable** там, где значение реактивно: `bg=lambda: ACCENT if state["cat"] == c else NONE`, `ui.text(lambda: str(fps()))`.
21. **Своя команда чата — `@command("имя")`, аргументы берутся из СИГНАТУРЫ функции.** Первый параметр всегда `ctx` (или функция вовсе без параметров), описание для `.help` — из docstring. Типы: `int`, `float`, `bool`, `str`, `"player"`, `"module"`, `"block"`; значение по умолчанию = необязательный аргумент, `*words` = остаток строки. Занять имя встроенной команды НЕЛЬЗЯ: скрипт не загрузится (проверка — `commands.exists(name)`). Команда снимается вместе со скриптом, а ошибка внутри команды скрипт НЕ выгружает (в отличие от события).
22. **Уведомление, отправленное скриптом, само же приходит событием `notification`.** `notify.*` внутри обработчика `notification` без проверки `getStyle()`/`getText()` зацикливает клиент.
23. **Слоты инвентаря нумеруются как в игре:** 0-8 хотбар, 9-35 рюкзак, 36-39 броня (шлем→ботинки), 40 левая рука; часть инвентаря задаётся словом `"hotbar"`/`"main"`/`"armor"`/`"offhand"`/`"all"`. Перекладывание — это клики по слотам, сервер их видит: не делай пачку за один тик, лучше одно действие за тик.
24. **Цвета темы (`theme`) живые:** бери их в момент отрисовки, а не запоминай в переменную при загрузке — иначе смена акцента игроком тебя не догонит.
25. **Профиль игрока (`profile`) приезжает с сайта уже ПОСЛЕ запуска клиента.** В теле скрипта `profile.username` обычно пустой, а `profile.role` — `default`: проверяй `profile.loaded` и читай значения там, где они нужны. Это свойства, а не методы (`profile.username`, без скобок), и это НЕ ник в Minecraft (тот — `mc.getSession().getUsername()`). У бессрочной подписки `profile.days_left` равен `inf`, при неизвестном сроке — `None`: сравнивать `None` с числом нельзя.
26. **Словари, которые отдаёт клиент, читаются и точкой:** `el.alpha` == `el["alpha"]`. Это обычные `dict` (get(), перебор, `in`, json), просто с точкой в придачу — так работают `hud.elements`, `menu.panels`, `music.current()`, `funtime.*`, `profile.all()`. Исключение одно: имена методов самого словаря точкой не перекрываются, значение такого ключа берут скобками (`bag["keys"]`).
27. **Вокруг элементов HUD рисуют события `hud_render` (слой ПОД ними) и `post_hud_render` (ПОВЕРХ),** а координаты и анимации всех элементов клиента лежат в `hud.elements` (словари: `x`, `y`, `width`, `height`, `center_x/y`, `alpha`, `scale`, `drag`, `showing`, `script`, …). Элемент всплывает не только альфой, но и масштабом: слой, который должен сидеть на нём вплотную, считай от центра с `el.scale`. Спрятанные элементы остаются в списке с `alpha == 0`.
28. **Рисовать вокруг меню клиента можно двумя событиями:** `menu_render` кладёт слой ПОД панели, `post_menu_render` — ПОВЕРХ них. Оба идут внутри анимации открытия и в тех же координатах, что и панели (`menu.panels`), поэтому повторять анимацию руками не нужно: нарисованное подпрыгивает и улетает в мир вместе с меню. Координаты панелей едут каждый кадр — бери их в обработчике; прозрачность умножай на `menu.alpha`, иначе слой останется висеть, когда меню спрятали клавишей.
29. **`target.best(...)` обходит все сущности мира.** Считай цель в `tick` и запоминай, а в `render_2d`/`render_3d` рисуй уже готовое.
30. **`funtime.events()` схлопывает записи по названию ивента** (одна строка на имя, а не на сервер). Нужны все записи — `funtime.fetch_events(колбэк)` и `json.loads`. Данные наполняются, пока играешь на FunTime: пустой список сразу после запуска это норма, а не ошибка.
31. **`collision_shape` — самое горячее событие клиента.** Зовётся на каждый блок рядом с каждой движущейся сущностью, тысячи раз за тик. Обработчик там — 2-3 строки с ранним выходом; `print`/`client.msg`/тяжёлые вычисления вешают игру. Так же дороги `hand_render`, `camera_update`, `game_render` и `trace`: они идут каждый кадр.
32. **Newton (`newton`) держит РОВНО ОДНУ задачу.** Новая отменяет старую, и отменённая отдаёт `newton_failed` с причиной `отменён` — поэтому перезапуск задачи прямо в обработчике `newton_failed` без проверки причины даёт вечный круг. Пока задача идёт, Newton сам жмёт клавиши движения: свои `mc.options.*Key.setPressed(...)` будут с ним драться. Цель почти всегда задавай с запасом (`newton.goto(pos, radius=1)`), иначе путь на конкретный блок часто не находится.
33. **События клавиатуры и мыши отменяемые, кроме `mouse_move`.** `event.cancel()` не пускает нажатие в игру, и этим легко сломать игроку управление: отменяя нажатие клавиши, отменяй и её отпускание (иначе игра считает клавишу зажатой), а прокрутку и клики гаси только по условию. Esc, `.` и клавиши открытия чата клиент не отдаёт намеренно. Клавишу сравнивай по коду из `keys` (`event.getKey() == keys.G`), а не по `getName()`: подпись зависит от языка клиента. `mouse_move` идёт почти непрерывно — внутри только запоминание позиции.
34. Скрипт можно продать на маркете: покупателю он приходит marshalled-байткодом в памяти, исходник на диск не пишется. Ассеты такого скрипта задавай ссылкой (`image(url)`, `assets.ttf(name, url)`, `assets.download(url)`), а не путём: файлов рядом со скриптом у покупателя нет, и `assets.image` с несуществующим путём выгрузит скрипт целиком.

### Ремап-сейф идиомы (копируй как есть)

```python
MOVE = "net.minecraft.network.packet.c2s.play.PlayerMoveC2SPacket"

@events.attack
def on_attack(e):
    ent = e.getEntity()                       # обёртка уже на месте
    client.msg(str(ent.getNameForScoreboard()))   # НЕ getName().getString()

@events.send_packet
def on_send(e):
    p = e.getPacket()
    if is_instance(p, MOVE):                  # ловит и наследников ($Full, ...)
        print(p.x, p.y, p.z, p.onGround)      # ПОЛЯ, а не p.getX()

aura = client.find("Aura")                    # find() отдаёт None, если модуля нет
if aura is not None and aura.isEnabled():     # try/except тут НЕ нужен
    client.msg("Aura включена")
```

## Карта справочников (progressive disclosure)

Запрашивай раздел справочника только когда задача его касается:

| Раздел | Когда читать |
|---|---|
| `script_api section=api` | Полный справочник API: модули, настройки, интроспекция `PySetting`, цвета/шрифты/ассеты, свои шейдеры GLSL (`shader`), `world`/`mc`, Aura и ротации, storage/Timer/vec, потоки, все методы `CustomDrawContext`. Читай при любой нетривиальной задаче. |
| `script_api section=events` | Все 58 событий: отменяемость, точные поля, пример подписки на каждое. Читай, когда нужно событие, которого нет в скелете. |
| `script_api section=ui` | HUD (render / layout / signature), Dynamic Island, `screen` и `raw_screen`, ui-билдер: все контейнеры, виджеты и ВСЕ стилевые kwargs. Читай для любого меню/HUD/оверлея. |
| `script_api section=recipes` | Готовые копируемые скрипты: HUD с координатами и FPS, ESP через `render_3d`, уведомление об атаке, меню на ui-билдере, фоновый поток с очередью и корректным гашением, storage, свой режим ротации Aura. Начинай отсюда, если задача похожа на один из рецептов. |

## Чек-лист перед выдачей скрипта

- [ ] Нет `import` глобалов клиента (`Module`, `events`, `mc` — уже в неймспейсе).
- [ ] Все использованные методы и события реально существуют (сверься с `script_api section=api` и `script_api section=events`; ничего не придумывай).
- [ ] Объекты Minecraft (сущность, пакет, ItemStack, BlockPos, Vec3d) зовутся напрямую, без `wrap(...)`.
- [ ] Имя сущности берётся через `getNameForScoreboard()`, а не `getName().getString()`.
- [ ] Тип пакета проверяется через `is_instance(...)`, а не `isinstance`.
- [ ] Модуль проверяется через `mod.isEnabled()`, а не через несуществующие `on_enable`.
- [ ] `Mode` сравнивается строкой (`setting.get() == "Head"`), а не через `is(...)`.
- [ ] У `Slider` порядок `.min().max().step().set()`.
- [ ] Результат `client.find` / `modules.find` проверен на `None` (try/except тут не нужен).
- [ ] Сеттер `ui.switch` / `ui.toggle` принимает аргумент (`lambda v: ...`); клик `ui.toggle_c` — без аргумента.
- [ ] `on_click` висит на `ui.row`/`ui.column`, а не на `ui.text`/`ui.image`/`ui.swatch`.
- [ ] У созданного `IslandStatus(...)` вызван `.selected(True)`.
- [ ] `render3d.marker` / `line` получают точки `[x, y, z]`, а не сущность.
- [ ] Сотни фигур за кадр рисуются пачкой (`render3d.billboards` / `render3d.lines`), а не поштучно в цикле.
- [ ] У `render3d.text` размер задан **в блоках** (0.25 это четверть блока), а строка померена `render3d.text_width`, а не `font(...).width(...)`.
- [ ] `music.current()` / `music.current_lyric()` проверены на `None`: плеера может не быть вовсе.
- [ ] Звук из тика или отрисовки заводится через `sound.once` только по событию, а не каждый кадр: голосов у скрипта не больше 32.
- [ ] `Shader(...)` вызван в теле скрипта, а не в отрисовке; у каждого цикла в GLSL есть предел.
- [ ] `notify` не вызывается внутри обработчика `notification` без проверки (иначе вечный круг).
- [ ] Цель через `target.best(...)` считается в `tick`, а не в каждом кадре отрисовки.
- [ ] Цвета `theme.*` берутся при отрисовке, а не сохранены в переменную при загрузке.
- [ ] Данные `profile.*` читаются там, где нужны (в теле скрипта профиля ещё нет), и это свойства без скобок.
- [ ] Слои вокруг меню (`menu_render` / `post_menu_render`) берут координаты из `menu.panels` в самом обработчике и гасятся по `menu.alpha`.
- [ ] Слои вокруг HUD (`hud_render` / `post_hud_render`) читают `hud.elements` в обработчике, пропускают элементы с нулевой `alpha` и учитывают `scale`.
- [ ] У своей команды первый параметр `ctx`, имя не совпадает со встроенной командой клиента.
- [ ] Задача `newton` не перезапускается в `newton_failed` без проверки причины (`отменён` — это твоя же отмена).
- [ ] В обработчике `key` есть проверка `isScreenOpen()`, клавиша сравнивается с кодом из `keys`, а `cancel()` стоит только по условию (и на нажатие, и на отпускание).
- [ ] Нет обращений к `mc` / модулям / HUD из чужого потока.
- [ ] Есть защита от `None` (`world.ingame()`, `mc.player is None`).
- [ ] Свои переменные не затеняют глобальные имена.
