# UI: HUD, Dynamic Island, экраны, ui-билдер, 2D-рисование

## 0. Грабли, из-за которых UI молча не работает

| Грабля | Правильно |
|---|---|
| `IslandStatus(...)` не появляется на экране | добавь `.selected(True)` — свежесозданный статус не выбран, и Dynamic Island его не рисует |
| `ui.switch` / `ui.toggle` не переключает | сеттер получает **новое значение**: `lambda v: ps.boolSet(v)` (лямбда без параметра ломается молча) |
| `ui.toggle_c` не переключает | второй колбэк — это **клик БЕЗ аргументов**: `lambda: ps.boolToggle()` |
| `on_click` на `ui.text` / `ui.image` / `ui.swatch` не срабатывает | эти виджеты `interactive(false)`; оборачивай: `with ui.row(cursor="hand", on_click=fn): ui.text(...)` (или добавь `interactive=True`) |
| `on_click_pos` получает не то | сигнатура — `fn(x, y, button)`, `button` — **строка**: `left` / `right` / `middle` |
| анимация входа игнорируется | `enter=` и `enter_slide=` пишут в одно и то же поле — победит последний kwarg. Используй что-то одно |
| `raw_screen("Title", 400, 300)` рисует не в окне 400×300 | title и размеры **игнорируются**: холст = весь экран, координаты абсолютные |

---

## 1. HUD-элементы

Три режима: **render** (рисуешь сам, императивно), **layout** (дерево виджетов ui-билдера) и
**список** (готовые строки в стиле клиентских кейбиндов, зелий и стафф-листа).

### Создание

```python
el = Hud("MyHud", width=100, height=20, x=8, y=8)
```

Полная сигнатура:

```python
Hud(name, icon="hud/player", width=80, height=20, x=8, y=8,
        showing=True, render=None, visible_when=None, layout=None)  # -> _HudElement
```

Прочее API `hud`: `hud.find(name)`, `hud.remove(name | element)`, `hud.all()`, `hud.mine()`.

### `_HudElement`

- Свойства (чтение+запись): `x`, `y`, `width`, `height`, `showing`. Только чтение: `name`, `raw`.
- Методы: `pos(x, y)`, `size(w, h)`, `show()`, `hide()`, `remove()`.
- `render(fn)` — `fn(d)` или `fn(d, element)`.
- `layout(fn)` — `fn(ui)`, дерево виджетов.
- `rows(fn)` — режим списка: `fn()` или `fn(element)` возвращает строки (см. ниже).
- Настройка списка: `title(text)`, `header(on)`, `uniform(on)`, `sort(on)`, `hide_empty(on)`, `every(ms)`, `gap(px)`.
- `signature(fn)` — функция, возвращающая строку. Меняется строка → layout пересобирается.
- `visible_when(fn)` / `show_when(fn)` — показывать только когда `fn()` истинно.
- Настройки прямо на элементе (появятся в HUD-редакторе по ПКМ): `el.checkbox("X")`, `el.slider("X")`, `el.mode("X")`, `el.select("X")`, `el.button("X")`, `el.range("X")`, `el.color("X")`, `el.bind("X")`, `el.text("X")`, `el.time("X")`, `el.gradient("X")`, `el.position("X")`, `el.bezier("X")`, `el.blocks("X")`, `el.info("X")`.

### Режим render

```python
el = Hud("MyHud", width=110, height=18, x=8, y=8)

@el.render
def draw(d):                                       # координаты ОТНОСИТЕЛЬНЫЕ
    d.rounded_rect(0, 0, d.width, d.height, radius=6, color=Color(9, 9, 11, 204))
    d.text("Rockstar", 6, 5, size=7, color=Color(207, 215, 251))
```

Контекст рисования `d` (координаты относительно элемента):

- Свойства: `d.x`, `d.y`, `d.width` / `d.w`, `d.height` / `d.h`, `d.alpha`, `d.drag`, `d.mouse_x`, `d.mouse_y`, `d.delta`.
- `d.font(weight="medium", size=8)`
- `d.size(w, h)` — изменить размер элемента (например, подогнать по ширине текста)
- `d.rect(x, y, w, h, color)` — `w`/`h` по умолчанию = размер элемента
- `d.rounded_rect(x, y, w, h, radius=6, color)`
- `d.border(x, y, w, h, radius=6, thickness=1, color)`
- `d.shadow(x, y, w, h, radius=6, softness=12, color)`
- `d.client_rect(x=0, y=0, width=None, height=None, alpha=None, drag=None, squircle=3, radius=None, outline=False)` — фон в стиле клиента. Все аргументы опциональны: `d.client_rect()` рисует подложку размером с элемент, `alpha`/`drag` по умолчанию берутся из `d.alpha` / `d.drag` (анимации показа и перетаскивания работают сами)
- `d.text(value, x, y, size=7, weight="medium", color, font, outline=None, outline_width=1, outline_steps=0)` — `outline` это цвет обводки вокруг букв, `outline_width` её ширина в пикселях (до 8). Обводку берут непрозрачной: у полупрозрачной копии складываются и край выходит плотнее. `outline_steps` — сколько копий строки рисовать по кругу (`0` = посчитать по толщине); каждая копия стоит как ещё одна отрисовка строки
- `d.centered_text(...)`, `d.right_text(...)` — те же аргументы, включая обводку
- `d.icon(name, x, y, size=8, color)`
- `d.item(stack, x, y, size=1)`
- `d.effect(effect, x, y, size=10, color)` — значок эффекта: объект из `effects.*` или имя (`"speed"`)
- `d.image(texture, x, y, w, h, radius=0, color)` (алиас `d.texture`) — ассет из `assets.image(...)`, обложка трека, аватарка из `profile.avatar`
- `d.raw()` — полный контекст рисования, те же методы, что в `render_2d`

Рисовать вокруг меню клиента: события `menu_render` (слой под панелями) и `post_menu_render` (слой поверх), координаты панелей — в глобале `menu` (см. `script_api section=api`, раздел «Меню клиента»).

Вокруг элементов HUD — события `hud_render` и `post_hud_render`, а координаты и анимации всех элементов клиента (включая чужие) — в `hud.elements` (см. `script_api section=api`, раздел «Элементы HUD клиента»).

Все методы возвращают `d` — можно цепочкой.

### Режим layout (+ signature)

Layout строится один раз и переиспользуется. Если состав/порядок зависят от настроек — задай `signature`, и при изменении строки-подписи дерево пересоберётся. Текст делай **реактивным** (передавай функцию, а не строку) — он обновляется каждый кадр без пересборки.

```python
import time

FG  = Color(207, 215, 251)
BG  = Color(9, 9, 11, 204)
DIV = Color(255, 255, 255, 20)

def _fps():
    try:
        return "%d fps" % int(mc.getCurrentFps())
    except Exception:
        return "0 fps"

ELEMENTS = [
    ("Brand", lambda: "Rockstar"),
    ("Time",  lambda: time.strftime("%H:%M")),
    ("FPS",   _fps),
]
PROV = {label: fn for label, fn in ELEMENTS}

el = Hud("Bar", width=116, height=17, x=8, y=8)

sel = el.select("Elements").draggable().min(0)     # порядок перетаскивается в HUD-редакторе
for label, _ in ELEMENTS:
    sel.add(label)
sel.select("Brand")
sel.select("Time")

def build(ui):
    with ui.row(align="center", gap=0, radius=6, bg=BG):
        first = True
        for label in list(sel.getValues()):
            if not sel.isSelected(label):
                continue
            if not first:
                ui.column(width=1, height=7, bg=DIV)      # разделитель
            with ui.row(align="center", gap=4, pad=(5, 7)):
                ui.text(PROV[label], size=7, weight="medium", color=FG)   # реактивный текст
            first = False

def sig():
    return "|".join(list(sel.getValues())) + "#" + ",".join(sorted(sel.getSelected()))

el.layout(build)
el.signature(sig)
```

---

### Режим списка (`rows`) — как кейбинды, зелья и стафф-лист

Клиентские списки (бинды, зелья, персонал) устроены одинаково: шапка со значком, под ней строки-кейкапы,
лесенка по ширине, появление и уход строк с анимацией, прижатие к своей стороне экрана. Всё это даёт
`hud.list(...)`: скрипт отдаёт только строки.

```python
binds = hud.list("Мои бинды", icon="keyboard", x=8, y=40)

@binds.rows
def rows():
    return [[m.getName(), m.getKeyName()] for m in client.modules.all()
            if m.isEnabled() and m.getKey() > 0]
```

Полная сигнатура:

```python
hud.list(name, icon="hud/player", x=8, y=8, showing=True, rows=None, title=None,
         header=True, uniform=False, sort=True, hide_empty=True, every=100, gap=1, visible_when=None)
```

**Строка** это список ячеек (или словарь `{"key": ..., "cells": [...]}` — ключ держит за строкой её
анимацию, когда текст меняется). **Ячейка** это текст либо словарь:

| Ключ | Что делает |
|---|---|
| `text` | текст кейкапа |
| `icon` | значок клиента в квадрате 10x10 |
| `item` | слот с предметом: стек из `inventory.stack(slot)`, id строкой (`"totem_of_undying"`) или `None` для пустого слота. Количество и полоска прочности рисуются сами, выключаются `"count": False` и `"bar": False` |
| `size` | сторона ячейки-квадрата (значок, эффект, слот). По умолчанию 10; для слота инвентаря берут 18, тогда предмет внутри выходит ровно 16, как в игре |
| `effect` | иконка эффекта: объект из `effects.*` или имя (`"speed"`) |
| `dot` | точка статуса: цвет или `True` (зелёная) |
| `color` | цвет текста, значка или иконки |
| `background` | цвет подложки ячейки |
| `fill` | эта ячейка забирает свободную ширину |
| `width` (`w`), `min_width` (`min`) | фиксированная и минимальная ширина |
| `align` | `start`, `center`, `end` — выравнивание текста |

Без явного `fill` растягивается **первая текстовая** ячейка: поэтому `["Aura", "R"]` сразу выглядит
биндом, а `[{"effect": e}, name, time]` — строкой зелья.

```python
pots = hud.list("Зелья", icon="hud/potion", x=8, y=80)

@pots.rows
def rows():
    return [[{"effect": e}, e.label, e.time] for e in effects.list()]
```

Строка из одних слотов даёт **сетку**: инвентарь 9x3 это три строки по девять ячеек.

```python
inv = hud.list("Инвентарь", icon="hud/player", x=8, y=160, sort=False)

@inv.rows
def rows():
    return [{"key": "main%d" % start,
             "cells": [{"item": inventory.stack(s), "size": 18} for s in range(start, start + 9)]}
            for start in (9, 18, 27)]
```

Пустой слот (`"item": None`) рисуется пустой ячейкой и держит место в сетке, поэтому ряды не разъезжаются.

```python
staff = hud.list("Персонал", icon="hud/staff", x=8, y=120, uniform=True)

@staff.rows
def rows():
    return [{"key": p.getNameForScoreboard(),
             "cells": ["Модер", p.getNameForScoreboard(), {"dot": Color(70, 210, 120)}]}
            for p in world.players()]
```

⚠️ **Функция строк вызывается не каждый кадр, а раз в `every` мс (по умолчанию 100).** Так и задумано:
вызов питона на каждый кадр просаживает FPS. Тексты внутри строк обновляются на каждом опросе, дерево
при этом не пересобирается — оно меняется только когда меняется состав строк.

⚠️ **Пустой список прячется сам** (кроме открытого чата — иначе элемент нечем подвинуть). Нужен всегда
видимый — `hide_empty(False)`.

⚠️ Настройки списка (`sort`, `uniform`, `title`, `header`, `hide_empty`) можно звать прямо из функции строк:
повтор с тем же значением ничего не делает, дерево от этого не пересобирается.

⚠️ Ключ строки по умолчанию это текст её первой текстовой ячейки. Если текст меняется каждую секунду
(время, счётчик), задавай `key` явно, иначе строка будет считаться новой и переигрывать появление.

## 2. Dynamic Island

Статус создают глобальным конструктором `IslandStatus(...)` (как `Module(...)`); сам `island` — менеджер (`find`/`all`/`mine`/`remove`).

> ⚠️ **`IslandStatus(...)` без `.selected(True)` НЕ рисуется.** `DynamicIsland` показывает только выбранные статусы (`visibleStatuses()` фильтрует по `isSelected()`), а свежесозданный статус не выбран. Это тихий баг: код без ошибок, на экране пусто.

Новый статус встаёт **в начало списка**, над встроенными: остров рисует один статус за раз, самый верхний из подходящих, и снизу статус скрипта был бы почти всегда перекрыт. Порядок игрок меняет перетаскиванием в настройках HUD, и его выбор запоминается между перезагрузками скрипта.

```python
st = IslandStatus("MyStatus", width=48, height=15, radius=7, expandable=False)
st.selected(True)                                  # ОБЯЗАТЕЛЬНО, иначе статуса не будет видно

@st.render
def draw(d):
    d.centered_text("Hi", d.w / 2, 4)

st.visible_when(lambda: world.ingame())
st.click(lambda mx, my, btn: client.msg("клик"))   # btn — int (код кнопки мыши)
st.color(lambda: Color(255, 0, 0))
st.measure(lambda: st.size(60, 15))
```

Сигнатура: `IslandStatus(name, width=48, height=15, radius=7, expandable=False, render=, visible_when=, measure=, click=, color=)`.
Менеджер: `island.find(name)`, `island.remove(...)`, `island.all()`, `island.mine()`.

Свойства статуса: `x`, `y`, `width`/`w`, `height`/`h`, `alpha`, `extended`, `expanding`, `name`, `raw`.
Методы: `size(w, h[, radius])`, `radius(r)`, `expandable(b)`, **`selected(b)`**, `render(fn)`, `measure(fn)`, `click(fn)`, `color(fn | Color)`, `visible_when(fn)`, `remove()`.

Колбэки принимают разное число аргументов (клиент подстраивается под сигнатуру):
`render(d)` или `render(d, status)`; `click()` / `click(status)` / `click(mx, my, btn)` / `click(mx, my, btn, status)`; `measure()` / `measure(status)`; `visible_when()` / `visible_when(status)`.

Контекст рисования `d` — тот же, что у HUD (относительные координаты).

---

## 3. Экран с лейаутом — `@screen`

```python
mod  = Module("Menu", "Other")
flag = Checkbox(mod, "Flag")

@screen("Моё меню", 400, 300)
def menu(ui):
    with ui.column(gap=8, pad=12, bg=Color(20, 20, 24), fill=True):
        ui.text("Заголовок", size=10, weight="bold", color=Color(255, 255, 255))
        with ui.row(gap=6, align="center"):
            ui.button("Кнопка", on_click=lambda: client.msg("клик"))
            ui.toggle("Флаг", lambda: flag.get(), lambda v: flag.set(v))   # сеттер ПРИНИМАЕТ значение

Button(mod, "Открыть").action(lambda: menu.open())
```

Функция-строитель вызывается при открытии экрана. Методы объекта: `menu.open()`, `menu.close()`, свойство `menu.opened`.

### Контейнеры (context manager)

`ui.column(**style)`, `ui.row(**style)` — используются через `with`.

### Виджеты

| Виджет | Сигнатура | Кликабелен по умолчанию |
|---|---|---|
| `ui.text` | `(value_or_callable, size=0, weight="medium", color=None, **style)` — callable → реактивный текст | ❌ `interactive(false)` |
| `ui.button` | `(label, **style)` — клик через `on_click=` | ✅ |
| `ui.toggle` | `(label, get, set, **style)` — **`set` принимает новое значение** | ✅ |
| `ui.switch` | `(get, set, **style)` — **`set` принимает новое значение** | ✅ |
| `ui.slider` | `(label, lo, hi, value=0.0, on_change=None, step=0.0, **style)` — `on_change(v)` | ✅ |
| `ui.slider_bar` | `(get, set, lo, hi, step=0.0, **style)` — **`set(v)` принимает значение** | ✅ |
| `ui.toggle_c` | `(get, on_click, on=None, off=None, knob=None, **style)` — **`on_click` БЕЗ аргументов** | ✅ |
| `ui.slider_c` | `(get, set, lo, hi, step=0, track=, fill=, ring=, inner=, thumb_radius=, thumb_border=, track_height=, **style)` — **`set(v)`** | ✅ |
| `ui.text_input` | `(get, set, placeholder="", bg=None, color=None, size=0, weight="regular", **style)` — **`set(v)`**; `size`/`weight` — кегль и начертание текста, высота поля растёт вместе с кеглем | ✅ |
| `ui.swatch` | `(get, **style)` — кружок цвета | ❌ `interactive(false)` |
| `ui.setting` | `(py_setting, **style)` — клиентский рендер настройки (фолбэк для редких типов) | ✅ |
| `ui.icon` | `(name, size=10, color=None, **style)` | ✅ кликабельна |
| `ui.image` | `(texture, size=10, color=None, radius=0, **style)` | ❌ `interactive(false)` |
| `ui.effect` | `(effect, size=12, color=None, **style)` — эффект объектом, именем или функцией (тогда иконка реактивна) | ❌ `interactive(false)` |
| `ui.space` | `(px=4)` | — |
| `ui.divider` | `(**style)` | — |
| `ui.color` | `(name)` → цвет темы: `accent`, `text`, `background`/`bg`, `second`, `outline`, `white` | — |

### ⚠️ Сеттеры: три разных контракта

```python
ps = mod.settings()[0]

# 1) switch / toggle — колбэк получает НОВОЕ ЗНАЧЕНИЕ (внутри: set.call(not get()))
ui.switch(lambda: ps.boolGet(), lambda v: ps.boolSet(v))
ui.toggle("Флаг", lambda: ps.boolGet(), lambda v: ps.boolSet(v))
# ui.switch(lambda: ps.boolGet(), lambda: ps.boolToggle())   # НЕВЕРНО: лямбда без параметра — молча не работает

# 2) toggle_c — второй колбэк это КЛИК, аргументов НЕТ
ui.toggle_c(lambda: ps.boolGet(), lambda: ps.boolToggle(), on=ACCENT, off=CTRL, knob=WHITE)

# 3) slider_bar / slider_c / text_input — сеттер принимает значение
ui.slider_bar(lambda: ps.numGet(), lambda v: ps.numSet(v), ps.numMin(), ps.numMax(), ps.numStep())
```

### ⚠️ Клик на неинтерактивных виджетах

`ui.text`, `ui.image`, `ui.swatch` создаются с `interactive(false)`, и `on_click=` этот флаг **не поднимает** — клик просто не придёт. Рабочая идиома (её используют штатные меню клиента):

```python
with ui.row(cursor="hand", radius=5, pad=(3, 5), on_click=lambda: client.msg("клик")):
    ui.text("Нажми меня", size=6)
```

Альтернатива — явно `interactive=True` на самом виджете: `ui.text("X", interactive=True, on_click=fn)`.

### ⚠️ `toggle_c` / `slider_c`: цвета статичные, размер — стилем

Цветовые аргументы этих двух виджетов принимаются как готовый `Color`, **колбэк туда не передать** (в отличие от `bg=`/`color=` у любого узла). Цвет читается один раз, когда строится дерево, — при смене темы на лету контрол не перекрасится, только после переоткрытия меню.

Размер у `toggle_c` зашит (38×22), но перебивается обычным стилем, потому что стили применяются после конструирования виджета:

```python
ui.toggle_c(lambda: ps.boolGet(), lambda: ps.boolToggle(), on=ACCENT, size=(30, 16))
```

Форму поменять нельзя: тоггл — капсула с круглым бегунком, слайдер — полоса с круглой ручкой. Нужен контрол другой формы (квадратная галочка, сегменты, радиокнопки, `-`/`+`) — собирай из `ui.row` + `ui.text`/`ui.icon` + `on_click`, значение читай/пиши через `PySetting`.

> `Select` из скриптового API снять галочку не умеет: `select(name)` только включает. Единственный способ переключить — `selToggle(i)` у настройки из `mod.settings()`; он же соблюдает `min()`.

### Стили — kwargs, доступные любому узлу

| Группа | Ключи |
|---|---|
| размер | `width`, `height`, `size=(w, h)`, `min_size`, `max_size` |
| отступы | `gap`, `pad` / `padding` (число или `(v, h)`) |
| форма | `radius`, `radius_bottom`, `squircle`, `border=(width, color)` |
| заливка | `color` / `bg` (ColorRGBA **или callable**) |
| размытие | `blur` (число > 0 включает размытие, сила одна на весь клиент — свои панели он рисует с 45; парой `(число, ColorRGBA)` — с подкраской), `glass` (True или число 0..1 — готовое стекло клиента: размытие + тон темы) |
| растяжение | `fill`, `fill_width`, `fill_height` |
| раскладка | `align` (`start\|center\|end\|stretch`), `justify` (`start\|center\|end\|between\|around\|evenly`), `direction` (`up\|down\|left\|right`), `columns`, `wrap` |
| скролл/слои | `scroll`, `stack`, `scrollbar` (`auto\|always\|never`), `sticky`, `collapse` |
| поведение | `on_click` (`fn()`), `on_click_pos` (**`fn(x, y, button)`**, button — строка `left`/`right`/`middle`), `visible_when`, `interactive` (bool — поднять флаг кликабельности у `text`/`image`/`swatch`), `draggable` (True или `x\|y\|none\|all`), `cursor` (`hand`/`pointer`, `text`/`ibeam`, `crosshair`, `hresize`/`horizontal`, `vresize`/`vertical`, `block`/`notallowed`, `resize`/`resizeall`) |
| анимации | `enter` / `exit` (`none\|fade\|vanish\|fade_slide\|up\|down\|left\|right\|pop\|fade_pop`), `enter_slide` / `exit_slide` (сдвиг в пикселях), `motion` (`fast\|smooth\|signal\|spring\|spring_snap\|soft`), `stagger`, `fade` |
| прочее | `center` |

> ⚠️ `enter=` и `enter_slide=` пишут в одно поле (`el.enter(...)`) — сработает тот, что окажется последним в kwargs. То же у `exit` / `exit_slide`. Задавай что-то одно.

> ⚠️ **`blur` размывает то, что видно ПОЗАДИ узла** (мир под интерфейсом), а не соседние узлы меню: источник — снимок кадра, сделанный до отрисовки интерфейса. Число только включает размытие, силу им не крутят. Форму размытие берёт у самого узла, поэтому `radius` и `squircle` ставь на тот же узел — заливка и рамка лягут ровно поверх. Каждый размытый узел стоит отдельного прохода отрисовки: пара панелей на меню нормально, полсотни размытых строк списка съедят кадры.

```python
@screen("Glass", 240, 140)
def menu(ui):
    with ui.column(fill=True, gap=8, pad=12, radius=12, blur=45,
                   bg=Color(16, 17, 20, 150)):          # своя заливка поверх размытия
        ui.text("Стекло", size=9, color=ui.color("text"))

        with ui.row(fill_width=True, pad=(6, 10), radius=8, glass=True):
            ui.text("тон темы клиента", size=7, color=ui.color("text"))
```

```python
with ui.row(on_click_pos=lambda x, y, button: client.msg("%s @ %d,%d" % (button, int(x), int(y))),
            cursor="hand", width=60, height=20):
    ui.text("ПКМ/ЛКМ", size=6)
```

### Реактивность и замыкания

Любой стиль, принимающий значение, обычно принимает и функцию — она вызывается каждый кадр:

```python
ui.text(lambda: "FPS: %d" % int(mc.getCurrentFps()), size=7, color=WHITE)

with ui.row(bg=lambda: ACCENT if state["cat"] == c else NONE,
            on_click=lambda c=c: state.__setitem__("cat", c),
            cursor="hand", radius=5, pad=(3, 5)):
    ui.text(c.capitalize(), size=5)
```

**В циклах обязательно связывай переменные дефолтными аргументами** (`lambda i=i, ps=ps: ...`), иначе все лямбды схватят последнее значение итерации.

### Слои (stack) и скролл

`stack=True` у контейнера кладёт детей слоями друг на друга (последний — сверху). Типичный приём: нижний слой — скроллящийся контент на всю высоту, верхний — прижатая к низу панель, которая перекрывает контент.

```python
with ui.column(stack=True, radius=12, bg=WIN):
    with ui.column(fill=True, scroll=True, scrollbar="never", pad=(9, 10)):
        ...                                     # контент
        ui.row(fill_width=True, height=NAV_H + 8)   # запас снизу под панель
    with ui.column(fill=True, justify="end"):
        with ui.row(fill_width=True, height=NAV_H, bg=NAVBG, radius_bottom=12):
            ...                                 # нав-бар поверх
```

---

## 4. Экран без лейаута — `@raw_screen` (immediate mode)

> ⚠️ **`raw_screen(title, width, height)`: title и размеры ИГНОРИРУЮТСЯ.** Внутри создаётся пустой `PyScreen()`, холст — весь экран игры. Рамку окна рисуй сам, отталкиваясь от `d.width` / `d.height` (это размер ЭКРАНА).

```python
@raw_screen()                  # аргументы можно не передавать — они всё равно не используются
def render(d):                 # d — АБСОЛЮТНЫЕ координаты; d.width / d.height — размер ЭКРАНА
    w, h = 400, 300
    x = (d.width - w) / 2      # окно центрируем руками
    y = (d.height - h) / 2
    d.rounded_rect(x, y, w, h, radius=10, color=Color(12, 13, 15))
    d.text("Hi", x + 12, y + 12, size=8, color=Color(255, 255, 255))

@render.on_click
def click(mx, my, btn):        # btn — СТРОКА: left / right / middle. Есть и @render.on_release
    client.msg("клик %s %d,%d" % (btn, int(mx), int(my)))

render.open()                  # render.close(), render.opened
```

Методы `d` те же, что в HUD-контексте, но координаты абсолютные: `rect`, `rounded_rect`, `border`, `client_rect`, `text`, `centered_text`, `right_text` (с той же обводкой: `outline`, `outline_width`, `outline_steps`), `icon`, `image`, `font`, `raw`.
Отличие от HUD-контекста: у `raw`-варианта `d.client_rect(x, y, w, h, alpha=1.0, drag=0.0, squircle=3)` — координаты и размер обязательны.

---

## 5. 2D-рисование напрямую (`render_2d` / `pre_render_2d`)

```python
@events.render_2d
def draw(e):
    ctx = e.getContext()
    ctx.drawRoundedRect(10, 10, 120, 22, border(6), Color(0, 0, 0, 180))
    ctx.drawText(font("medium", 8), "Rockstar", 16, 16, Color(255, 255, 255))
```

Методы `CustomDrawContext`:

| Метод | Сигнатура |
|---|---|
| `drawRect` | `(x, y, w, h, color)` |
| `drawRoundedRect` | `(x, y, w, h, border, color)` |
| `drawRoundedBorder` | `(x, y, w, h, thickness, border, color)` |
| `drawSquircle` | `(x, y, w, h, squirt, border, color)` |
| `drawSquircleBorder` | `(x, y, w, h, thickness, squirt, border, color)` |
| `drawShadow` | `(x, y, w, h, softness, border, color)` |
| `drawBlurredRect` | `(x, y, w, h, blurRadius, border, color)` / `(x, y, w, h, blur, squirt, border, color)` |
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
| `drawHead` | `(entity, x, y, size, border, color)` |
| `drawTexture` | `(identifier, x, y, w, h[, color])` |
| `drawRoundedTexture` | `(identifier, x, y, w, h, border[, color])` |
| `drawEntity` | `(x1, y1, x2, y2, size, f, mouseX, mouseY, entity)` |
| `drawArc` | `(x, y, size, thickness, startAngle, endAngle, color)` |
| `drawCircleProgress` | `(cx, cy, radius, thickness, progress, color)` |
| `drawLine` | `(Vec2f from, Vec2f to, color)` |
| `pushMatrix()` / `popMatrix()` | — |

> Перегрузки Java резолвятся **по числу аргументов**: у `drawBlurredRect` вариант с 7 и с 8 аргументами — разные методы.

---

## 6. Цвета, шрифты, скругления, ассеты

```python
Color(255, 0, 0)              # r, g, b (0..255)
Color(255, 0, 0, 128)         # + альфа
Color.from_hex("#ff0000")     # или "#ff0000aa"
Color.from_int(0xFFFF0000)
Color.from_hsb(0.5, 1.0, 1.0)
ColorRGBA.WHITE / BLACK / RED / GREEN / BLUE / YELLOW

c.withAlpha(120)
c.mulAlpha(0.5)
c.mix(other, 0.5)
c.toHex()

font("medium", 8)                       # веса: noto, bold, medium, regular, semibold, roundbold
client.font_width("medium", 8, "text")
client.font_height("medium", 8)

border(6)                               # все углы
border4(10, 0, 10, 0)                   # tl, tr, br, bl

assets.image("assets/logo.png")         # путь относительно scripts/; кэшируется, перечитывается при изменении
assets.resource("textures/gui/x.png")
assets.ttf("Inter", "assets/Inter.ttf", 9)                          # свой шрифт из ttf/otf

client.cursor("hand")                   # arrow/default, hand/pointer, text/ibeam, crosshair,
                                        # hresize, vresize, block, resize
client.menu_opened()
```

Картинки грузи защищённо — если файла нет, `assets.image` бросит исключение и уронит скрипт:

```python
def img(path):
    try:
        return assets.image(path)
    except Exception:
        return None
```
