# Rockstar Script API — полный справочник

Источник правды по коду клиента: `prelude.py` (формирует неймспейс), Java-классы `pyrock/**`, загрузчик `systems/python/**`, команда `.py`.

**Язык: Python 3 через Jep. Lua в клиенте нет.** Файлы: `<gameDir>/scripts/*.py`, где `gameDir = client.gameDir()`.

---

## 1. Жизненный цикл скрипта

- Каждый `.py` в `scripts/` — отдельный скрипт. Имя скрипта = имя файла без расширения.
- Тело файла выполняется **один раз** при загрузке (`exec` в собственном namespace) — это «конструктор»: создаём модули, настройки, HUD, подписываемся на события.
- Глобальные имена инжектятся автоматически. **Импортировать их нельзя.**
- При выгрузке (`unload`) автоматически снимаются все модули, HUD-элементы, настройки и обработчики скрипта.
- **Авто-reload:** файл watch'ится, сохранение → перезагрузка скрипта.
- Ошибка в обработчике события → `[Python Error]` в чат и скрипт **выгружается**.
  - Сообщение в чате **без трейсбека** (и обрезано по первому `:`) — полный трейсбек ищи в `latest.log`.
  - ⚠️ После падения **слежение за файлом умирает**: сохранение файла больше не перезагрузит скрипт. Нужен `.py load <имя>` (или `.py reload`).
- `print(...)` → лог клиента (latest.log). В чат — `client.msg(...)`.
- Включённость скриптов сохраняется в аккаунте (`client.rock`) и переживает перезаход.

### Команда `.py` (алиасы `.script`, `.python`)

| Команда | Алиасы | Что делает |
|---|---|---|
| `.py list` | | список скриптов + статус (кликабельно) |
| `.py load <имя>` | `use`, `enable`, `true` | включить скрипт |
| `.py unload <имя>` | `disable`, `off`, `false` | выключить |
| `.py toggle <имя>` | | переключить |
| `.py reload` | `update` | пересканировать папку и перезагрузить всё |
| `.py create <имя>` | `add` | создать новый файл-скрипт из шаблона; на занятом имени откажется |
| `.py delete <имя>` | `remove`, `del` | удалить файл |
| `.py install <пакет>` | `pip`, `i` | `pip install` во встроенный python-runtime |
| `.py sync` | `push`, `upload` | отправить скрипты на сайт вручную; штатно они уезжают сами при сохранении файла |
| `.py dir` | `direction` | открыть папку скриптов в проводнике |

> ℹ️ **`.py save` ничего не пишет и не перезаписывает** — клиент только напомнит, что скрипт правят прямо в файле `<gameDir>/scripts/`. Создаёт новый файл `.py create`, и на занятом имени он тоже откажется: потерять код этими командами нельзя.

---

## 2. Глобальный неймспейс

| Имя | Тип | Назначение |
|---|---|---|
| `Module` / `module` | фабрика | создать модуль чита |
| `Checkbox` / `checkbox` | фабрика | настройка-галка |
| `Slider` / `slider` | фабрика | настройка-слайдер |
| `Mode` / `mode` | фабрика | настройка-выбор одного |
| `Select` / `select` | фабрика | настройка-мультивыбор |
| `Button` / `button` | фабрика | настройка-кнопка |
| `Range` | фабрика | настройка-диапазон (двойной слайдер). Строчного `range` в неймспейсе НЕТ — builtin не затенён |
| `ColorSetting` / `colorsetting` | фабрика | настройка-цвет |
| `Bind` / `bind` | фабрика | настройка-клавиша |
| `TextSetting` / `textsetting` | фабрика | настройка-строка (поле ввода) |
| `TimeSetting` / `timesetting` | фабрика | настройка-время (часы/минуты/секунды) |
| `Gradient` / `gradient` | фабрика | настройка-градиент из двух цветов |
| `PositionSetting` / `positionsetting` | фабрика | настройка-точка на площадке |
| `Bezier` / `bezier` | фабрика | настройка-кривая плавности |
| `Blocks` / `blocks` | фабрика | настройка-сетка блоков |
| `Info` / `info` | фабрика | заголовок секции: делит список настроек на группы |
| `Color` / `color` | фабрика | `Color(r,g,b[,a])`, `Color.from_hex("#fff")` |
| `ColorRGBA` | класс | сырой Java-класс цвета (константы `WHITE`/`BLACK`/`RED`/...) |
| `border` | функция | `border(r)` → BorderRadius (все углы) |
| `border4` | функция | `border4(tl, tr, br, bl)` → BorderRadius |
| `events` | объект | подписка на события |
| `client` | объект | API клиента |
| `modules` | объект | = `client.modules` |
| `settings` | объект | = `client.settings` |
| `messages` | объект | = `client.messages` |
| `ui` | объект | = `client.ui` (курсор, border) |
| `hud` / `HUD` / `Hud` | объект | HUD-элементы |
| `IslandStatus` / `island_status` | класс | создать статус Dynamic Island (как `Module(...)`) |
| `island` / `dynamic_island` / `DynamicIsland` | объект | менеджер статусов Dynamic Island (`find`/`all`/`mine`/`remove`) |
| `screen` | декоратор | экран/меню с лейаутом |
| `raw_screen` / `screen_raw` | декоратор | экран с «голым» рисованием |
| `paths` | объект | `root()` (= `client.gameDir()`), `scripts()`, `runtime()` |
| `fonts` / `font` | объект | `font("medium", 8)` |
| `assets` | объект | картинки, шрифты, пути |
| `mc` | обёртка `_J` | MinecraftClient (`mc.player`, `mc.world`, `mc.options`) |
| `jimport` | функция | `jimport("net.minecraft.entity.LivingEntity")` |
| `is_instance` / `isInstance` | функция | проверка класса по полному named-имени |
| `wrap` / `unwrap` | функция | ручная обёртка/распаковка Java-объекта (нужна редко) |
| `world` | объект | сущности, игроки, цель |
| `newton` | объект | ходьба, полёт на элитре, копка, области |
| `command` | декоратор | своя команда чата: `@command("hello")` |
| `commands` | объект | команды: `add`, `remove`, `exists`, `all`, `run`, `prefix` |
| `notify` | объект | уведомления клиента |
| `inventory` / `inv` | объект | инвентарь: поиск, счётчики, перекладывание |
| `container` / `chest` | объект | открытое чужое меню: содержимое слотов и клики по ним |
| `effects` / `buffs` | объект | баффы и дебаффы игрока: список, время, иконки |
| `theme` / `colors` | объект | цвета текущей темы |
| `profile` / `account` / `user` | объект | аккаунт игрока: ник, uid, роль, подписка, аватарка (= `client.profile`) |
| `menu` | объект | меню клиента: тип, анимация, координаты панелей (= `client.menu`) |
| `target` | объект | выбор цели правилами клиента |
| `funtime` / `ft` | объект | данные FunTime |
| `aura` | объект | Aura: свои режимы ротации |
| `rotations` | объект | ротации вне Aura |
| `music` | объект | что играет на компьютере: трек, обложка, текст песни, управление |
| `sound` / `audio` / `sounds` | объект | свои звуки: wav, mp3 и ogg из папки скрипта или по ссылке |
| `render3d` / `render_3d` | объект | 3D-рендер |
| `shader` / `shaders` | объект | свои шейдеры GLSL |
| `Timer` | класс | таймер |
| `storage` | объект | JSON-хранилище |
| `vec` | объект | 3D-математика |
| `print` | функция | лог клиента |

> **Затенение имён.** Не используй под свои переменные: `module`, `color`, `border`, `select`, `mode`, `slider`, `button`, `checkbox`, `bind`, `info`, `gradient`, `bezier`, `blocks`, `settings`, `image`, `texture`, `font`, `fonts`, `world`, `screen`, `storage`, `vec`, `ui`, `hud`, `client`, `events`, `mc`, `assets`, `paths`, `modules`, `messages`, `island`, `music`, `sound`, `audio`, `container`, `chest`, `aura`, `newton`, `command`, `commands`, `notify`, `inventory`, `effects`, `buffs`, `theme`, `colors`, `profile`, `account`, `user`, `menu`, `target`, `funtime`, `rotations`, `wrap`, `unwrap`, `is_instance`.
> Builtins (`range`, `len`, `print`) НЕ затеняются — в неймспейсе только `Range` с большой буквы.

---

## 2.1. Ремап: мост, `is_instance`, `jimport` — ЧИТАТЬ ОБЯЗАТЕЛЬНО

В релизной сборке классы и методы Minecraft **обфусцированы** (`getX()` → `method_23317` и т.п.). Named-имена подставляет мост `McBridge`, а подключён он обёрткой `_J`.

**Обёрнуто всё, что отдаёт API — готовить руками нечего:**
объект события и всё, что вернули его геттеры (сущность, пакет, `ItemStack`, `BlockPos`, `Vec3d`, `Camera`, матрицы), `mc` и всё, что через него достаётся (`mc.player`, `mc.world`, `mc.options`, `mc.getSession()`), `world.*`, `inventory.stack()`, `target.*`, `aura.target()`, `jimport(...)`.

```python
@events.attack
def on_attack(e):
    ent = e.getEntity()                  # обёртка уже на месте
    print(ent.getX(), ent.getNameForScoreboard())
```

`wrap(...)` остался как ручная обёртка и **идемпотентен**: старый код вида `wrap(e.getEntity())` работает как работал, просто лишний. Обратная операция — `unwrap(obj)`, нужна редко (отдать сырой Java-объект в чужую библиотеку).

**Чего мост НЕ умеет:**

- **Перегрузку ищет сперва по числу аргументов, и только среди совпавших — по типам.** Если named-метод объявлен с 1 аргументом, вызвать его без аргументов не выйдет (пример — `PlayerMoveC2SPacket.getX()`, у которого argc=1; читай **поле** `p.x`). Передал `None` — тип определять не по чему, возьмётся первая перегрузка с таким числом аргументов.
- **`dir()` на `_J` не работает** — обёртка не отдаёт список методов. `dir()` работает только на Jep-объектах клиента (`PyModule`, `PySetting`).
- **Классы вне маппингов** (наши события, `moscow.rockstar.*`, java.*, brigadier, authlib, joml) мост зовёт по имени **как есть** — это рабочий путь, но имя должно совпадать буква в букву. Для имени сущности всё равно надёжнее `getNameForScoreboard()`, чем `getName().getString()`.

**Проверка типа — `is_instance`:**

```python
MOVE = "net.minecraft.network.packet.c2s.play.PlayerMoveC2SPacket"

@events.send_packet
def on_send(e):
    p = e.getPacket()
    if is_instance(p, MOVE):
        print(p.x, p.y, p.z, p.yaw, p.pitch, p.onGround)   # ПОЛЯ, не геттеры!
```

`isinstance(...)` и `obj.getClass().getName()` в релизе молча не сработают. `is_instance` ловит и наследников (`$Full`, `$LookAndOnGround`, ...). Старый вызов `McBridge.isInstance(obj, fqn)` (`from pyrock import McBridge`) тоже работает.

---

## 3. Модули

```python
mod = Module("MyModule", "Combat")     # имя, категория
mod.setDesc("Описание модуля")         # fluent — возвращает self
```

**Категории** (регистр не важен): `Combat`, `Movement`, `Visuals`, `Player`, `Other`. Неизвестная → `Other`.

Методы `PyModule`:

| Метод | Возврат | Описание |
|---|---|---|
| `isEnabled()` | bool | включён ли |
| `setEnabled(bool)` | self | вкл/выкл |
| `toggle()` | self | переключить |
| `getName()` | str | имя |
| `getCategory()` | str | категория. У СВОЕГО модуля — ровно та строка, что передали в конструктор (`"Combat"`); у чужого — enum в ВЕРХНЕМ регистре (`"COMBAT"`). Сравнивай без учёта регистра |
| `getDesc()` / `setDesc(str)` | str / self | описание. `setDesc()` работает **только со своим** модулем (у чужого — no-op) |
| `getKey()` / `setKey(int)` | int / self | бинд (GLFW-код) |
| `getKeyName()` | str | имя клавиши |
| `settings()` | PySetting[] | настройки с интроспекцией |

**Колбэков `on_enable` / `on_disable` НЕТ.** Варианты реакции на включение:

```python
# 1) проверка внутри события
@events.tick
def tick(e):
    if mod.isEnabled():
        ...

# 2) событие module_toggled
@events.module_toggled
def on_toggle(e):
    if e.getModule().getName() == "MyModule":
        client.msg("включён" if e.isState() else "выключен")
```

### Чужие модули

> ℹ️ **`find` возвращает `None`, если модуля нет** — исключения он не бросает, `try/except` вокруг него не нужен. Это касается `client.find`, `modules.find`, `modules.get`. КОНТРАСТ: `modules.require(name)` на неизвестном имени бросает `ValueError` — и через `require` работают `enable/disable/toggle`, значит они тоже бросят `ValueError`. `modules.enabled(name)` вернёт `False`.

```python
client.modules.all()            # список всех PyModule

aura_mod = client.find("Aura")  # PyModule или None, если модуля нет
if aura_mod is not None and aura_mod.isEnabled():
    ...

client.modules.require("Aura")  # PyModule или ValueError, если модуля нет

client.modules.enabled("Aura")  # bool (False, если модуля нет)
client.modules.enable("Aura")   # через require → ValueError, если модуля нет
client.modules.disable("Aura")
client.modules.toggle("Aura")

client.find("Aura")             # то же, что modules.find → PyModule или None
client.find("Aura", "Range")    # настройка модуля → Py*Setting или None
```

`client.find(module, setting)` умеет отдавать только настройки типов **boolean / slider / mode / select / range / color / button**. Для остальных типов (`bind`, `text`, `time`, `gradient`, `position`, `bezier`, `blocks`, `info`) он вернёт `None` — их достают через `mod.settings()` (см. `PySetting` ниже). Неизвестное имя настройки (при существующем модуле) → тоже `None`. Неизвестное имя модуля → тоже `None`.

---

## 4. Настройки

Создаются с привязкой к модулю (или к HUD-элементу — первым аргументом).

```python
mod = Module("Demo", "Visuals")

enabled = Checkbox(mod, "Enabled")
speed   = Slider(mod, "Speed").min(1).max(10).step(0.5).set(5).suffix(" м/с")   # порядок важен!
target  = Mode(mod, "Target").add("Head").add("Body")        # "Head" выбран автоматически
filters = Select(mod, "Filters").add("Players").add("Mobs").select("Players").min(1).draggable()
btn     = Button(mod, "Run").action(lambda: client.msg("клик"))
rng     = Range(mod, "Range").min(0).max(20).step(1).first(3).second(7)
col     = ColorSetting(mod, "Color").color(255, 0, 0).alpha(True)

hotkey  = Bind(mod, "Hotkey").set("G")                       # код GLFW или имя клавиши
nick    = TextSetting(mod, "Nick").maxLength(16).set("Steve")
pause   = TimeSetting(mod, "Pause").units("minutes", "seconds").set(90)   # значение в СЕКУНДАХ
grad    = Gradient(mod, "Gradient").set(Color(255, 0, 90), Color(90, 0, 255))
offset  = PositionSetting(mod, "Offset").bounds(-1, -1, 1, 1).set(0, 0)
curve   = Bezier(mod, "Easing").start(0.2, 0.0).end(0.8, 1.0)
blocks  = Blocks(mod, "Blocks").select("obsidian")            # id как в игре
Info(mod, "Заголовок секции")                                 # значения нет
```

| Тип | Конструктор | Fluent-методы | Чтение |
|---|---|---|---|
| `Checkbox` | `(target, name)` | `set(bool)` | `get() -> bool`, `toggle()` |
| `Slider` | `(target, name)` | `min(n) max(n) step(n) set(n) suffix(s)` | `get() -> float`, `getMin() getMax() getStep()` |
| `Mode` | `(target, name)` | `add(name)`, `select(name)` | `get() -> str` (сравнивай строкой: `mode_setting.get() == "Head"`) |
| `Select` | `(target, name)` | `add(name)`, `select(name)`, `min(int)`, `draggable()` | `isSelected(name)`, `getSelected() -> [str]`, `getValues() -> [str]` |
| `Button` | `(target, name)` | `action(fn)` | `click()` |
| `Range` | `(target, name)` | `min max step first second` | `get() -> [float, float]`, `getFirst() getSecond()`, `getMin() getMax() getStep()` |
| `ColorSetting` | `(target, name)` | `color(ColorRGBA)`, `color(r,g,b[,a])`, `alpha(bool)` | `get() -> ColorRGBA`, `hasAlpha()` |
| `Bind` | `(target, name)` | `set(code \| "G")`, `clear()` | `get() -> int`, `name() -> str`, `isKey(code \| "G")`, `isSet()` |
| `TextSetting` | `(target, name)` | `set(str)`, `maxLength(int)`, `numberOnly(bool)` | `get() -> str`, `isEmpty()` |
| `TimeSetting` | `(target, name)` | `set(seconds)`, `units(*names)`, `unit(name, bool)`, `maxHours(int)`, `maxMinutes(int)` | `get() -> int` (секунды), `millis()`, `ticks()`, `formatted()`, `hours() minutes() seconds()` |
| `Gradient` | `(target, name)` | `set(c1, c2)`, `first(c)`, `second(c)`, `alpha(bool)` | `getFirst()`, `getSecond()`, `at(0..1) -> ColorRGBA`, `hasAlpha()` |
| `PositionSetting` | `(target, name)` | `set(x, y)`, `x(n)`, `y(n)`, `bounds(minX, minY, maxX, maxY)` | `get() -> [float, float]`, `getX() getY()`, `getMinX() getMaxX() getMinY() getMaxY()` |
| `Bezier` | `(target, name)` | `start(x, y)`, `end(x, y)` | `ease(0..1) -> float`, `interpolate(from, to, 0..1)`, `getStart()`, `getEnd()` |
| `Blocks` | `(target, name)` | `select(id)`, `toggle(id)`, `allow(id)`, `allowAll()`, `allowItem(id)`, `allowAllItems()` | `getSelected() -> [str]`, `isSelected(id)`, `count()` |
| `Info` | `(target, name)` | `level(int)` крупнее, `splitted()` перенос по строкам, `centered()` по центру | значения нет |

**Дефолты:** Slider `min=1 max=10 value=5 step=1`; Range `min=1 max=10 first=3 second=7 step=1`; Checkbox выключен; ColorSetting белый, `alpha=True`; Gradient оба цвета белые; PositionSetting поле `-1..1`, точка в `(0, 0)`; TimeSetting все три колонки, значение `0`; Bezier `start=(0,0) end=(1,1)`; Blocks в сетке все блоки, отмеченных нет.

> ⚠️ **У `Bind` сравнение называется `isKey(...)`, а не `is(...)`** — по той же причине, что и у `Mode`: `is` это ключевое слово Python. И `set`, и `isKey` принимают как GLFW-код, так и имя клавиши (`"G"`, `"LEFT_SHIFT"`, `"LMB"`).

> **Бинд бывает сочетанием.** Игрок в меню держит Ctrl и нажимает G — клиент запоминает `CTRL + G` одним числом (клавиша в младших битах, модификаторы в старших). Скрипту это прозрачно: `isKey(event.getKey())` сам проверит, что модификаторы зажаты, а `name()` вернёт `"CTRL + G"`. Из скрипта сочетание задают строкой: `set("CTRL+G")`, `keys.code("ALT+SHIFT+F")`. Раскладывать число руками не нужно.

> ⚠️ **`TimeSetting.units()` перечисляют аргументами, а не списком:** `units("minutes", "seconds")`. Списком не заработает: перегрузки Java резолвятся по числу аргументов.

> ⚠️ **`Blocks` читается полными именами.** `select("obsidian")` и `select("minecraft:obsidian")` делают одно и то же, но `getSelected()` всегда вернёт `["minecraft:obsidian"]`.

> ⚠️ **`Blocks`: `allow(...)` вызывают ДО `select(...)`.** Сужение сетки выкидывает из отмеченных всё, чего в ней больше нет, поэтому `.select("obsidian").allow("stone")` оставит настройку пустой.

> ⚠️ **`Slider.set()` клампится по ТЕКУЩЕМУ шагу.** Шаг по умолчанию = 1, поэтому `.set(3.5).step(0.1)` даст **4.0**, а не 3.5.
> Единственно верный порядок: **`.min() → .max() → .step() → .set()`**. То же и у `Range` (`step` до `first`/`second`).

> ⚠️ **`Mode` сам выбирает ПЕРВЫЙ добавленный вариант.** `select("Head")` после `add("Head")` — лишний вызов; `select()` нужен, только если дефолтом должен быть не первый вариант.

⚠️ **У `Mode` есть Java-метод `is(name)`, но из Python он НЕВЫЗЫВАЕМ** — `is` это ключевое слово Python (`style.is("Head")` — SyntaxError). Сравнивай строку:

```python
style = Mode(mod, "Style").add("Head").add("Body")   # "Head" выбран сам (первый add)

if style.get() == "Head":     # ПРАВИЛЬНО
    print("head")
```

### Интроспекция чужих настроек — `PySetting` (`mod.settings()`)

`type()` → `"boolean" | "slider" | "range" | "mode" | "select" | "color" | "button" | "bind" | "text" | "time" | "gradient" | "position" | "bezier" | "blocks" | "info" | "other"`

| Группа | Методы |
|---|---|
| общее | `name()` (подпись из меню), `rawName()` (постоянное имя), `visible()`, `type()` |
| boolean | `boolGet()`, `boolSet(b)`, `boolToggle()` |
| slider | `numGet()`, `numSet(v)`, `numMin()`, `numMax()`, `numStep()` |
| mode | `optionLabels()`, `options()`, `modeIndex()`, `modeSelect(i)` |
| select | `optionLabels()`, `selOn(i)`, `selToggle(i)`, `selCount()` |
| color | `colorGet()`, `colorSet(c)` |
| button | `click()` |
| bind | `bindKey()`, `bindName()`, `bindSet(key)` |
| text | `textGet()`, `textSet(v)` |
| time | `timeGet()` (секунды), `timeSet(seconds)`, `timeMillis()`, `timeTicks()`, `timeFormatted()` |
| gradient | `gradientFirst()`, `gradientSecond()`, `gradientSet(c1, c2)` |
| position | `posX()`, `posY()`, `posSet(x, y)` |
| bezier | `bezierEase(0..1)` |
| blocks | `blocksSelected()`, `blockSelected(id)`, `blockToggle(id)` |

Используется, чтобы нарисовать чужие настройки своими виджетами (кастомные меню). Неизвестный тип — фолбэк на клиентский рендер: `ui.setting(ps)`.

### Бинды

Бинд модуля (клавиша включения): `mod.setKey(glfw_code)` / `mod.getKeyName()`. Обычно его назначает игрок в меню.

Клавиша под своё действие — настройка `Bind`: рисуется в меню такой же строкой, игрок назначает её мышью,
скрипт сравнивает её с клавишей из события `key`. Игрок может назначить сочетание (`CTRL + G`) — сравнение
это учитывает само.

```python
hotkey = Bind(mod, "Hotkey").set("G")


@events.key
def on_key(event):
    if not event.isPress() or not hotkey.isKey(event.getKey()):
        return
    client.msg("нажали " + hotkey.name())
```

---

## 5. События (кратко)

Подписка (имя нечувствительно к регистру):

```python
@events.tick
def on_tick(event): ...

events.tick(on_tick)
events.tick.on(on_tick)
events.getEvent("tick").on(on_tick)
```

Колбэк получает **сырой Java-объект события** — вызывай настоящие геттеры. Отменяемые: `event.cancel()`, `event.isCancelled()`.
**То, что геттер ВЕРНУЛ (сущность, пакет, стек, позиция), приходит обёрнутым — зови методы сразу** (см. раздел 2.1).

Всего событий 59: `tick`, `motion`, `input`, `move_post`, `travel_post`, `slowdown`, `attack`, `after_attack`, `block_break`, `block_place`, `entity_jump`, `pickup`, `firework`, `rotate_camera`, `send_message`, `world_change`, `send_packet`, `receive_packet`, `connect`, `disconnect`, `render_2d`, `pre_render_2d`, `render_3d`, `pre_render_3d`, `module_toggled`, `newton_started`, `newton_path`, `newton_node`, `newton_finished`, `newton_failed`, `game_tick`, `tick_end`, `keep_sprint`, `trace`, `collision_shape`, `sound`, `entity_death`, `finish_eat`, `effect_added`, `effect_removed`, `start_break_block`, `break_totem`, `set_cooldown`, `close_screen`, `container_click`, `hand_render`, `camera_update`, `game_render`, `notification`, `key`, `char_typed`, `mouse`, `scroll`, `mouse_move`, `language_changed`, `menu_render`, `post_menu_render`, `hud_render`, `post_hud_render`.

Событий больше нет. В частности, `PostHudRenderEvent` и события чата существуют в клиенте, но **скрипту недоступны** (у них нет `@EventInfo`). `@events.tick` — это тик игрока (`ClientPlayerTickEvent`), тик игры — отдельное `game_tick`, которое идёт и вне мира.

🔥 `collision_shape` зовётся на КАЖДЫЙ блок рядом с каждой движущейся сущностью — тысячи раз за тик. Обработчик держи в 2-3 строки с ранним выходом; `print`/`client.msg` там вешают игру.
`render_2d` / `pre_render_2d` приходят только **в игре** (из InGameHud) — на главном экране их нет.

**Полные поля и примеры — `script_api section=events`.**

---

## 6. Цвета, шрифты, ассеты

### Цвет

```python
c = Color(255, 0, 0)                # r,g,b (0..255), alpha=255
c = Color(255, 0, 0, 128)           # с альфой
c = Color.from_hex("#ff0000")       # или from_hex("#ff0000aa")
c = Color.from_int(0xFFFF0000)
c = Color.from_hsb(0.5, 1.0, 1.0)   # 0..1

ColorRGBA.WHITE / BLACK / RED / GREEN / BLUE / YELLOW

c.withAlpha(120)      # копия с другой альфой (0..255)
c.mulAlpha(0.5)       # умножить альфу
c.mix(other, 0.5)     # смешать
c.toHex()             # "#rrggbbaa"
```

### Шрифт

```python
f = font("medium", 8)                  # weight, size
client.font_width("medium", 8, "text") # ширина текста
client.font_height("medium", 8)
```

Веса: `noto`, `bold`, `medium`, `regular`, `semibold`, `roundbold`.

### Скругления

```python
border(6)                 # все углы
border4(10, 0, 10, 0)     # tl, tr, br, bl
```

### Ассеты

```python
tex = assets.image("assets/logo.png")   # путь относительно папки scripts/
tex = assets.image("https://site.ru/logo.png")   # или ссылка: качается один раз, дальше с диска
assets.resource("gui/icon.png")         # ТОЛЬКО ресурсы клиента (assets/rockstar/...)
assets.ttf("Inter", "assets/Inter.ttf", 9)                       # свой шрифт из ttf/otf
assets.ttf("Inter", "https://site.ru/Inter.ttf", 9)              # он же по ссылке
assets.svg("моё/сердце", "assets/heart.svg")                     # свой значок из svg
assets.svg_text("моё/звезда", "<svg viewBox='0 0 24 24'>...</svg>")  # он же прямо из кода
assets.download("https://site.ru/data.json", on_ready)           # любой другой файл: путь к копии
assets.scripts_dir()

paths.root()        # <gameDir> = .minecraft/Rockstar (папка клиента)
paths.scripts()     # <root>/scripts
paths.runtime()     # <root>/runtime  (сам CPython и site-packages лежат глубже: <root>/runtime/python)
```

Картинка кэшируется и перечитывается при изменении файла на диске. Если файла нет — оборачивай в `try/except` и рисуй без картинки.

Ссылка `http(s)://` работает везде, где ждут путь: файл скачивается один раз в папку клиента, со второго
запуска берётся с диска. Картинка отдаёт пропуск сразу (до загрузки пустой, потом появляется сама), шрифт
до загрузки рисуется запасным начертанием, `assets.download` вернёт путь, если файл уже скачан, иначе
`None` и позовёт колбэк на главном потоке.

⚠️ Кеш вечный, ссылка считается неизменной: поменялся файл на сайте — меняй ссылку (`?v=2`).
⚠️ Больше 32 МБ клиент не качает; промах (нет сети, не тот адрес) уходит в лог и скрипт не роняет.

Свой значок из svg рисуется дальше как встроенный: `d.icon("моё/сердце", x, y, size=10, color=Color(255, 80, 80))`, `ui.icon("моё/сердце", size=12)`. Имя даёшь сам, поэтому бери с префиксом скрипта: оно общее на все скрипты, и короткое `star` может занять сосед.

⚠️ **Значок одноцветный.** Он рисуется как буква, цветом из аргумента: заливки и градиенты внутри файла не переносятся, а фигуры с `fill="none"` (обводка) пропускаются целиком — контур должен быть залитой фигурой. Наборы вроде Lucide или Phosphor в варианте fill подходят, иллюстрация с цветами — нет.

⚠️ Понимаются `path`, `rect`, `circle`, `ellipse`, `polygon`, `line` и преобразования (`translate`, `scale`, `rotate`, `matrix`). Файл больше 512 КБ не берётся: разбор такого — секунды.

⚠️ Значков у скрипта не больше 64, и заводят их **в теле скрипта**, а не в отрисовке. Тот же svg под тем же именем ничего не пересоздаёт, так что перезагрузка скрипта бесплатна. Имена снимаются вместе со скриптом.

> `assets.resource(path)` достаёт **только ресурсы клиента** (`assets/rockstar/…`). Ванильные текстуры Minecraft через него не получить — для них нужен `Identifier` (`jimport("net.minecraft.util.Identifier")`).

---

## 7. Сообщения и клиент

```python
client.msg("текст")       # в чат (info)
client.warn("текст")
client.error("текст")
client.overlay("текст")   # над хотбаром
client.gameDir()          # папка КЛИЕНТА: .minecraft/Rockstar (== paths.root()), а НЕ папка игры
client.menu_opened()      # открыто ли меню клиента
client.cursor("hand")
```

Типы курсора (регистр не важен): `arrow`/`default`, `hand`/`pointer`, `text`/`ibeam`, `crosshair`,
`hresize`/`horizontal`, `vresize`/`vertical`, `block`/`notallowed`, `resize`/`resizeall`.
Неизвестная строка → `default` (без ошибки).

---

## 8. Рисование 2D (`render_2d`, `pre_render_2d`)

```python
@events.render_2d
def draw(e):
    ctx = e.getContext()
    ctx.drawRect(10, 10, 100, 20, Color(255, 255, 255))
    ctx.drawRoundedRect(10, 40, 100, 20, border(6), Color(0, 0, 0, 180))
    ctx.drawText(font("medium", 8), "Привет", 12, 44, Color(255, 255, 255))
```

Методы `ctx` (`CustomDrawContext`):

| Метод | Сигнатура |
|---|---|
| `drawRect` | `(x, y, w, h, color)` |
| `drawRoundedRect` | `(x, y, w, h, border, color)` |
| `drawRoundedBorder` | `(x, y, w, h, thickness, border, color)` |
| `drawSquircle` | `(x, y, w, h, squirt, border, color)` |
| `drawSquircleBorder` | `(x, y, w, h, thickness, squirt, border, color)` |
| `drawShadow` | `(x, y, w, h, softness, border, color)` |
| `drawBlurredRect` | `(x, y, w, h, blurRadius, border, color)` или `(x, y, w, h, blur, squirt, border, color)` |
| `drawLiquidGlass` | `(x, y, w, h, squirt, power, border, color)` |
| `drawClientRect` | `(x, y, w, h, alpha, dragAnim, squircle[, radius[, outline]])` |
| `drawLoadingRect` | `(x, y, w, h, progress, border, color)` |
| `drawText` | `(font, text, x, y, color)` |
| `drawCenteredText` | `(font, text, x, y, color)` |
| `drawRightText` | `(font, text, x, y, color)` |
| `drawTextWithShadow` | `(font, text, x, y, color, shadowColor, offX, offY, blur)` |
| `drawTextWithOutline` | `(font, text, x, y, color, outlineColor, thickness[, steps])` — есть и `drawCenteredTextWithOutline`, `drawRightTextWithOutline` |
| `drawFadeoutText` | `(font, text, x, y, color, fadeStart, fadeEnd[, maxWidth])` |
| `drawIcon` | `(name, x, y, size[, color])` |
| `drawItem` | `(itemStack, x, y, size)` |
| `drawEffect` | `(effect, x, y, size[, color])` — эффект объектом или именем (`"speed"`) |
| `drawHead` | `(entity, x, y, size, border, color)` |
| `drawTexture` | `(identifier, x, y, w, h[, color])` |
| `drawRoundedTexture` | `(identifier, x, y, w, h, border[, color])` |
| `drawEntity` | `(x1, y1, x2, y2, size, f, mouseX, mouseY, entity)` |
| `drawArc` | `(x, y, size, thickness, startAngle, endAngle, color)` |
| `drawCircleProgress` | `(cx, cy, radius, thickness, progress, color)` |
| `drawLine` | `(Vec2f from, Vec2f to, color)` |
| `pushMatrix()` / `popMatrix()` | — |

> Помни: перегрузки Java резолвятся **по числу аргументов**. `drawBlurredRect` с 7 аргументами и с 8 — разные перегрузки.

---

## 9. HUD, Dynamic Island, экраны и UI-билдер

Кратко:

```python
el = Hud("MyHud", width=100, height=20, x=8, y=8)

@el.render
def draw(d):                  # координаты ОТНОСИТЕЛЬНЫЕ
    d.rect(0, 0, d.width, d.height, Color(0, 0, 0, 180))
    d.text("Привет", 4, 4, size=7, color=Color(255, 255, 255))
```

Главные грабли UI (детали — в `ui.md`):

- `IslandStatus(...)` **без `.selected(True)` не рисуется**.
- Сеттер `ui.switch` / `ui.toggle` получает НОВОЕ значение (`lambda v: ...`), а клик `ui.toggle_c` — без аргументов.
- `on_click` не работает на `ui.text` / `ui.image` / `ui.swatch` — вешай его на `ui.row(cursor="hand", on_click=...)`. `ui.icon` и `ui.button` кликабельны.
- `on_click_pos` даёт три аргумента: `fn(x, y, button)`, где `button` — строка (`left` / `right` / `middle`).
- `enter=` и `enter_slide=` конфликтуют (оба пишут в `el.enter(...)`) — используй что-то одно.
- `raw_screen(title, w, h)`: **title и размеры игнорируются**, холст всегда = весь экран.

**Полный раздел (HUD render/layout/signature, Dynamic Island, `screen` / `raw_screen`, все виджеты и стили ui-билдера) — `script_api section=ui`.**

---

## 10. 3D-рендер (`render_3d`)

```python
@events.render_3d
def draw(e):
    for p in world.players():
        render3d.box(e, p, Color(255, 0, 0))
```

Есть и второй момент кадра — `pre_render_3d`: те же методы, те же аргументы, но мир ещё не нарисован,
поэтому фигуры прячутся за блоками и существами. Всё, что игрок должен видеть сквозь стены, оставляй в `render_3d`.

| Метод | Что принимает вторым аргументом | Сигнатура |
|---|---|---|
| `render3d.depth` | — | `(on=True)` — считаться с блоками у всего, что рисуется дальше; годится и как `with render3d.depth():` |
| `render3d.depth_enabled` | — | `() -> bool` — стоит ли сейчас этот режим |
| `render3d.through_walls` | — | `(on=True)` — то же наоборот: рисовать сквозь блоки |
| `render3d.line` | **только точки** | `(event, start, end=None, color=None, through=None)` — два `[x,y,z]` или один список из 6 чисел |
| `render3d.marker` | **только точка** `[x, y, z]` | `(event, pos, size=0.18, color=None, through=None)` |
| `render3d.box` | сущность / Box / Vec3d | `(event, target, color=None, through=None)` |
| `render3d.filled_box` | сущность / Box / Vec3d | `(event, target, color=None, through=None)` |
| `render3d.glowing_box` | сущность / Box / Vec3d | `(event, target, color=None, through=None)` |
| `render3d.box_gradient` | сущность / Box / Vec3d | `(event, target, bottom_color, top_color, through=None)` |
| `render3d.filled_box_gradient` | сущность / Box / Vec3d | `(event, target, bottom, top, through=None)` |
| `render3d.box_at` | **координаты** | `(event, x, y, z, width, height, depth, color=None, through=None)` |
| `render3d.filled_box_at` | **координаты** | `(event, x, y, z, w, h, d, color=None, through=None)` |
| `render3d.ring` | сущность / Box / Vec3d | `(event, target, radius=0.8, y_offset=0.05, segments=48, color=None, through=None)` |
| `render3d.target` | сущность (или `None` → цель Aura) | `(event, target=None, color=None, through=None)` — композит |
| `render3d.billboard` | точка `[x, y, z]` | `(event, texture, pos, width=1.0, height=None, color=None, roll=0.0, additive=False, through=None)` |
| `render3d.effect` | точка `[x, y, z]` или сущность | `(event, effect, pos, size=0.5, color=None, roll=0.0, additive=False, through=None)` — иконка эффекта билбордом |
| `render3d.billboards` | плоский список чисел | `(event, texture, particles, additive=True, through=None)` — по 8 на частицу: `x, y, z, size, r, g, b, a` |
| `render3d.lines` | плоский список чисел | `(event, segments, additive=True, through=None)` — по 10 на отрезок: `x1, y1, z1, x2, y2, z2, r, g, b, a` |
| `render3d.text` | точка `[x, y, z]` или сущность | `(event, text, pos, size=0.25, color=None, font=None, outline=None, outline_width=0.06, outline_steps=4, shadow=None, shadow_offset=None, facing=True, yaw=0.0, pitch=0.0, roll=0.0, align="center", through=None, additive=False)` |
| `render3d.texts` | список надписей | `(event, items, ...)` — те же именованные параметры; `yaw`, `pitch` и `roll` задаются у элемента |
| `render3d.text_width` | строка | `(text, size=0.25, font=None) -> float` — ширина **в блоках** |
| `render3d.text_height` | размер | `(size=0.25, font=None) -> float` — шаг между строками |
| `render3d.letters` | строка | `(text, size=0.25, font=None) -> list[(символ, смещение, ширина)]` |

⚠️ **Сотни фигур рисуй пачкой.** Каждый одиночный вызов (`line`, `billboard`, `glowing_box`, …) — это отдельный draw call: сотня частиц или сетка из линий просаживают FPS не отрисовкой, а числом отправок на видеокарту. `billboards` / `lines` рисуют всю пачку за один вызов, 500 частиц стоят как одна. Цвет там задаётся числами 0..255, объект `Color` не нужен, поэтому и Java-вызовов на частицу нет:

```python
data = []
for p in particles:
    data.extend((p.x, p.y, p.z, 0.16, 120.0, 205.0, 255.0, 200.0))
render3d.billboards(event, texture, data, True)
```

Список плоский, без вложенности; лишний хвост, не кратный 8 (или 10), игнорируется. Частицы и их хвосты клади в один список.

### Стены

По умолчанию всё нарисованное видно сквозь блоки. Чтобы фигуры прятались за стенами, включи режим — он свой у каждого
скрипта и держится до следующего вызова, помечать каждое рисование не нужно:

```python
@events.render_3d
def draw(e):
    render3d.depth(True)               # дальше всё считается с блоками
    render3d.billboards(e, tex, data, True)

    with render3d.depth(False):        # а вот эту рамку видно всегда
        render3d.box(e, target, COL)
```

Флаг `through` у отдельного вызова важнее режима: `through=False` прячет за стенами, `through=True` рисует сквозь них,
`None` (по умолчанию) отдаёт решение режиму. Глубину мира мы только читаем, но не пишем, поэтому полупрозрачные фигуры
по-прежнему не закрывают друг друга.

⚠️ **Не путай две группы.**
`marker` / `line` с СУЩНОСТЬЮ — падают в релизе (внутри идёт прямой вызов `getPos()` на сыром MC-объекте). Передавай точку:

```python
p = world.self()
render3d.marker(event, [p.getX(), p.getY() + 1.0, p.getZ()], 0.2, Color(255, 0, 0))
render3d.line(event, [p.getX(), p.getY(), p.getZ()], [0, 64, 0], Color(255, 255, 255))
```

`box` / `filled_box` / `ring` со СПИСКОМ координат — молча ничего не нарисуют (Java `boxOf()` вернёт `null`). Для бокса по координатам есть `box_at` / `filled_box_at`.

### Текст в мире

```python
render3d.text(event, "hello", [x, y, z], 0.25, Color(255, 255, 255), outline=Color(0, 0, 0, 200))
```

⚠️ **`size` — высота ЗАГЛАВНОЙ БУКВЫ В БЛОКАХ**, а не кегль экрана: 0.25 это четверть блока. Мерить строку тоже надо в блоках, через `render3d.text_width`; `font("bold", 8).width(...)` меряет пиксели экрана и в мире не годится.

`pos` — точка `[x, y, z]` или сущность (тогда берётся её середина, как у `billboard`).

`facing`: `True` разворачивает надпись к камере целиком, `"y"` только по горизонту (надпись стоит вертикально и не заваливается при взгляде сверху), `False` оставляет её на месте по своим `yaw` / `pitch`. Углы считаются как у игрока, который смотрит на надпись, поэтому `pitch=90` кладёт текст на землю лицом вверх, а `yaw` можно брать прямо у себя (`world.self().getYaw()`).

`through=False` прячет надпись за блоками (по умолчанию видно сквозь стены, как у остального ESP), а `render3d.depth(True)` прячет всё, что скрипт рисует дальше.

⚠️ **Обводка стоит закраски, а не дроколлов.** Каждое направление это ещё одна копия буквы: вплотную к камере буква занимает пол-экрана, и восемь копий считаются восемь раз. По умолчанию `outline_steps=4` (крест), восемь берут только под широкую обводку; тень добавляет ещё одну копию. Игрок подошёл к надписи вплотную и просел FPS — дело в этом.

⚠️ **Много надписей — пачкой**, ровно как частицы: `render3d.texts` рисует всю пачку одним draw call. Элемент это словарь (`text`, `pos`, `size`, `color`, `roll`, `yaw`, `pitch`) или кортеж `(текст, точка, размер, цвет, наклон, yaw, pitch)`; обводка, тень и выравнивание задаются один раз на весь вызов, а их прозрачность подгоняется под прозрачность каждой надписи.

**Углы живут у элемента.** При `facing=False` каждая надпись в пачке смотрит куда хочет, оставаясь в том же единственном вызове, а `yaw` / `pitch` самого вызова остаются значением по умолчанию для тех, кто их не задал. Так делают буквы, каждая из которых летит и падает по-своему; при `facing=True` углы элемента не нужны — к камере разворачивается вся пачка.

```python
items = []
for p in world.players():
    items.append({"text": p.getName().getString(),
                  "pos": [p.getX(), p.getY() + 2.3, p.getZ()],
                  "size": 0.22, "color": Color(255, 255, 255)})
render3d.texts(event, items, outline=Color(0, 0, 0, 200))
```

`render3d.letters` нужна, когда каждая буква живёт отдельно (разлетается, падает, крутится): она отдаёт `(символ, смещение слева, ширина)` в блоках, дальше буквы кладут обычными элементами в `texts`.

---

## 10.1. Свои шейдеры GLSL (`shader`)

Фрагментный шейдер приходит обычной **строкой**, клиент компилирует его сам при загрузке скрипта.

```python
GLSL = """
uniform float Power;

void main() {
    vec2 center = Size * 0.5;
    float dist = roundedBoxSDF(center - FragCoord * Size, center - 1.0, vec4(8.0));
    float shape = 1.0 - smoothstep(1.0 - sdfAA(dist, 1.0), 1.0, dist);

    float wave = sin(FragCoord.x * 10.0 + Time * Power) * 0.5 + 0.5;
    fragColor = vec4(Color.rgb * (0.6 + 0.4 * wave), shape * Color.a);
}
"""

panel = Shader("panel", GLSL)          # ОДИН раз, в теле скрипта


@events.render_2d
def draw(e):
    panel.set("Power", 2.0)
    panel.color(Color(120, 200, 255))
    panel.rect(e.getContext(), 20, 20, 200, 60)
```

### Шапка дописывается сама

Версия языка, `out vec4 fragColor`, встроенные переменные и хелперы клиента дописываются клиентом.
**Объявляй только свои `uniform`** — повторное объявление встроенного имени это ошибка компиляции.
Текст, начатый с `#version 150`, уходит видеокарте как есть, без шапки (режим для готовых чужих шейдеров).

| Встроенное имя | Тип | Что это |
|---|---|---|
| `FragCoord` (алиас `TexCoord`) | `vec2` | точка внутри фигуры, 0..1; `(0,0)` слева сверху |
| `Size` | `vec2` | ширина и высота фигуры в gui-единицах |
| `Time` | `float` | секунды с запуска (по модулю 3600) |
| `Color` | `vec4` | цвет из `shd.color(...)` |
| `Resolution` | `vec2` | размер экрана |
| `MousePos` | `vec2` | курсор |
| `GuiScale` | `float` | масштаб интерфейса |
| `Sampler0..Sampler3` | `sampler2D` | картинки из `shd.texture(...)` |
| `CamPos` | `vec3` | позиция камеры (`fullscreen` / `quad3d`) |
| `InvViewProj` | `mat4` | обратная view-projection, мировая точка из экранной |
| `ModelViewMat`, `ProjMat` | `mat4` | матрицы кадра |

Хелперы из `common.glsl` клиента: `roundedBoxSDF(centerPos, halfSize, radii)` и `sdfAA(dist, smoothness)` —
ими делаются скруглённые углы со сглаживанием.

### API

| Метод | Сигнатура |
|---|---|
| `Shader(...)` | `(name, fragment, vertex=None) -> Shader` — собрать из текста (старая форма `shader.create`) |
| `shader.load` | `(name, fragment, vertex=None) -> Shader` — текст из файла рядом со скриптом |
| `shd.set` | `(name, a[, b, c, d])` — `float` / `vec2` / `vec3` / `vec4` |
| `shd.set_int` | `(name, value)` |
| `shd.color` | `(color, name="Color")` |
| `shd.texture` | `(unit, image)` — `assets.image(...)` в `Sampler<unit>`, unit 0..7 |
| `shd.matrix` | `(name, matrix)` |
| `shd.rect` | `(ctx, x, y, width, height)` — прямоугольник на экране |
| `shd.fullscreen` | `(event)` — эффект по всему кадру мира, из `render_3d` |
| `shd.quad3d` | `(event, pos, width, height=None, mode="billboard", additive=False, depth=False)` |
| `shd.mesh3d` | `(event, vertices, origin=(0,0,0), mode="triangles", colors=False, additive=False, depth=True, cull=False)` — своя геометрия в мире |
| `shd.mesh2d` | `(ctx, vertices, mode="triangles", colors=False)` — своя геометрия на экране |
| `shd.dispose` | `()` — снять; вместе со скриптом снимается сам |

В HUD-элементе есть короткая запись `d.shader(shd, x=0, y=0, w=None, h=None)`: координаты от угла элемента,
размер по умолчанию равен размеру элемента.

```python
@el.render
def draw(d):
    panel.color(Color(90, 180, 255).mulAlpha(d.alpha))
    d.shader(panel)
```

### Эффект по всему кадру мира

`fullscreen(event)` пропускает уже отрисованный кадр через шейдер: `Sampler0` — картинка мира,
`Sampler1` — глубина. Вызывай последним в обработчике `render_3d`.

```python
POST = """
uniform float Warp;

void main() {
    vec2 fromCenter = FragCoord - 0.5;
    float edge = dot(fromCenter, fromCenter);
    float spread = edge * 0.006 * Warp;

    vec3 color = vec3(
        texture(Sampler0, FragCoord + fromCenter * spread).r,
        texture(Sampler0, FragCoord).g,
        texture(Sampler0, FragCoord - fromCenter * spread).b
    );
    fragColor = vec4(color * (1.0 - edge * 0.45), 1.0);
}
"""

post = Shader("post", POST)


@events.render_3d
def world_pass(e):
    post.set("Warp", 1.0)
    post.fullscreen(e)
```

### Квад в мире

`quad3d(event, pos, width, height=None, mode=..., additive=False, depth=False)`, где `pos` — точка `[x, y, z]` или сущность.
Режимы: `billboard` (лицом к камере), `ground` (плашмя на земле), `wall` (стоймя, поворот только вбок).
`depth=True` включает тест глубины — квад прячется за блоками и сущностями; по умолчанию он рисуется поверх всего, как ESP.
Кольцо на земле поднимай на пару сотых блока (`pos.y + 0.02`): ровно на уровне поверхности с тестом глубины пойдёт рябь z-fighting.

```python
victim = target.current()
if victim is not None:
    p = victim.getPos()
    ring.color(Color(120, 200, 255))
    ring.quad3d(e, (p.x, p.y + 0.02, p.z), 2.4, mode="ground", additive=True, depth=True)
```

### Своя геометрия (`mesh3d` / `mesh2d`)

Квад и рект это готовые формы. Куб, сферу, спираль или модель скрипт считает сам и отдаёт вершины плоским списком.

| Формат вершины | Числа |
|---|---|
| `mesh3d` без цвета | `x, y, z, u, v` |
| `mesh3d` с `colors=True` | `x, y, z, u, v, r, g, b, a` (цвет 0..255, в шейдере `VertexColor`) |
| `mesh2d` без цвета | `x, y, u, v` |
| `mesh2d` с `colors=True` | `x, y, u, v, r, g, b, a` |

`mode`: `triangles` (по умолчанию), `triangle_strip`, `triangle_fan`, `lines`, `line_strip`, `line_loop`, `points`.

```python
# передняя грань куба: два треугольника, обход против часовой при взгляде снаружи
verts = [
    -0.5, -0.5, 0.5, 0, 0, 255, 90, 90, 255,
     0.5, -0.5, 0.5, 1, 0, 255, 90, 90, 255,
     0.5,  0.5, 0.5, 1, 1, 255, 90, 90, 255,
    -0.5, -0.5, 0.5, 0, 0, 255, 90, 90, 255,
     0.5,  0.5, 0.5, 1, 1, 255, 90, 90, 255,
    -0.5,  0.5, 0.5, 0, 1, 255, 90, 90, 255,
]

me = world.self()
box.mesh3d(e, verts, origin=(me.getX(), me.getY() + 2.6, me.getZ()),
           mode="triangles", colors=True, depth=True, cull=True)
```

⚠️ **`origin` — не украшение.** Координаты уезжают в видеокарту одинарной точностью: на миллионе блоков от нуля
шаг числа около семи сантиметров, и фигура дрожит. Ставь `origin` рядом с фигурой, вершины считай от него.

⚠️ **При `cull=True` порядок вершин решает всё.** Обход снаружи против часовой; перепутал — грань исчезнет.
Проверяется без игры: нормаль треугольника `(p1-p0) × (p2-p1)` должна смотреть НАРУЖУ от центра фигуры.

⚠️ **Вершины считай в тике или заранее**, а не собирай список на тысячи чисел каждый кадр в питоне: сам меш
рисуется одним draw call, но постройка списка на чистом Python съест больше, чем отрисовка.

### Грабли

⚠️ **`create` — только в теле скрипта.** Тот же текст повторно не компилируется (есть кеш по паре
«скрипт + текст»), но привычка звать `create` в отрисовке рано или поздно упрётся в лимит 32 шейдера на скрипт.

⚠️ **Цикл без выхода вешает видеодрайвер целиком** (на Windows — сброс по TDR и вылет игры).
Клиент отбивает буквальные `while (true)` и `for (;;)`, обойти это тривиально, поэтому у любого цикла
в шейдере обязан быть предел.

⚠️ **Имя `uniform` должно совпадать буква в букву.** Опечатка в `set` не даёт ошибки: значение просто
не доедет, шейдер нарисуется с нулём.

⚠️ **`fullscreen` считает каждый пиксель каждый кадр.** Много `texture(...)` и длинные циклы режут FPS вдвое.

⚠️ **Каждый шейдерный прямоугольник — отдельный draw call**, в общий батч клиента он не попадает.
Десяток панелей нормально, сотня заметна.

---

## 11. Мир и игрок

```python
world.ingame()          # bool — мир и игрок существуют
world.self()            # свой игрок (mc.player)
world.entities()        # все сущности
world.living()          # только LivingEntity
world.players()         # другие игроки (без себя)
world.nearest_player()  # ближайший игрок или None
world.target()          # текущая цель Aura
world.time()            # время мира
```

Всё, что отдаёт `world.*`, **уже обёрнуто** в `_J` — методы зовутся по named-именам, `wrap` не нужен.

Прямой доступ к Minecraft — `mc` (тоже `_J`, обёрнут):

```python
mc.player
mc.world
mc.options
mc.getSession().getUsername()      # net.minecraft.client.session.Session
mc.getCurrentFps()

p = mc.player
p.getX(), p.getY(), p.getZ()
p.getYaw(), p.setYaw(v), p.getPitch(), p.setPitch(v)
p.getHealth(), p.isOnGround()
p.getId()                          # интерфейс EntityLike — существует
p.getNameForScoreboard()           # имя строкой (getName().getString() НЕ работает!)

# клавиши игры (только с главного потока!)
mc.options.forwardKey.setPressed(True)
# доступные: forwardKey, backKey, leftKey, rightKey, jumpKey,
#            sneakKey, sprintKey, attackKey, useKey
```

Импорт классов Minecraft (named-маппинги, ремап-сейф):

```python
from net.minecraft.entity import LivingEntity      # через meta-path finder
Box = jimport("net.minecraft.util.math.Box")
```

> Перегрузка выбирается сперва по числу аргументов, а среди одинаковых по числу — по типам того, что передали.
> `Entity.getId()` (интерфейс `EntityLike`) и `Entity.getName()` (интерфейс `Nameable`) существуют — мост находит их обходом интерфейсов. Для имени бери `getNameForScoreboard()`: одна строка вместо возни с `Text`.

---

## 11.1. Newton: ходьба, полёт, копка (`newton`)

Часть клиента, которая сама ищет дорогу и ведёт персонажа. Задача одна за раз, новая отменяет предыдущую.
Ни один метод не бросает: если Newton ещё не запущен или блок не найден — вернётся `False` / `None`.

```python
# точка: три числа, [x, y, z] или сущность; дробные координаты округляются вниз
newton.goto(100, 64, -200, radius=1)     # radius почти всегда нужен
newton.goto(world.nearest_player(), radius=2)
newton.goto_xz(100, -200)                # любая высота
newton.goto_y(12)                        # только высота
newton.fly_to(1500, 120, -800)           # на элитре (нужны элитра и ракеты)
newton.goto(1500, 120, -800, elytra=True)   # то же самое

newton.mine("diamond_ore")               # id блока, minecraft: можно опустить
newton.excavate([100, 60, 200], [110, 66, 210])          # раскопать область
newton.excavate([100, 60, 200], [110, 66, 210], "stone")  # только камень
newton.fill([100, 60, 200], [110, 66, 210], "cobblestone")

newton.cancel()                          # стоп + отпустить клавиши (алиас stop())
```

Выделение области — то же, что `.newton sel` в игре:

```python
newton.select(100, 60, 200)              # угол 1
newton.select(110, 66, 210)              # угол 2
area = newton.selection()                # {"min": [x, y, z], "max": [x, y, z]} | None
newton.excavate_selection()              # или fill_selection("stone")
newton.clear_selection()
```

Состояние:

| Метод | Возвращает | Что |
|---|---|---|
| `newton.ready()` | bool | Newton запущен |
| `newton.active()` | bool | сейчас что-то выполняется |
| `newton.process()` | str \| None | `goto`, `mine <id>`, `excavate`, `fill`, `elytra` |
| `newton.status()` | str \| None | строка состояния (как `.newton status`) |
| `newton.path()` | dict \| None | `{"step": int, "steps": int, "next": [x,y,z] \| None, "goal": [x,y,z] \| None}` |
| `newton.progress()` | float | 0.0…1.0 |
| `newton.pause()` / `resume()` / `paused()` | bool | пауза задачи |
| `newton.command(line)` | bool | команда строкой: `"goto 100 64 -200"` |
| `newton.safewalk` / `newton.logging` | bool (свойства) | не падать с краёв / писать отчёт в чат |

События хода работы: `newton_started`, `newton_path`, `newton_node`, `newton_finished`, `newton_failed` (см. `script_api section=events`).

⚠️ **Грабли:**
- Новая задача отменяет старую, и отменённая шлёт `newton_failed` с причиной `отменён`. Перезапуск задачи в `newton_failed` без проверки причины = вечный круг.
- Пока задача идёт, Newton сам жмёт клавиши движения: свои `mc.options.*Key.setPressed(...)` будут с ним драться.
- `newton.path()` есть только у ходьбы: у полёта и копки маршрута по шагам нет, будет `None`.
- Цель без радиуса часто недостижима (блок в стене, под водой, на краю) — задавай `radius=1..3`.

Цепочка точек (штатный способ обойти маршрут):

```python
POINTS = [[100, 64, 200], [140, 64, 210], [180, 70, 190]]
state = {"i": 0}


def go_next():
    point = POINTS[state["i"] % len(POINTS)]
    state["i"] += 1
    newton.goto(point, radius=1)


@events.newton_finished
def on_done(event):
    go_next()


@events.newton_failed
def on_fail(event):
    if event.getReason() != "отменён":
        client.warn("Newton: " + event.getReason())
```

---

## 11.2. Свои команды чата (`command`, `commands`)

Команда скрипта работает как встроенная: попадает в `.help` и в подсказки чата, снимается вместе со скриптом.

```python
@command("hello", desc="Здоровается", aliases=["hi"])
def hello(ctx):
    ctx.msg("Привет!")


@command("tp")
def tp(ctx, x: int, y: int, z: int):      # аргументы — из СИГНАТУРЫ функции
    """Идти к координатам"""           # docstring = описание для .help
    newton.goto(x, y, z, radius=1)


@command("say")
def say(ctx, *words):                     # *words — весь остаток строки
    ctx.msg(" ".join(words))


@command("stay")
def stay(ctx, seconds: int = 10):         # значение по умолчанию = необязательный аргумент
    ctx.msg("Стою %d сек" % seconds)
```

Типы аргументов: `int`, `float`, `bool`, `str` (по умолчанию) и строковые `"player"`, `"module"`, `"block"` —
у последних трёх подсказки и проверка уже готовы. Свои подсказки:

```python
@command("mode", suggests={"value": ["fast", "slow"]})
def mode(ctx, value="fast"): ...

# динамический список: функция получает набранный кусок и возвращает варианты
@command("warp", suggests={"name": lambda partial: list(db.all().keys())})
def warp(ctx, name): ...
```

Подкоманды — декоратором `sub` у созданной команды (глубина не ограничена):

```python
@command("warps")
def warps(ctx):
    """Список точек"""
    ctx.msg(", ".join(db.all().keys()) or "пусто")


@warps.sub("add")
def warps_add(ctx, name):
    """Сохранить точку"""
    p = world.self()
    if p is not None:
        db.set(name, [p.getX(), p.getY(), p.getZ()]).save()
```

| Член | Описание |
|---|---|
| `ctx.msg/warn/error/overlay(text)` | ответ игроку |
| `ctx.name` / `ctx.args` / `ctx.get(i, default)` | имя команды и аргументы |
| `cmd.sub(name, desc=, aliases=, suggests=)` | декоратор подкоманды |
| `cmd.remove()` / `cmd.name` | снять команду, её имя |
| `commands.add(name, fn, desc=, aliases=, suggests=)` | то же, что декоратор, без него |
| `commands.remove(name \| cmd)` | снять СВОЮ команду (чужую не тронет) |
| `commands.exists(name)` / `commands.all()` | занято ли имя, все команды клиента |
| `commands.run(line)` / `commands.prefix()` | выполнить команду, текущий префикс |

⚠️ **Грабли:**
- Первый параметр функции — всегда `ctx`; функция без параметров тоже допустима, но тогда аргументов у команды нет.
- Имя (или алиас) встроенной команды занять нельзя: `install` бросит ошибку и скрипт не загрузится.
- Аргумент с пробелом игрок пишет в двойных кавычках: `.warp "мой дом"`.
- Ошибка внутри команды пишет `[Python Error]`, но скрипт НЕ выгружает — в отличие от ошибки в событии.

---

## 11.3. Уведомления, инвентарь, тема, цель, FunTime

### Уведомления (`notify`)

```python
notify.island("Готово", "success")             # строка в Dynamic Island: info | success | error
notify.success("Готово"); notify.error("Беда"); notify.info("Просто так")
notify.crosshair("Внимание", "Рядом игрок")    # плашка под прицелом
notify.item("Нашёл", "diamond", highlight="алмаз", color=theme.accent())
notify.effect("Выдали", "speed", highlight="Скорость")   # плашка со значком эффекта
notify.sound(); notify.count()
```

Каждая показанная плашка (в том числе чужая и своя) приходит событием `notification`:
`getStyle()` (island/crosshair/mini/irc), `getType()`, `getTitle()`, `getText()`.

⚠️ Своё уведомление тоже придёт в это событие — `notify` внутри обработчика без проверки зациклит клиент.

### Инвентарь (`inventory`, алиас `inv`)

Слоты как в игре: **0-8** хотбар, **9-35** рюкзак, **36-39** броня (шлем→ботинки), **40** левая рука.
Часть инвентаря словом: `"hotbar"`, `"main"`, `"armor"`, `"offhand"`, `"all"` (по умолчанию `all`).

```python
inventory.selected()                       # слот в руке
inventory.select(2)                        # взять слот (и пакетом серверу)
inventory.id(2), inventory.label(2), inventory.count(2), inventory.stack(2)

slot = inventory.find("totem_of_undying", "hotbar")   # None если нет
inventory.find_all("obsidian", "main"); inventory.has("ender_pearl"); inventory.total("ender_pearl")
inventory.empty("hotbar"); inventory.items("hotbar")  # [(слот, id, количество), ...]
inventory.hold("golden_apple")             # взять в руку, если он в хотбаре

inventory.swap(0, 1); inventory.move(9, 0); inventory.quick_move(9)
inventory.to_offhand(slot); inventory.to_armor(9, "helmet")
inventory.with_slot(8, действие)           # временная смена слота, вернётся сам
inventory.durability(0)                    # проценты, None если не ломается
inventory.enchant(0, "sharpness")          # уровень, 0 если нет
inventory.offhand_is("totem_of_undying"); inventory.container_open()
```

⚠️ Перекладывание — это клики по слотам, сервер их видит: одно действие за тик, а не пачка.

### Эффекты (`effects`, алиас `buffs`)

Баффы и дебаффы игрока. Эффект всюду называют строкой (`"speed"` или `"minecraft:speed"`),
объектом эффекта или ванильным `StatusEffectInstance`.

```python
for eff in effects.list():                 # отсортированы по id: иконки в ряд не прыгают
    client.msg("%s %s" % (eff.label, eff.time))

effects.list(hidden=True)                  # + служебные (сервер спрятал частицы и значок)
effects.good(); effects.bad()              # только полезные / только вредные
effects.has("speed"); effects.get("speed") # проверка и сам эффект (или None)
effects.level("speed")                     # уровень с единицы, 0 если нет
effects.duration("speed"); effects.seconds("speed")   # тики и секунды, бесконечный = -1
effects.time("speed")                      # "01:23"
effects.info("strength")                   # описание типа, даже если эффекта нет
effects.of(entity)                         # эффекты существа
effects.types()                            # все id, какие знает игра

len(effects); "speed" in effects; [e.id for e in effects]   # объект работает и как список
```

Свойства одного эффекта — **свойства, а не методы** (скобок нет):
`id`, `key`, `name`, `label` («Скорость II»), `level`, `amplifier`, `duration`, `seconds`, `time`,
`color`, `category` (`good`/`bad`/`neutral`), `good`, `bad`, `infinite`, `ambient`, `particles`,
`visible`, `hidden`, `active`, `atlas`, `uv`, `instance`, `raw`, метод `draw(ctx, x, y, size, color)`.

Иконка эффекта рисуется где угодно: `ctx.effect(eff, x, y, size)` в HUD и на своих экранах,
`ui.effect(eff, 12)` в меню, `render3d.effect(event, eff, pos, size=0.35)` в мире,
`notify.effect("Выдали", eff)` плашкой.

⚠️ **У чужих игроков список почти всегда пустой** — сервер эти данные не рассылает, клиент знает
только свои эффекты. Это не ошибка скрипта.

⚠️ **Эффект — снимок:** время внутри не идёт. Список берут заново там, где рисуют или считают,
а не держат в переменной между тиками.

⚠️ **Смену ловят событиями `effect_added` / `effect_removed`,** а не опросом каждый тик.

### Цвета темы (`theme`, алиас `colors`)

```python
theme.accent(); theme.text(); theme.background(); theme.second(); theme.outline(); theme.on_accent()
theme.color("separator")                   # accent|text|background|second|outline|shadow|on_accent|flat|separator
theme.readable(theme.accent())             # читаемый текст поверх своей заливки
theme.name(); theme.dark(); theme.set_accent(Color(255, 90, 90))
```

⚠️ Цвета живые: бери их при отрисовке, а не запоминай при загрузке скрипта.

### Аккаунт игрока (`profile`, алиасы `account`, `user`)

```python
profile.username      # ник аккаунта на сайте (= profile.name); "" пока ответ не пришёл
profile.uid           # номер аккаунта
profile.role          # default|user|beta|media|support|moderator|alpha|admin|owner
profile.staff         # админ, модератор или владелец
profile.admin         # только админ и владелец
profile.loaded        # ответ сайта уже пришёл
profile.has_role("admin", "owner")

profile.subscription        # строка как в клиенте: "05-05-2026" или "Навсегда"
profile.subscription_end    # секунды эпохи (как time.time()) либо None (бессрочно/неизвестно)
profile.subscription_left   # секунды до конца либо None
profile.days_left           # число, inf у бессрочной, None если неизвестно
profile.forever; profile.expired

profile.avatar              # картинка: d.image(profile.avatar, 7, 7, 30, 30, radius=15)
profile.avatar_url
profile.avatar_of("ConeTin")

profile.client; profile.version   # "Rockstar", "2.1"
profile.all()                     # всё сразу обычным dict
```

⚠️ Это СВОЙСТВА, а не методы: `profile.username`, без скобок. Профиль приезжает с сайта уже ПОСЛЕ
запуска клиента, а скрипты грузятся раньше: в теле скрипта ник обычно пустой, а роль `default`.
Проверяй `profile.loaded` и читай значения там, где они нужны, а не запоминай при загрузке.

⚠️ Это НЕ ник в Minecraft: игровое имя берут у игрока (`mc.getSession().getUsername()`).

⚠️ `days_left` у бессрочной подписки равен `inf`, а при неизвестном сроке это `None` — сравнивать
`None` с числом нельзя, сначала проверь.

### Свой список в стиле клиента (`hud.list`)

Бинды, зелья и персонал у клиента устроены одинаково: шапка со значком и строки-кейкапы. Такой же
элемент собирается из одной функции — она отдаёт строки, всё остальное (лесенка по ширине, анимации,
прижатие к своей стороне экрана) клиент берёт на себя.

```python
binds = hud.list("Мои бинды", icon="keyboard", x=8, y=40)

@binds.rows
def rows():
    return [[m.getName(), m.getKeyName()] for m in client.modules.all()
            if m.isEnabled() and m.getKey() > 0]
```

Строка это список ячеек, ячейка — текст или словарь (`text`, `icon`, `item`, `effect`, `dot`, `color`,
`background`, `fill`, `size`, `width`, `min_width`, `align`). Иконка эффекта и точка статуса дают строки
зелий и стафф-листа один в один, а строка из одних `item` — сетку слотов: инвентарь 9x3 это три строки
по девять ячеек `{"item": inventory.stack(s), "size": 18}`.

⚠️ Функция строк вызывается раз в `every` мс (по умолчанию 100), а не каждый кадр.

**Полный раздел (сигнатура, все ячейки, грабли) — `script_api section=ui`.**

### Элементы HUD клиента (`hud.elements`)

```python
hud.elements                 # список словарей: и встроенные элементы, и скриптовые
hud.info("targethud")        # один по имени (ключ, последний сегмент ключа или перевод)
```

Словарь читается и точкой, и скобками: `el.alpha` это то же самое, что `el["alpha"]`. Внутри
обычный `dict` (работают `get()`, перебор, `in`, `json.dumps`), так устроены ВСЕ словари, которые
отдаёт клиент: элемент HUD, панель меню, трек музыки, запись FunTime, `profile.all()`.

Ключи словаря: `name`, `title`, `icon`, `x`, `y`, `width`, `height`, `right`, `bottom`,
`center_x`, `center_y`, `alpha` (появление 0..1), `appear`/`visible` (её половины), `scale`,
`select` (выделение в правке), `drag`/`dragging`, `showing`, `script`.

Слои вокруг них — события `hud_render` (ПОД элементами) и `post_hud_render` (ПОВЕРХ):

```python
@events.hud_render
def under(e):
    ctx = e.getContext()
    for el in hud.elements:
        if el.alpha <= 0.02:
            continue
        w = el.width * el.scale          # элемент всплывает и масштабом тоже
        h = el.height * el.scale
        x, y = el.center_x - w / 2, el.center_y - h / 2
        ctx.drawRoundedRect(x - 4, y - 4, w + 8, h + 8, border(9),
                            Color(120, 190, 255).withAlpha(40 * el.alpha))
```

У событий есть `getContext()`, `getCount()`, `isEditing()` (открыт чат — HUD в режиме правки)
и `getTickDelta()`.

⚠️ Спрятанные элементы остаются в списке с `alpha == 0`: проверяй, иначе рисуешь вокруг пустоты.

⚠️ Координаты живые: элемент едет при перетаскивании и меняет ширину по содержимому. Читай их в
обработчике, а не запоминай при загрузке.

⚠️ У своего элемента то же состояние доступно свойствами: `el.alpha`, `el.scale`, `el.drag`,
`el.dragging`, `el.selecting` (именно `selecting` — `el.select(...)` это фабрика настройки).

### Меню клиента (`menu`)

```python
menu.opened            # меню на экране или доигрывает закрытие
menu.type              # "panel" | "modern" | None
menu.progress          # открытость 0..1 (1 — на месте, 0 — нет)
menu.open              # анимация открытия с кривой: на отскоке уходит за единицу
menu.close             # закрытие 0..1, идёт и без экрана (меню улетает в мир)
menu.closing
menu.alpha             # 1 видно, 0 спрятано клавишей скрытия
menu.scale             # масштаб кадра: 0.7 → 1 на открытии

menu.x; menu.y; menu.width; menu.height    # габарит: окно у modern, рамка всех панелей у panel
menu.panels                                # список словарей
menu.panel("combat")                       # или "window" у modern
menu.all()
```

Панель — словарь: `name`, `x`, `y`, `width`, `height`, `right`, `bottom`, `center_x`, `center_y`.
У panel панелей пять (по категории: `combat`, `movement`, `visuals`, `player`, `other`), у modern одна — `window`.

Слои вокруг меню — события `menu_render` (ПОД панелями) и `post_menu_render` (ПОВЕРХ):

```python
@events.menu_render
def under(e):
    ctx = e.getContext()
    for p in menu.panels:
        ctx.drawShadow(p.x - 8, p.y - 8, p.width + 16, p.height + 16,
                       30, border(18), Color(120, 190, 255).withAlpha(110 * menu.progress))
```

⚠️ Это свойства, скобки не нужны (`menu.progress`, а не `menu.progress()`).

⚠️ Оба события идут ВНУТРИ анимации открытия и в координатах панелей: повторять масштаб руками не надо.
Вне этих событий (например в `render_2d`) координаты те же, но масштаба нет — он в `menu.scale`.

⚠️ Панели едут каждый кадр (открытие модуля, скролл, перетаскивание окна): читай их в обработчике.
Прозрачность умножай на `menu.alpha`, иначе слой останется висеть, когда меню спрятали клавишей.

### Выбор цели (`target`)

```python
victim = target.best(players=True, range=6, sort="fov")
everyone = target.all(players=True, mobs=True, range=16, sort="distance")
target.valid(entity, players=True, range=8)
target.current(); target.living()          # цель Aura

target.add("Nick"); target.is_target("Nick"); target.list(); target.remove("Nick"); target.clear()
```

Настройки: `players`, `mobs`, `animals`, `invisibles`, `naked`, `friends`, `users`, `armor_stands`,
`exclude_teammates`, `range`, `sort` (`distance`, `health`, `fov`, `bad_armor`, `good_armor`).

⚠️ Выборка обходит все сущности мира: ищи цель в `tick`, а не каждый кадр.

### Данные FunTime (`funtime`, алиас `ft`)

```python
funtime.ready()
funtime.events(); funtime.mines(); funtime.copper_dungeons(); funtime.warden_cities()
funtime.system_info()                      # {"events": .., "mines": .., ...}

funtime.fetch_events(колбэк)               # строка JSON
funtime.fetch_players(колбэк)              # [{"name", "donate", "server_id", ...}]
funtime.fetch_bans(колбэк, {"playerName": "Nick"})
funtime.solve_captcha(base64, колбэк)      # {"solved", "text", "percent"}
```

Колбэк зовётся уже на главном потоке — внутри можно трогать `mc` и рисовать.

⚠️ `events()` схлопывает записи по названию ивента; нужны все — `fetch_events` + `json.loads`.
⚠️ Данные наполняются, пока играешь на FunTime: пустой список сразу после запуска это норма.
⚠️ `ready()` — это «данные уже собраны», а не «SDK жив»: `fetch_*` работают и при `ready() == False`,
а `system_info()` приходит только по вебсокету и вне его режима равен `None`.

Объект создают именем с большой буквы, как `Module(...)`: `Hud(...)`, `Esp(...)`, `IslandStatus(...)`,
`Storage(...)`, `Shader(...)`, `@Command(...)`. Строчные имена (`hud`, `esp`, `storage`, `shader`, `commands`) —
те же системы с методами (`hud.all()`, `esp.to_screen()`, `commands.run()`). Прежние формы `hud.add(...)`,
`esp.element(...)`, `storage.open(...)`, `shader.create(...)` тоже работают: старые скрипты не ломаются.

### Свои элементы ESP (`esp`)

Элемент живёт рядом со встроенными (свечение, боксы, неймтеги): цели отбирает клиент по галочкам меню,
скрипт только рисует. Галочки, бинды и настройки уходят в конфиг, элемент снимается вместе со скриптом.

```python
el = Esp("esp.mybox", targets=["players", "mobs"], enable=["others"])
color = ColorSetting(el, "esp.mybox.color")     # настройки как у модуля, первым аргументом элемент


@el.filter                       # необязательный отбор поверх галочек
def only_close(entity):
    return entity.distanceTo(mc.player) < 20


@el.render                       # на каждую цель: fn(entity, event)
def draw(entity, event):
    render3d.box(event, entity, color.get())


@el.render_all                   # ИЛИ все цели кадра разом: fn(entities, event)
def draw_all(entities, event):
    for entity in entities[:20]:
        render3d.marker(event, [entity.getX(), entity.getY(), entity.getZ()])


el.enable_for("local", "friends")
el.enabled(); el.remove()
esp.enabled(); esp.elements()
esp.to_screen(x, y, z)           # -> (x, y) в единицах render_2d либо None (точка за спиной)
```

Цели: `players` (виды `local`, `friends`, `rockstar_users`, `others`), `mobs`, `animals`, `items`.

⚠️ Пока выключен модуль ESP, не рисует ни один элемент — ни твой, ни встроенный.
⚠️ `render` зовёт питон на КАЖДУЮ цель каждый кадр; при десятках целей бери `render_all` (один вызов на кадр).
⚠️ Внутри рисования ничего тяжёлого: бюджет 3D примерно 150 примитивов на кадр.
⚠️ Имя элемента и имена настроек — ключи локализации, переводы объявляй через `lang`.
⚠️ Ошибка в колбэке снимает колбэки элемента (иначе она повторялась бы каждый кадр) и уходит в лог.

---

### Переводы (`lang`)

Ключ вместо готовой строки: язык подставляет клиент, при смене языка надписи меняются сами.

```python
lang.load({
    "ru_ru": {"mymod.speed": "Скорость", "mymod.speed.description": "Как быстро", "mymod.hi": "Привет, %s"},
    "en_us": {"mymod.speed": "Speed", "mymod.speed.description": "How fast", "mymod.hi": "Hi, %s"},
})
lang.add("uk_ua", {"mymod.speed": "Швидкість"})
lang.load_file("lang.json")            # или ссылка; верхний уровень json - коды языков

speed = Slider(mod, "mymod.speed")     # надпись в меню переведётся сама
client.msg(lang("mymod.hi", nick))     # своя строка с подстановкой
lang.current()                          # "ru_ru" | "en_us" | "uk_ua" | "pl_pl"
lang.has("mymod.hi")
lang.plural(5, "игрок", "игрока", "игроков")
```

Переводятся сами (клиент прогоняет их через локализацию на каждой отрисовке):
имя настройки, `<имя настройки>.description` (подсказка под ней), значения `Mode`/`Select`,
описание модуля по ключу `modules.descriptions.<имя модуля маленькими буквами, пробелы в _>`.

⚠️ **Имя модуля НЕ переводится** и переводиться не должно: по нему пишется конфиг, его ищет `.bind` и нейросеть.
⚠️ Ключ без перевода показывается как есть — так видно, чего не хватает; скрипт при этом работает.
⚠️ Строки самого клиента скрипт не переопределит: его слой ищется после клиентского. Ключи называй с префиксом.
⚠️ Языка нет — берётся `en_us`, потом `ru_ru`, потом любой заданный. Один язык в скрипте это нормально.
⚠️ Строки, переведённые один раз в переменную, обновляй по событию `language_changed` (§51).

---

### Скины и плащи (`skins`)

Подмена облика на своём экране: у Mojang скин не меняется, наружу ничего не уходит,
правила снимаются вместе со скриптом.

```python
skins.me(skin="Notch", cape="optifine:Notch")     # себе: скин по нику + плащ Optifine
skins.skin("Player123", "skins/my.png")           # чужому: файл рядом со скриптом
skins.skin(player_entity, "https://.../skin.png") # цель — и объект игрока тоже
skins.all(skin="Herobrine")                       # всем, у кого нет своего правила
skins.cape(None, False)                           # снять плащ вовсе
skins.model("Player123", "slim")                  # тонкие руки (для файла и ссылки)
skins.elytra(None, "capes/wings.png")             # текстура элитры
skins.reset("Player123"); skins.clear()           # снять правило цели / все правила скрипта
skins.targets(); skins.get("Player123")           # что сейчас подменено
```

Цель: `None`/`"self"` — сам игрок, `"all"` — все, ник или объект игрока — конкретный.
Источник: ник (Mojang, вместе с плащом и моделью), путь к png, ссылка, `"optifine:ник"`
(только плащ), текстура из `image(...)`, `None` — снять.

⚠️ Загрузка идёт в фоне: облик меняется через мгновение после вызова, а промах (нет ника,
файла, сети) уходит в лог клиента, исключения скрипту не будет.
⚠️ Скин — png 64x64 либо старый 64x32 (клиент развернёт сам).
⚠️ Свой плащ — png 64x32: рисунок в прямоугольнике (1,1) размером 10x16, изнанка в (12,1) того же
размера. Кратные размеры (128x64, 256x128) — чёткий плащ, 46x22 и 92x44 — формат Optifine, всё
остальное кладётся в левый верхний угол холста 64x32. Прозрачность не работает: слой плаща
непрозрачный, дырок не сделать. Динамическая текстура (`assets.dynamic_texture`) годится как файл —
меняешь пиксели, плащ меняется в тот же кадр.
⚠️ В `set/me/all` части облика задают именованными аргументами: `skin=`, `cape=`, `elytra=`, `model=`.

---

### Клавиши и курсор (`keys`)

Пара к событиям `key`, `char_typed`, `mouse`, `scroll`, `mouse_move` (§46-50 в `events.md`).

```python
keys.G; keys.LEFT_SHIFT; keys.F5           # код клавиши прямо через точку
keys.code("LEFT_ALT")                      # то же, но имя можно собрать; нет такой клавиши -> -1
keys.code("CTRL+G")                        # сочетание одним числом, годится для Bind.set()
keys.name(71)                              # подпись клавиши так, как её показывает клиент
keys.down("LEFT_SHIFT"); keys.down(71)     # зажата ли прямо сейчас (принимает код и имя)
keys.mouse(1)                              # зажата ли кнопка мыши: 0 ЛКМ, 1 ПКМ, 2 колесо
keys.x(); keys.y(); keys.cursor()          # курсор в единицах render_2d
keys.names()                               # все имена, которые понимает code()
```

Имена клавиш — как у GLFW: `A`, `SPACE`, `LEFT_SHIFT`, `F5`; мышь — `LMB`, `RMB`, `MMB`, `MOUSE4`.
Сочетание пишут через плюс: `CTRL+G`, `ALT+SHIFT+F`.

⚠️ Сравнивай `event.getKey()` с `keys.<ИМЯ>`, а не `getName()` со строкой: подпись зависит от языка клиента.
⚠️ Несуществующее имя через точку (`keys.ЧТОТО`) бросает `AttributeError`; `keys.code(...)` вернёт `-1`.

---

## 11.3.1. Открытый контейнер (`container`, алиас `chest`)

Чужое меню на экране: сундук, шалкер, меню сервера на предметах. Свой инвентарь по клавише E контейнером не считается.

```python
if container.open:
    print(container.title, container.size)          # заголовок и число слотов контейнера
    for item in container.items():                  # slot, id, name, count, lore
        print(item.slot, item.name, item.count)

    slot = container.find("diamond")                # ищет и по id, и по видимому имени
    if slot >= 0:
        container.shift_click(slot)                 # перенести себе
```

| Вызов | Что делает |
|---|---|
| `container.open` / `title` / `type` | открыто ли, заголовок окна, тип меню (`generic_9x3`, `hopper`) |
| `container.size` / `total` / `sync_id` | слотов у контейнера, всего (с инвентарём), идентификатор окна |
| `container.id(slot)` / `label(slot)` / `count(slot)` / `lore(slot)` | что лежит в слоте |
| `container.items(with_player=False)` | всё содержимое разом |
| `container.find(query)` / `find_all(query)` | слот и все слоты с предметом |
| `container.click(slot, button=0, mode="pick")` | клик; mode: `pick`, `shift`, `drop`, `swap`, `clone` |
| `container.right_click(slot)` / `shift_click(slot)` / `drop(slot, stack)` | частые случаи одной строкой |
| `container.close()` | закрыть меню |

⚠️ **Нумерация слотов тут своя — серверная**: сначала слоты контейнера, потом инвентарь игрока. С номерами из `inventory` (где 0 это первый слот хотбара) она НЕ совпадает.

⚠️ Клик уходит тем же пакетом, что от руки, курсор не двигается. Меню сервера отвечают не мгновенно: между кликами выжди пару тиков `Timer`, а не жми всё подряд в одном обработчике.

---

## 11.3.2. Блоки и измерение (`world`)

```python
world.block(x, y, z)                    # id блока или None (чанк не загружен)
world.block_name(x, y, z)               # имя, как видит игрок
world.block_info(x, y, z)               # словарь: id, name, air, liquid, solid, pos, state
world.is_block("chest", x, y, z)
world.is_air(x, y, z) / is_solid(...) / is_liquid(...)
world.nearest_block("chest", radius=32) # [x, y, z] или None
world.find_blocks("chest", radius=32, limit=64)
world.top(x, z)                         # высота верхнего непустого блока
world.known_block("chest")              # есть ли такой блок в игре (ловит опечатку)

world.dimension()                       # minecraft:overworld / the_nether / the_end
world.dimension_name()                  # overworld / the_nether / the_end
world.is_overworld() / is_nether() / is_end()
```

Координаты принимаются тремя числами, списком или объектом с координатами (сущность, `BlockPos`). Имя блока — `chest` или `minecraft:chest`, разницы нет.

⚠️ **Перебор растёт кубом**: радиус 16 это 35 тысяч блоков, 32 — 270 тысяч. Зови из `tick` и не каждый тик, результат держи в переменной; радиус больше 64 не принимается. В отрисовке этому не место.

⚠️ Клиент знает только загруженные чанки: за краем прогрузки блока нет, и `world.block(...)` там вернёт `None`, а поиск ничего не найдёт.

---

## 11.3.3. Чат и переподключение (`client`)

```python
client.chat("привет")            # сказать в чат ОТ ИМЕНИ ИГРОКА (уходит на сервер)
client.chat("/spawn")            # со слэша — уйдёт командой
client.command("spawn")          # то же самое, слэш не обязателен
client.reconnect(3.0)            # перезайти на тот же сервер через 3 секунды
client.disconnect()              # выйти в меню серверов
client.server()                  # адрес сервера или None
```

⚠️ Не путай с `client.msg(...)`: тот пишет строку ТОЛЬКО тебе в чат, наружу ничего не уходит.

⚠️ Пауза у `reconnect` не для красоты: сервер держит прежнюю сессию ещё пару секунд и встречает мгновенный повторный вход отказом «вы уже в игре».

---

## 11.4. Музыка (`music`)

Музыка, которая играет на компьютере: та же системная медиасессия, из которой Dynamic Island берёт название, обложку и текст. Тот же объект доступен как `client.music`.

```python
track = music.current()          # None, если ничего не играет
if track:
    client.msg(track["artist"] + " : " + track["title"])
```

| Метод | Что возвращает |
|---|---|
| `music.active()` / `music.playing()` | есть ли сессия и играет ли она сейчас |
| `music.current()` | словарь: `title`, `artist`, `owner`, `playing`, `position`, `position_ms`, `duration`, `duration_ms`, `progress`, `bpm`, `color`, `artwork`, `lyrics_synced`, `has_lyrics` |
| `music.position()` / `position_ms()` | сколько отыграно |
| `music.duration()` / `duration_ms()` | длина трека |
| `music.progress()` | доля 0..1 |
| `music.bpm()` | темп трека или 0 |
| `music.color()` / `music.artwork()` | цвет и картинка обложки или `None` |
| `music.lyrics_synced()` | есть ли текст с таймкодами |
| `music.lyrics()` | весь текст: список из `text`, `time_ms`, `cues` |
| `music.current_lyric()` / `music.lyric_at(time_ms)` | строка сейчас или на заданное время (алиасы `line_at`, `at`); плюс `index`, `progress`, `singing_progress`, `active` |
| `music.play()` / `pause()` / `toggle()` / `next()` / `previous()` / `stop()` | управление плеером, `True` если команда ушла |

У строки есть `time_ms`, `text` и `cues`; в `cues` лежат `{time_ms, char_index}` для пословной караоке-анимации. Таймкод всегда в миллисекундах. Пока текст ещё ищется, `lyrics()` вернёт пустой список; если источник отдал обычный текст без таймкодов, у строк будет `time_ms = -1`, а `lyric_at(...)` вернёт `None`. Снимок всегда снимается с одного трека целиком, поэтому переключение плеера не смешивает соседние песни.

⚠️ **Плеера может не быть вовсе**: `current()`, `color()`, `artwork()` и `current_lyric()` тогда отдают `None`, числовые методы — нули. Проверяй перед использованием, иначе скрипт выгрузится на первой же паузе.

⚠️ **Смену строки лови по `index`**, а не по тексту: одинаковые строки в припеве иначе слипнутся в одну.

⚠️ Опрашивай музыку в `tick`, а не в `render_2d` / `render_3d`: 20 раз в секунду хватает с запасом.

```python
state = {"index": -1}

@events.tick
def watch(event):
    line = music.current_lyric()
    if not line or int(line["index"]) == state["index"]:
        return
    state["index"] = int(line["index"])
    client.msg(line["text"])
```

---

## 11.5. Свои звуки (`sound`, алиас `audio`)

Свои звуковые файлы: `wav`, `mp3` и `ogg`. Не путать с событием `sound` (`@events.sound`) — то приходит, когда звук играет сама игра. Путь считается от папки скриптов, можно дать полный путь с диска или ссылку (клиент скачает файл в кеш и заиграет, когда тот приедет). Тип определяется по содержимому файла, а не по расширению.

```python
sound.play("beep.wav")                          # один голос на файл: повтор начинает заново
sound.once("hit.wav", volume=0.5)               # отдельный голос: звуки накладываются
track = sound.loop("ambient.mp3", volume=0.2)   # играет по кругу

track.volume(0.1)
track.stop()
```

| Вызов | Что делает |
|---|---|
| `sound.play(path, volume, speed, loop, category, overlap, on_end)` | проиграть с начала; один голос на файл |
| `sound.once(path, ...)` | отдельный голос, снимается сам после конца |
| `sound.loop(path, ...)` | то же, что `play(..., loop=True)` |
| `sound.load(path, ...)` | подготовить звук, не запуская |
| `sound.stop(path)` / `sound.stop()` / `sound.stop_all()` | остановить один файл или все звуки скрипта |
| `sound.playing()` | сколько звуков скрипта звучит сейчас |

Каждый вызов возвращает объект звука:

| Метод звука | Что делает |
|---|---|
| `play()` / `stop()` | запустить с начала, остановить |
| `pause()` / `resume()` / `toggle()` | пауза и продолжение с того же места |
| `volume(v)` / `speed(v)` / `loop(True)` / `category(name)` | настройки; без аргумента метод возвращает текущее значение |
| `on_end(fn)` | колбэк на естественный конец |
| `playing` / `paused` / `position` / `duration` / `looping` / `path` | свойства, читаются как поля (без скобок) |

Громкость по умолчанию считается от ползунков звука в настройках игры. Ползунок выбирается параметром `category`: `master`, `music`, `players`, `blocks`, `ambient` и остальные; `category="none"` отвязывает звук от игры совсем.

⚠️ **`sound.play` держит по одному голосу на файл.** Повторный вызов перезапускает тот же звук, и два удара подряд не наложатся. Нужно наложение — `sound.once` (он же `overlap=True`).

⚠️ **Скорость читается при старте**: линия вывода открывается сразу на нужной частоте, поэтому смена `speed()` у играющего звука доедет со следующим `play()`. Громкость, наоборот, меняется на ходу и плавно — ей удобно делать затухание прямо в `tick`.

⚠️ **Звуки глохнут вместе со скриптом.** Выгрузка и перезагрузка останавливает всё, что он завёл, в том числе зацикленную музыку.

⚠️ **Лимиты**: разом клиент тянет 24 звука (самый старый глохнет), а один скрипт не может держать больше 32 звуков — столько означает, что `sound.once` зовут из тика или отрисовки, и скрипт падает с ошибкой.

⚠️ **Звук не привязан к позиции в мире**: ни затухания по расстоянию, ни панорамы. Нужен звук от точки — считай громкость по расстоянию сам.

```python
hit = sound.load("hit.wav", volume=0.6)

@events.attack
def on_attack(event):
    hit.play()
```

---

## 12. Aura и ротации

Свой режим ротации классом:

```python
class MyRot:
    name = "My Rot"

    def rotate(self, ctx):                 # или (handler, attack_distance, walls,
        yaw, pitch = ctx.default()         #      ray_trace, move_correction, target)
        return (yaw, pitch)                # или {"yaw": ..., "pitch": ...}

    def attack(self): ...                  # опционально
    def can_attack(self): return True      # опционально
    def target_null(self): ...             # опционально
    def update(self): ...                  # опционально

aura.add(MyRot(), select=True)
```

Или без класса:

```python
@aura.rotation("Simple", select=True)
def rotate(ctx):
    return ctx.to(ctx.target)
```

API `aura`: `add(mode, select=False)`, `add_rotation(name, rotate=, attack=, can_attack=, target_null=, update=, select=)`, `rotation(name)` (декоратор), `select(name)`, `remove(name|mode)`, `has(name)`, `current()`, `target()`, свойства `enabled`, `attack_distance`, `module`.

Контекст `ctx` в `rotate`: поля `handler`, `attack_distance`, `walls`, `ray_trace`, `move_correction`, `target`, `rotations`; методы `default()`, `to(entity=None)`, `apply(yaw, pitch, **kw)`.

> ⚠️ **Ошибка внутри `rotate` отключает режим НАВСЕГДА** (до перезагрузки скрипта): флаг `errored` ставится один раз и режим больше не зовётся. Оборачивай тело `rotate` в `try/except` и всегда возвращай валидные углы.
> `ctx.target` может быть `None` — проверяй. `ctx.handler` и `aura.module` — обёртки над классами КЛИЕНТА (`moscow.rockstar.*`): мост зовёт их методы по именам как есть.
> Если `rotate` вернул **словарь**, дефолт `priority` — `TO_TARGET` (а не `normal`, как у `rotations.apply`).

`rotations` (вне Aura):

```python
rotations.current()
rotations.player()
rotations.to(entity)
rotations.to_point(x, y, z)
rotations.default(target)
rotations.gcd(from_yaw, from_pitch, to_yaw, to_pitch)
rotations.gcd_step(from_yaw, from_pitch, to_yaw, to_pitch, step)               # pitch_step — опционально
rotations.gcd_step(from_yaw, from_pitch, to_yaw, to_pitch, step, pitch_step)
rotations.vanilla_step()
rotations.idling()                                                             # камеру сейчас никто не крутит
rotations.apply(yaw, pitch, correction="silent", priority="normal",
                yaw_speed=180, pitch_speed=180, return_speed=180,
                vanilla_gcd=True, raw_gcd=False)
```

Допустимые значения (строки):

| Параметр | Значения |
|---|---|
| `correction` | `silent` (дефолт), `none` / `off`, `direct`, `strict`, `smooth`, `change_look`, `targeted` |
| `priority` | `normal` (дефолт), `low`, `target`, `use_item`, `override`, `max` |

---

## 13. Хранилище, таймер, вектор

```python
db = Storage("myscript")   # scripts/storage/myscript.json
db.set("kills", 10).save()
db.get("kills", 0)
db["kills"] = 5
db.all()
db.remove("k")
db.clear()
db.load()

t = Timer()
if t.finished(500):             # прошло >= 500 мс
    t.reset()
t.elapsed()                     # мс

vec.add(a, b)
vec.sub(a, b)
vec.scale(a, s)
vec.dot(a, b)
vec.length(a)
vec.distance(a, b)
vec.normalize(a)
vec.lerp(a, b, t)
vec.clamp(v, lo, hi)
```

---

## 14. Потоки, сеть, библиотеки

**Правило №1: с чужого потока НЕЛЬЗЯ трогать `mc`, модули, HUD.**
Тяжёлую работу (сеть, CV, боты) выносим в поток, результат передаём через `queue.Queue` и разбираем в `@events.tick` (главный поток).

```python
import threading, queue, builtins

actions = queue.Queue()

def worker(stop):
    while not stop.is_set():
        ...                       # сеть / вычисления
        actions.put_nowait("do")

@events.tick
def tick(e):
    while True:
        try:
            cmd = actions.get_nowait()
        except queue.Empty:
            break
        client.msg(cmd)           # безопасно: главный поток

# при reload гасим прошлый поток
_prev = getattr(builtins, "_my_stop", None)
if _prev:
    _prev()
_stop = threading.Event()
builtins._my_stop = _stop.set
threading.Thread(target=worker, args=(_stop,), daemon=True).start()
```

Важно: состояние, которым обмениваются потоки, держи в **чистых Python-типах** (float/str/dict), а не в Java-объектах.

**Библиотеки:** `.py install requests` (pip во встроенный runtime), затем обычный `import requests`. Стандартная библиотека Python доступна вся, кроме запрещённого списка ниже.

---

## 14.1. Чего скриптам нельзя

Скрипт работает **внутри процесса игры**, поэтому доступ к памяти процесса и к запуску чужого кода закрыт: иначе скриптом снимался бы дамп клиента, а купленный на маркете скрипт мог бы делать что угодно на машине покупателя. Запрет ловится на месте, скрипт падает с понятным текстом.

| Закрыто | Что именно |
| --- | --- |
| FFI | `ctypes`, `_ctypes`, `cffi`, `_cffi_backend`, `pymem` |
| Запуск процессов | `subprocess.Popen`, `os.system`, `os.startfile`, `os.exec*`, `os.spawn*`, `os.kill` и `_winapi` (`CreateProcess`, `OpenProcess`, `TerminateProcess`). Сами модули `subprocess` и `multiprocessing` импортируются как раньше — закрыт именно запуск |
| Сторонние нативки | `.pyd`/`.dll` грузятся только из встроенного рантайма — свой файл рядом со скриптом не подключить, и записать что-то в папку рантайма скрипт тоже не может. `os.add_dll_directory` принимает только пути внутри рантайма |
| `torch` | В игре не импортируется. Он стоит в рантайме ради обучения нейро-ауры (оно идёт отдельным процессом), а `torch.ops.load_library` грузит в процесс игры любую dll. Для математики есть `numpy` — он работает |
| Реестр Windows | Запись: `winreg.CreateKey`, `SetValue`, `DeleteKey`, `DeleteValue`, `SaveKey`, `LoadKey`, `ConnectRegistry`. Чтение разрешено |
| Классы JVM | `sun.*`, `jdk.*`, `com.sun.*`, `java.lang.reflect.*`, `java.lang.invoke.*`, `java.lang.foreign.*`, `java.security.*`, `javax.script.*`, `org.lwjgl.system.*`, `io.netty.util.internal.*`, `jep.*`, а поимённо — `Runtime`, `ProcessBuilder`, `Class`, `ClassLoader`, `Thread`. У `System` закрыты только `load`, `loadLibrary`, `exit`, `setSecurityManager` — остальное (`currentTimeMillis`, `nanoTime`, `getProperty`, `out`) работает через `jimport("java.lang.System")`, но не через питоновский `from java.lang import System` |
| `import` java-пакетов | Работает как раньше для `java.*`, `javax.*`, `org.joml`, `org.lwjgl`, `com.mojang`, `net.fabricmc` (`from java.util import ArrayList`), но закрытые классы из таблицы не найдутся. Классы игры (`net.minecraft.*`) по-прежнему берут через `jimport(...)`: только он знает обфусцированные имена |

Тексты ошибок: `скриптам запрещено: ...` (питон) и `класс ... закрыт для скриптов` (мост в JVM).

Всё остальное на месте: стандартная библиотека (включая `asyncio`, `socket`, `winreg` на чтение), потоки, сеть (`requests`), `numpy`, pip-зависимости, `jimport` до классов игры и клиента.

---

## 15. Публикация на маркете

Скрипт можно продавать. Купленный скрипт приходит покупателю **marshalled-байткодом в памяти** — исходник на диск не пишется (защита кода продавца). Зависимости (pip), указанные при публикации, ставятся автоматически.
