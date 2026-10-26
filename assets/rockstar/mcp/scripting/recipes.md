# Рецепты — готовые скрипты

Каждый рецепт — целый файл, который можно положить в `<gameDir>/scripts/` и загрузить (`.py reload`, затем `.py load <имя>`). Все API-вызовы реальные и проверены по коду клиента.

Рецепты уже соблюдают ключевые правила — сохраняй их при правках:
объекты Minecraft из событий готовы к работе (`wrap` не нужен) • порядок `Slider`: `.min().max().step().set()` • проверка на `None` после `client.find` • `island.selected(True)` • сеттер `ui.switch`/`ui.toggle` принимает значение, клик `ui.toggle_c` — нет • `on_click` только на контейнерах • `render3d.marker`/`line` — точки, `box`/`ring` — сущности.

---

## 1. HUD с координатами и FPS (режим render)

```python
# coords_hud.py — компактный HUD-бар: координаты, FPS, ник.

BG   = Color(9, 9, 11, 204)
FG   = Color(207, 215, 251)
GRAY = Color(255, 255, 255, 140)

el = Hud("Coords", width=120, height=28, x=8, y=8)

show_fps = el.checkbox("Show FPS").set(True)     # настройка появится в HUD-редакторе (ПКМ)


def _coords():
    p = world.self()
    if p is None:
        return "0, 0, 0"
    return "%d, %d, %d" % (int(p.getX()), int(p.getY()), int(p.getZ()))


def _fps():
    try:
        return "%d fps" % int(mc.getCurrentFps())
    except Exception:
        return "0 fps"


@el.render
def draw(d):
    d.rounded_rect(0, 0, d.width, d.height, radius=6, color=BG)
    d.text(_coords(), 7, 5, size=8, weight="semibold", color=FG)
    if show_fps.get():
        d.text(_fps(), 7, 16, size=6, color=GRAY)
    else:
        d.text("Rockstar", 7, 16, size=6, color=GRAY)


el.visible_when(lambda: world.ingame())
```

---

## 2. ESP игроков через `render_3d`

```python
# player_esp.py — боксы вокруг игроков, маркер над головой и кольцо под целью Aura.

mod = Module("PlayerESP", "Visuals")
mod.setDesc("Подсветка игроков боксами")

filled  = Checkbox(mod, "Filled")
rings   = Checkbox(mod, "Target ring").set(True)
marks   = Checkbox(mod, "Head marker")
col     = ColorSetting(mod, "Color").color(86, 124, 252, 255).alpha(True)
# ПОРЯДОК: min -> max -> step -> set (set клампится по ТЕКУЩЕМУ шагу!)
max_dst = Slider(mod, "Distance").min(5).max(150).step(5).set(60).suffix(" м")


@events.render_3d
def draw(event):
    if not mod.isEnabled() or not world.ingame():
        return

    me = world.self()
    color = col.get()
    limit = max_dst.get()

    for p in world.players():
        try:
            dx = p.getX() - me.getX()
            dy = p.getY() - me.getY()
            dz = p.getZ() - me.getZ()
            if (dx * dx + dy * dy + dz * dz) ** 0.5 > limit:
                continue
        except Exception:
            continue

        # box / filled_box / ring / target принимают СУЩНОСТЬ
        if filled.get():
            render3d.filled_box(event, p, color)
        else:
            render3d.box(event, p, color)

        # marker и line принимают ТОЛЬКО точку [x, y, z] — сущность сюда передавать нельзя
        if marks.get():
            render3d.marker(event, [p.getX(), p.getY() + 2.2, p.getZ()], 0.15, color)

    if rings.get():
        target = world.target()       # может быть None
        if target is not None:
            render3d.ring(event, target, radius=0.9, color=color)
```

---

## 3. Уведомление об атаке (событие + всплывашка через `render_2d`)

```python
# attack_toast.py — при атаке показываем плашку с именем цели, она гаснет через 2 секунды.

mod = Module("AttackToast", "Combat")
mod.setDesc("Показывает, кого мы ударили")

DURATION = 2000                        # мс
BG    = Color(9, 9, 11, 210)
WHITE = Color(255, 255, 255)
ACC   = Color(86, 124, 252)

timer = Timer()
last = {"name": None}


@events.attack
def on_attack(event):
    if not mod.isEnabled():
        return
    # getEntity() отдаёт Entity, а НЕ LivingEntity: здоровья у лодки или рамки нет
    ent = event.getEntity()
    try:
        # getNameForScoreboard(), а НЕ getName().getString() — Text.getString() не резолвится в релизе
        last["name"] = str(ent.getNameForScoreboard())
    except Exception:
        last["name"] = "Entity"
    timer.reset()


@events.render_2d
def draw(event):
    if not mod.isEnabled() or last["name"] is None:
        return
    if timer.finished(DURATION):
        last["name"] = None
        return

    ctx = event.getContext()
    text = "Атака: " + last["name"]
    f = font("medium", 8)
    w = client.font_width("medium", 8, text) + 16

    ctx.drawRoundedRect(10, 10, w, 22, border(6), BG)
    ctx.drawRect(10, 10, 2, 22, ACC)
    ctx.drawText(f, text, 18, 17, WHITE)
```

---

## 4. Меню на ui-билдере (реальные модули клиента, свои виджеты)

```python
# mini_menu.py — компактное меню: категории слева, карточки модулей справа.
# Настройки чужих модулей рисуем своими виджетами через интроспекцию PySetting.

CATS = ["COMBAT", "MOVEMENT", "VISUALS", "PLAYER", "OTHER"]
state = {"cat": None}

WIN    = Color(12, 13, 15)
CARD   = Color(16, 17, 20)
CTRL   = Color(26, 27, 32)
ACCENT = Color(86, 124, 252)
WHITE  = Color(255, 255, 255)
LABEL  = Color(255, 255, 255, 178)
GRAY   = Color(150, 150, 160)
NONE   = Color(0, 0, 0, 0)


def _fmt(ps):
    v = float(ps.numGet())
    return str(int(v)) if v == int(v) else ("%.2f" % v).rstrip("0").rstrip(".")


def _cat(m):
    # getCategory(): у своего модуля — как передали ("Combat"), у чужого — enum ("COMBAT")
    return str(m.getCategory()).upper()


@screen("Mini", 420, 280)
def menu(ui):
    mods = client.modules.all()                    # список всех модулей; find(name) отдаёт один или None
    present = [c for c in CATS if any(_cat(m) == c for m in mods)]
    if state["cat"] not in present:
        state["cat"] = present[0] if present else None

    def setc(c):
        return lambda: state.__setitem__("cat", c)

    def row_label(name):
        ui.text(name, size=6, color=LABEL, fill_width=True, fade=True)

    def render_setting(ps):
        t = ps.type()
        nm = ps.name()
        if t == "boolean":
            with ui.row(align="center", fill_width=True, height=10):
                row_label(nm)
                # toggle_c: ВТОРОЙ колбэк — клик БЕЗ аргументов (в отличие от ui.switch/ui.toggle)
                ui.toggle_c(lambda ps=ps: ps.boolGet(), lambda ps=ps: ps.boolToggle(),
                            on=ACCENT, off=CTRL, knob=WHITE, size=(15, 8))
        elif t == "slider":
            with ui.row(align="center", gap=5, fill_width=True, height=10):
                row_label(nm)
                # slider_c: сеттер ПРИНИМАЕТ значение
                ui.slider_c(lambda ps=ps: ps.numGet(), lambda v, ps=ps: ps.numSet(v),
                            ps.numMin(), ps.numMax(), ps.numStep(),
                            track=CTRL, fill=ACCENT, ring=NONE, inner=WHITE,
                            width=44, height=8, track_height=2, thumb_radius=2.5, thumb_border=0)
                with ui.row(width=18, height=8, radius=2, bg=CTRL, align="center", justify="center"):
                    ui.text(lambda ps=ps: _fmt(ps), size=5, color=WHITE)
        elif t == "mode":
            with ui.row(align="center", fill_width=True, height=10):
                row_label(nm)
                # клик вешаем на РЯД: у ui.text interactive=false, on_click на нём не сработает
                with ui.row(radius=2, pad=(1.5, 3), bg=CTRL, cursor="hand",
                            on_click=lambda ps=ps: ps.modeSelect(
                                (int(ps.modeIndex()) + 1) % len(list(ps.optionLabels())))):
                    for i, lab in enumerate(list(ps.optionLabels())):
                        ui.text(lab, size=5, color=WHITE,
                                visible_when=lambda i=i, ps=ps: ps.modeIndex() == i)
        elif t == "button":
            with ui.row(fill_width=True, height=12, cursor="hand", radius=3, bg=CTRL,
                        align="center", justify="center", on_click=lambda ps=ps: ps.click()):
                ui.text(nm, size=6, color=WHITE)
        elif t == "color":
            with ui.row(align="center", fill_width=True, height=10):
                row_label(nm)
                ui.swatch(lambda ps=ps: ps.colorGet(), width=7, height=7, radius=2)
        else:
            ui.setting(ps)                   # фолбэк на клиентский рендер (bind, text, ...)

    def module_card(mod):
        with ui.column(gap=5, radius=8, pad=(7, 7), bg=CARD, fill_width=True):
            with ui.row(align="center", fill_width=True, height=10):
                ui.text(mod.getName(), size=7, weight="semibold", color=WHITE,
                        fill_width=True, fade=True)
                ui.toggle_c(lambda mod=mod: mod.isEnabled(), lambda mod=mod: mod.toggle(),
                            on=ACCENT, off=CTRL, knob=WHITE, size=(15, 8))
            for ps in list(mod.settings()):
                if ps.visible():
                    render_setting(ps)

    with ui.row(gap=0, radius=10, bg=WIN, fill=True):
        # ---- сайдбар категорий ----
        with ui.column(gap=3, pad=(10, 8), width=90):
            ui.text("Rockstar", size=8, weight="bold", color=ACCENT)
            ui.space(4)
            for c in present:
                # on_click — на ui.row, а не на ui.text; переменную цикла связываем дефолтным аргументом
                with ui.row(cursor="hand", radius=5, pad=(4, 6), fill_width=True,
                            on_click=setc(c),
                            bg=lambda c=c: ACCENT if state["cat"] == c else NONE):
                    ui.text(c.capitalize(), size=6, weight="medium",
                            color=lambda c=c: WHITE if state["cat"] == c else GRAY)

        # ---- список модулей выбранной категории ----
        with ui.column(fill=True, scroll=True, scrollbar="auto", pad=(10, 10), gap=8):
            for c in present:
                with ui.column(fill_width=True, gap=8, enter="fade",
                               visible_when=lambda c=c: state["cat"] == c):
                    for mod in [m for m in mods if _cat(m) == c]:
                        module_card(mod)


m = Module("Mini Menu", "Other")
Button(m, "Открыть меню").action(lambda: menu.open())
```

---

## 5. Фоновый поток + очередь + корректное гашение при reload

Базовый каркас для всего тяжёлого (сеть, бот, CV). **С чужого потока `mc`, модули и HUD трогать нельзя** — только класть задачи в очередь.

```python
# worker.py — фоновый поток опрашивает HTTP, главный поток показывает результат.
# Зависимости: .py install requests

import threading
import queue
import builtins
import time

import requests

URL = "https://example.com/status"

mod = Module("Worker", "Other")
mod.setDesc("Фоновый опрос HTTP")

results = queue.Queue()                    # поток -> главный поток
shared = {"last": "—"}                     # только чистые Python-типы!


def loop(stop):
    while not stop.is_set():
        try:
            r = requests.get(URL, timeout=10)
            results.put_nowait("HTTP %d" % r.status_code)
        except Exception as e:
            results.put_nowait("Ошибка: %s" % e)
        # прерываемое ожидание вместо time.sleep(30)
        stop.wait(30)


@events.tick
def on_tick(event):
    while True:                            # разгребаем очередь на главном потоке
        try:
            msg = results.get_nowait()
        except queue.Empty:
            break
        shared["last"] = msg
        if mod.isEnabled():
            client.msg("[worker] " + msg)


@events.render_2d
def draw(event):
    if not mod.isEnabled():
        return
    event.getContext().drawText(font("medium", 7), shared["last"], 6, 6, Color(255, 255, 255))


# --- перезапуск: гасим прошлый поток при reload (иначе потоки размножатся) ---
_prev_stop = getattr(builtins, "_worker_stop", None)
if _prev_stop is not None:
    try:
        _prev_stop()
    except Exception:
        pass

_stop = threading.Event()
builtins._worker_stop = _stop.set

threading.Thread(target=loop, args=(_stop,), daemon=True, name="worker").start()

print("[worker] запущен")
```

Тот же приём — для Telegram-бота (asyncio-цикл на своём потоке) и для CV с вебкамеры: поток кладёт команды в `queue.Queue`, а `@events.tick` их применяет на главном потоке:

```python
def apply(cmd):
    if cmd == "forward":
        mc.options.forwardKey.setPressed(True)
    elif cmd == "aura":
        aura = client.find("Aura")            # find вернёт None, если модуля нет
        if aura is None:
            client.warn("Модуль Aura не найден")
        else:
            aura.toggle()
```

---

## 6. Хранилище (`storage`) — счётчик между сессиями

```python
# stats.py — считаем атаки, сохраняем в scripts/storage/stats.json

mod = Module("Stats", "Other")
mod.setDesc("Счётчик атак")

db = Storage("stats")                 # scripts/storage/stats.json
total = {"n": int(db.get("attacks", 0))}

save_timer = Timer()

reset = Button(mod, "Сбросить")
reset.action(lambda: (total.__setitem__("n", 0), db.set("attacks", 0).save(), client.msg("Сброшено")))


@events.attack
def on_attack(event):
    total["n"] += 1


@events.tick
def on_tick(event):
    if save_timer.finished(5000):          # пишем на диск не чаще раза в 5 секунд
        save_timer.reset()
        if int(db.get("attacks", 0)) != total["n"]:
            db.set("attacks", total["n"]).save()


@events.render_2d
def draw(event):
    if not mod.isEnabled():
        return
    ctx = event.getContext()
    ctx.drawText(font("medium", 8), "Атак: %d" % total["n"], 6, 40, Color(255, 255, 255))
```

---

## 7. Свой режим ротации Aura

Режим регистрируется в модуле Aura и выбирается в его настройке ротации.

### Вариант «класс» — полный контроль

> ⚠️ **Ошибка внутри `rotate` отключает режим НАВСЕГДА** (до перезагрузки скрипта): клиент ставит флаг `errored` и больше режим не зовёт. Поэтому всё тело — в `try/except`, и всегда возвращаем валидные углы.

```python
# smooth_rot.py — плавная ротация к цели с ограничением скорости поворота.

rot_mod = Module("Smooth Rotation", "Combat")
rot_mod.setDesc("Настройки моего режима ротации Aura")
# ПОРЯДОК: min -> max -> step -> set
max_step = Slider(rot_mod, "Max step").min(1).max(180).step(1).set(40).suffix("°")


def _wrap180(angle):
    return (angle + 180.0) % 360.0 - 180.0


class SmoothRotation:
    name = "Smooth Py"

    def rotate(self, ctx):
        yaw, pitch = ctx.default()             # куда «хочет» смотреть Aura
        try:
            p = world.self()                   # уже обёрнут (world.*) — wrap не нужен
            if p is None:
                return (yaw, pitch)

            cur_yaw = float(p.getYaw())
            cur_pitch = float(p.getPitch())
            step = float(max_step.get())

            d_yaw = max(-step, min(step, _wrap180(float(yaw) - cur_yaw)))
            d_pitch = max(-step, min(step, float(pitch) - cur_pitch))

            new_pitch = max(-90.0, min(90.0, cur_pitch + d_pitch))
            return (cur_yaw + d_yaw, new_pitch)
        except Exception as e:
            print("[smooth_rot] ошибка:", e)    # НЕ даём исключению уйти наружу
            return (yaw, pitch)

    def can_attack(self):
        return True


aura.add(SmoothRotation(), select=True)        # select=True — сразу выбрать этот режим
```

### Вариант «декоратор» — минимальный

```python
@aura.rotation("Simple Py", select=True)
def rotate(ctx):
    if ctx.target is None:                     # цели может не быть — проверяй
        return ctx.default()
    return ctx.to(ctx.target)                  # смотреть прямо на цель
```

Полезное: `aura.enabled` (вкл ли модуль), `aura.target()`, `aura.attack_distance`, `aura.current()`, `aura.has(name)`, `aura.select(name)`, `aura.remove(name)`.
`aura.module` и `ctx.handler` — обёртки над классами КЛИЕНТА (`moscow.rockstar.*`): мост зовёт их методы по именам как есть.

Ротации вне Aura — объект `rotations`:

```python
yaw, pitch = rotations.to(world.target())      # углы на цель Aura
rotations.apply(yaw, pitch, correction="silent", priority="normal")
# correction: silent (деф) | none/off | direct | strict | smooth | change_look | targeted
# priority:   normal (деф) | low | target | use_item | override | max
```

---

## 8. Горячая клавиша: бинд модуля или событие `key`

Бинд модуля лучше, когда действие одно: клавишу выбирает игрок, а не скрипт.

```python
# hotkey.py — бинд модуля работает как горячая клавиша: ловим module_toggled.

mod = Module("QuickAction", "Other")
mod.setDesc("Забинди меня в клиенте — по нажатию выполнится действие")


@events.module_toggled
def on_toggle(event):
    if event.getModule().getName() != "QuickAction":
        return
    if event.isState():
        client.msg("Действие выполнено")
        mod.setEnabled(False)          # сразу гасим — получается «кнопка», а не тумблер
```

Событие `key` нужно, когда клавиш несколько, важны сочетания или отпускание.

```python
# keybinds.py — свои сочетания на событии key.

mod = Module("KeyActions", "Other")
sneaking = {"on": False}


@events.key
def on_key(event):
    # пока открыт чат, игрок просто печатает
    if not mod.isEnabled() or event.isScreenOpen():
        return

    # сравниваем КОД, а не getName(): подпись клавиши зависит от языка клиента
    if event.isPress() and event.getKey() == keys.G:
        client.msg("G")
    elif event.isPress() and event.getKey() == keys.H and event.isShift():
        client.msg("Shift+H")

    # отпускание тоже приходит сюда
    if event.getKey() == keys.LEFT_ALT:
        sneaking["on"] = event.isPress()
```

Альтернатива без клавиши вовсе — кнопка в настройках модуля:

```python
Button(mod, "Выполнить").action(lambda: client.msg("Действие выполнено"))
```

---

## 9. Статус в Dynamic Island (не забыть `selected(True)`)

```python
# island_ping.py — статус с пингом/FPS в Dynamic Island.

WHITE = Color(255, 255, 255)
ACC   = Color(86, 124, 252)

st = IslandStatus("FPS", width=44, height=15, radius=7)
st.selected(True)                      # БЕЗ ЭТОГО СТАТУС НЕ РИСУЕТСЯ (он не выбран)


def _fps():
    try:
        return int(mc.getCurrentFps())
    except Exception:
        return 0


@st.render
def draw(d):                           # координаты ОТНОСИТЕЛЬНЫЕ
    d.centered_text("%d fps" % _fps(), d.w / 2, 4, size=6, color=WHITE)


st.color(lambda: ACC if _fps() >= 60 else Color(220, 80, 80))
st.visible_when(lambda: world.ingame())
st.click(lambda mx, my, btn: client.msg("FPS: %d" % _fps()))
```

---

## 10. Патруль по точкам через Newton (цепочка задач)

```python
# patrol.py — бот обходит точки по кругу: Newton ведёт, скрипт только выдаёт цели.

mod = Module("Patrol", "Player")
mod.setDesc("Обход точек через Newton")

POINTS = [[100, 64, 200], [140, 64, 210], [180, 70, 190]]
state = {"i": 0, "fails": 0}


def go_next():
    if not mod.isEnabled() or not newton.ready():
        return
    point = POINTS[state["i"] % len(POINTS)]
    state["i"] += 1
    # radius почти всегда нужен: ровно на один блок дойти удаётся не везде
    newton.goto(point, radius=1)


@events.newton_started
def on_start(event):
    client.overlay("Newton: " + event.getProcess())


@events.newton_node
def on_node(event):
    client.overlay("шаг %d/%d" % (event.getStep(), event.getSteps()))


@events.newton_finished
def on_done(event):
    state["fails"] = 0
    go_next()                          # Newton уже свободен, задачу ставить можно


@events.newton_failed
def on_fail(event):
    # ВАЖНО: отмена — тоже срыв. Без этой проверки свой же cancel() зациклит патруль.
    if event.getReason() == "отменён":
        return

    state["fails"] += 1
    if state["fails"] > 3:
        client.warn("Патруль встал: " + event.getReason())
        mod.setEnabled(False)
        return
    newton.goto(POINTS[(state["i"] - 1) % len(POINTS)], radius=state["fails"] + 1)


@events.module_toggled
def on_toggle(event):
    if event.getModule().getName() != "Patrol":
        return
    if event.isState():
        state["fails"] = 0
        go_next()
    else:
        newton.cancel()                # свои клавиши Newton отпустит сам
```

Прогресс задачи на HUD:

```python
el = Hud("Newton", icon="hud/player", width=110, height=22)


@el.render
def draw(d):
    d.size(110, 22)
    d.client_rect()

    if not newton.active():
        d.text("idle", 8, 7, size=7)
        return

    path = newton.path()               # None у полёта и копки: маршрута по шагам нет
    text = newton.process() or "?"
    if path is not None:
        text = "%s %d/%d" % (text, path["step"], path["steps"])

    d.text(text, 8, 7, size=7)
    d.rect(0, 20, 110 * newton.progress(), 2, Color(120, 200, 255))
```

---

## 11. Своя команда чата с подкомандами и подсказками

```python
# warps.py — .warps, .warps add <имя>, .warps del <имя>, .warp <имя>

db = Storage("warps")


def points():
    return list(db.all().keys())


@command("warps", aliases=["точки"])
def warps(ctx):
    """Список сохранённых точек"""     # первая строка docstring уходит в .help
    names = points()
    ctx.msg("Точки: " + (", ".join(names) if names else "пусто"))


@warps.sub("add")
def warps_add(ctx, name):
    """Сохранить текущую позицию"""
    p = world.self()
    if p is None:
        ctx.error("Ты не в игре")
        return
    db.set(name, [p.getX(), p.getY(), p.getZ()]).save()
    ctx.msg("Точка '%s' сохранена" % name)


@warps.sub("del", aliases=["remove"], suggests={"name": lambda partial: points()})
def warps_del(ctx, name):
    """Удалить точку"""
    if db.get(name) is None:
        ctx.error("Точки '%s' нет" % name)
        return
    db.remove(name).save()
    ctx.msg("Удалено")


@command("warp", suggests={"name": lambda partial: points()})
def warp(ctx, name):
    """Идти к сохранённой точке"""
    point = db.get(name)
    if point is None:
        ctx.error("Точки '%s' нет" % name)
        return
    newton.goto(point, radius=1)
    ctx.msg("Иду к '%s'" % name)
```

Аргументы с типами и проверкой:

```python
@command("modtoggle")
def modtoggle(ctx, name: "module"):       # "module" проверит, что такой модуль есть,
    """Переключить модуль клиента"""   # и подскажет имена при вводе
    mod = client.find(name)
    if mod is None:
        return
    mod.toggle()
    ctx.msg("%s: %s" % (name, "вкл" if mod.isEnabled() else "выкл"))


@command("dig")
def dig(ctx, block: "block", radius: int = 32):
    """Копать блоки этого типа"""
    ctx.msg("Копаю %s в радиусе %d" % (block, radius))
    newton.mine(block)
```

---

## 12. Автототем на утилитах инвентаря + уведомление

```python
# autototem.py — держит тотем в левой руке, сообщает плашкой.

mod = Module("AutoTotem", "Player")
mod.setDesc("Тотем в левую руку при низком хп")

health = Slider(mod, "Health").min(1).max(20).step(1).set(11)
timer = Timer()


@events.tick
def on_tick(event):
    if not mod.isEnabled() or not world.ingame():
        return
    if float(mc.player.getHealth()) > float(health.get()):
        return
    if inventory.offhand_is("totem_of_undying"):
        return
    # клики по слотам сервер видит: не чаще пары раз в секунду
    if not timer.finished(400):
        return

    slot = inventory.find("totem_of_undying")
    if slot is None:
        notify.error("Тотемов нет")
        return

    timer.reset()
    inventory.to_offhand(slot)
    notify.success("Тотем в руке (%d осталось)" % inventory.total("totem_of_undying"))
```

## 13. ESP цели правилами клиента + цвета темы

```python
# targetesp.py — подсвечивает того, кого выбрал бы клиент.

mod = Module("TargetESP", "Visuals")
mod.setDesc("Подсветка цели, выбранной правилами клиента")

reach = Slider(mod, "Range").min(2).max(12).step(0.5).set(6)
sort = Mode(mod, "Sort").add("distance").add("fov").add("health")

state = {"victim": None}


@events.tick
def on_tick(event):
    # цель считаем РАЗ В ТИК: выборка обходит все сущности мира
    if not mod.isEnabled() or not world.ingame():
        state["victim"] = None
        return
    state["victim"] = target.best(players=True, invisibles=True,
                                  range=float(reach.get()), sort=sort.get())


@events.render_3d
def draw3d(event):
    victim = state["victim"]
    if victim is None:
        return
    # цвет берём из темы прямо при отрисовке: игрок может сменить акцент в любой момент
    render3d.box(event, victim, theme.accent())
    render3d.ring(event, victim, radius=0.9, color=theme.accent())
```

## 14. Слежение за ивентами FunTime

```python
# ftwatch.py — плашка, когда стартует нужный ивент.

mod = Module("EventWatch", "Other")
timer = Timer()
seen = set()
WANTED = ["Метеорит", "Аномалия"]


@events.tick
def on_tick(event):
    if not mod.isEnabled() or not funtime.ready():
        return
    if not timer.finished(5000):      # данные всё равно обновляются не чаще
        return
    timer.reset()

    for item in funtime.events():
        name = item.get("name") or ""
        key = "%s:%s" % (name, item.get("server_id"))
        if key in seen or item.get("status") != "active":
            continue
        if not any(word.lower() in name.lower() for word in WANTED):
            continue

        seen.add(key)
        notify.success("%s: %s%s" % (name, item.get("server_type"), item.get("server_id")))
        notify.sound()


@events.world_change
def on_world(event):
    seen.clear()
```
---

## 15. Своя кнопка на экране: клик и перетаскивание мышью

```python
# panel.py — панель поверх экрана: ловит клик, тащится мышью, гасит клик для игры.

mod = Module("ClickPanel", "Other")

panel = {"x": 20.0, "y": 60.0, "w": 96.0, "h": 18.0}
drag = {"on": False}
count = 0


def inside(x, y):
    return (panel["x"] <= x <= panel["x"] + panel["w"]
            and panel["y"] <= y <= panel["y"] + panel["h"])


@events.mouse
def on_mouse(event):
    global count
    if not mod.isEnabled():
        return

    if event.isRelease():
        drag["on"] = False
        return
    if not event.isPress() or not inside(event.getX(), event.getY()):
        return

    if event.isRight():
        drag["on"] = True              # правой тащим
    else:
        count += 1                     # левой считаем нажатия
    event.cancel()                     # клик забрали себе: по игре он не пройдёт


@events.mouse_move
def on_move(event):
    # тут только сдвиг: событие приходит на каждое движение мыши
    if drag["on"]:
        panel["x"] += event.getDx()
        panel["y"] += event.getDy()


@events.render_2d
def draw(event):
    if not mod.isEnabled():
        return

    ctx = event.getContext()
    ctx.drawRoundedRect(panel["x"], panel["y"], panel["w"], panel["h"], border(4), theme.accent())
    ctx.drawText(font("medium", 7), "нажатий: %d" % count,
                 panel["x"] + 8, panel["y"] + 6, theme.on_accent())
```

⚠️ `cancel()` тут обязателен: без него левый клик по панели ещё и ударит в игре.
⚠️ Отменять клик стоит только при попадании в панель, иначе игрок вообще не сможет играть.

## 16. Свой шейдер: панель на HUD, кольцо у цели, эффект по кадру

```python
# Три способа применить свой GLSL: рект на HUD, квад в мире, полноэкранный проход.
# Шапку шейдера (версия, fragColor, встроенные переменные, roundedBoxSDF/sdfAA) дописывает клиент.

mod = Module("ShaderDemo", "Visuals")

s_speed = Slider(mod, "Скорость").min(0.1).max(4).step(0.1).set(1.0)
c_tint = ColorSetting(mod, "Цвет").color(90, 180, 255).alpha(True)
b_post = Checkbox(mod, "Эффект по миру").set(True)
b_ring = Checkbox(mod, "Кольцо под целью").set(True)

PANEL = """
uniform float Speed;

void main() {
    vec2 center = Size * 0.5;
    float dist = roundedBoxSDF(center - FragCoord * Size, center - 1.0, vec4(8.0));
    float shape = 1.0 - smoothstep(1.0 - sdfAA(dist, 1.0), 1.0, dist);

    float t = Time * Speed;
    float wave = sin(FragCoord.x * 8.0 + t) + sin(FragCoord.y * 5.0 - t * 0.8);

    fragColor = vec4(Color.rgb * (0.6 + 0.2 * wave), shape * Color.a);
}
"""

RING = """
uniform float Speed;

void main() {
    vec2 p = FragCoord * 2.0 - 1.0;
    float r = length(p);
    float line = smoothstep(0.06, 0.0, abs(r - 0.72 - sin(Time * Speed * 2.0) * 0.05));

    fragColor = vec4(Color.rgb, line * (1.0 - smoothstep(0.95, 1.0, r)) * Color.a);
}
"""

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

# компилируется здесь, один раз на загрузку скрипта
panel = Shader("demo_panel", PANEL)
ring = Shader("demo_ring", RING)
post = Shader("demo_post", POST)


el = Hud("ShaderDemo", icon="hud/keybinds", width=150, height=44, x=8, y=180)
el.visible_when(lambda: mod.isEnabled())


@el.render
def draw(d):
    panel.set("Speed", s_speed.get())
    panel.color(c_tint.get().mulAlpha(d.alpha))
    d.shader(panel)                      # во весь элемент; координаты от его угла
    d.text("свой шейдер", 8, 8, size=7, weight="bold")


@events.render_3d
def world_pass(event):
    if not mod.isEnabled() or not world.ingame():
        return

    if b_ring.get():
        victim = target.current()
        if victim is not None:
            p = victim.getPos()
            ring.set("Speed", s_speed.get())
            ring.color(c_tint.get())
            # depth=True: кольцо прячется за блоками, как обычная геометрия
            ring.quad3d(event, (p.x, p.y + 0.02, p.z), 2.4, mode="ground", additive=True, depth=True)

    # полноэкранный проход последним: он забирает уже отрисованный кадр целиком
    if b_post.get():
        post.set("Warp", 1.0)
        post.fullscreen(event)
```

⚠️ `Shader(...)` только в теле скрипта: в отрисовке он упрётся в лимит 32 шейдера на скрипт.
⚠️ Имя `uniform` в GLSL и в `set` должно совпадать буква в букву, иначе значение молча не доедет.
⚠️ У любого цикла в GLSL обязан быть предел: вечный цикл вешает видеодрайвер и роняет игру.


## 17. Водяные шары, которые сливаются и искажают мир (raymarching в `fullscreen`)

Тела считаются прямо в шейдере как поля расстояний (SDF), сливаются мягким объединением, а картинка
за ними берётся из уже отрисованного кадра. Так делают воду, ртуть, силовые поля, порталы.

```python
import math
import time

mod = Module("WaterBlobs", "Visuals")

s_count = Slider(mod, "Сколько шаров").min(1).max(8).step(1).set(5)
s_smooth = Slider(mod, "Слипание").min(0.05).max(2).step(0.05).set(0.7)
s_quality = Slider(mod, "Качество").min(16).max(96).step(8).set(56)

WATER = """
uniform vec4 Blobs[8];      // xyz ОТНОСИТЕЛЬНО КАМЕРЫ, w это радиус
uniform float Count;
uniform float Smooth;
uniform float Steps;
uniform vec3 Tint;

float smoothUnion(float a, float b, float k) {
    float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}

float map(vec3 p) {
    float d = length(p - Blobs[0].xyz) - Blobs[0].w;
    for (int i = 1; i < 8; i++) {
        if (float(i) >= Count) break;
        d = smoothUnion(d, length(p - Blobs[i].xyz) - Blobs[i].w, Smooth);
    }
    return d;
}

void main() {
    vec2 uv = FragCoord;
    vec3 background = texture(Sampler0, uv).rgb;
    vec2 ndc = uv * 2.0 - 1.0;

    // луч из камеры через пиксель
    vec4 farPoint = InvViewProj * vec4(ndc, 1.0, 1.0);
    vec3 dir = normalize(farPoint.xyz / farPoint.w);

    // и дистанция до мира в этом пикселе: дальше неё шар не рисуем
    float sceneDepth = texture(Sampler1, uv).r;
    vec4 scenePoint = InvViewProj * vec4(ndc, sceneDepth * 2.0 - 1.0, 1.0);
    float sceneDist = length(scenePoint.xyz / scenePoint.w);

    float travelled = 0.0;
    float hit = -1.0;
    for (int i = 0; i < 96; i++) {
        if (float(i) >= Steps) break;
        float dist = map(dir * travelled);
        if (dist < 0.012) { hit = travelled; break; }
        travelled += max(dist, 0.02);
        if (travelled > 48.0 || travelled > sceneDist) break;
    }

    if (hit < 0.0) { fragColor = vec4(background, 1.0); return; }

    vec3 point = dir * hit;
    vec2 e = vec2(0.015, 0.0);
    vec3 normal = normalize(vec3(
        map(point + e.xyy) - map(point - e.xyy),
        map(point + e.yxy) - map(point - e.yxy),
        map(point + e.yyx) - map(point - e.yyx)
    ));

    // преломление в экранных координатах: смещаем выборку фона по нормали
    vec3 refracted = texture(Sampler0, clamp(uv + normal.xy * 0.05, vec2(0.002), vec2(0.998))).rgb;
    vec3 water = mix(refracted, Tint, 0.35);
    water += pow(1.0 - max(dot(normal, -dir), 0.0), 3.0) * 0.3;   // светлая кромка

    fragColor = vec4(water, 1.0);
}
"""

water = Shader("water_blobs", WATER)


@events.render_3d
def draw(event):
    if not mod.isEnabled() or not world.ingame():
        return

    me = world.self()
    if me is None:
        return

    camera = event.getCamera().getPos()
    clock = time.time()
    count = int(s_count.get())

    for i in range(count):
        phase = clock * (0.7 + i * 0.13) + i * 2.399
        x = me.getX() + math.cos(phase) * 1.9
        y = me.getY() + 1.1 + math.sin(clock * 0.5 + i) * 0.5
        z = me.getZ() + math.sin(phase) * 1.9
        # ВАЖНО: шейдер считает в координатах относительно камеры
        water.set("Blobs[%d]" % i, x - camera.x, y - camera.y, z - camera.z, 0.55)

    water.set("Count", count)
    water.set("Smooth", s_smooth.get())
    water.set("Steps", s_quality.get())
    water.set("Tint", 0.24, 0.59, 0.86)
    water.fullscreen(event)
```

⚠️ **Координаты в `fullscreen` всегда относительно камеры.** `InvViewProj` собран из матриц кадра, где мир уже
сдвинут на минус позицию камеры: мировые координаты дадут фигуру где-то за горизонтом.

⚠️ **Сравнение с `sceneDist` обязательно**, иначе шар нарисуется поверх стен и блоков, как рентген.

⚠️ **Шагов столько, сколько нужно, и ни шагом больше.** Каждый шаг это `map()` по всем телам для каждого
пикселя экрана: 56 шагов на 8 шаров это уже полтысячи операций на пиксель. Держи настройку качества.

⚠️ **Массив `uniform` ставится по индексу в имени**: `set("Blobs[3]", x, y, z, r)`.

---

## 18. Текст песни в мире (`music` + `render3d.text`)

Строка песни встаёт перед игроком, а прошлая осыпается буквами на землю. Музыку опрашиваем в `tick`,
физику двигаем по реальному времени в `render_3d`, а вся пачка букв уходит **одним** `render3d.texts`.

```python
import math
import time

mod = Module("World Lyrics", "visuals")

s_size = Slider(mod, "Размер букв").min(0.05).max(0.6).step(0.01).set(0.22).suffix(" бл")
s_fall = Slider(mod, "Скорость падения").min(3).max(20).step(0.5).set(11)
c_text = ColorSetting(mod, "Цвет").color(207, 34, 225).alpha(True)

FONT = "roundbold"
state = {"index": -1, "line": None, "letters": [], "clock": time.monotonic()}


@events.tick
def poll(event):
    if not mod.isEnabled() or not world.ingame():
        return

    # плеера может не быть вовсе, а строка меняется по index, а не по тексту
    line = music.current_lyric()
    if not line or int(line["index"]) == state["index"]:
        return

    state["index"] = int(line["index"])
    shatter()                                  # прошлая строка рассыпается
    spawn(str(line["text"]).strip())


def spawn(text):
    me = world.self()
    yaw = math.radians(float(me.getYaw()))
    forward = (-math.sin(yaw), math.cos(yaw))
    state["line"] = {
        "text": text,
        "size": s_size.get(),
        "x": me.getX() + forward[0] * 7.0,
        "y": me.getEyeY() + 1.4,
        "z": me.getZ() + forward[1] * 7.0,
    }


def shatter():
    line = state["line"]
    state["line"] = None
    if line is None:
        return

    size = line["size"]
    width = render3d.text_width(line["text"], size, FONT)   # в БЛОКАХ, не в пикселях
    yaw = math.radians(float(world.self().getYaw()))
    right = (-math.cos(yaw), -math.sin(yaw))

    for i, (char, offset, char_width) in enumerate(render3d.letters(line["text"], size, FONT)):
        if char.isspace():
            continue
        shift = offset + char_width * 0.5 - width * 0.5
        state["letters"].append({
            "char": char, "size": size, "roll": 0.0,
            "x": line["x"] + right[0] * shift, "y": line["y"], "z": line["z"] + right[1] * shift,
            "vx": math.cos(i) * 0.4, "vy": 0.3, "vz": math.sin(i) * 0.4,
        })

    del state["letters"][:-45]                 # потолок, иначе буквы копятся без конца


@events.render_3d
def draw(event):
    if not mod.isEnabled() or not world.ingame():
        return

    now = time.monotonic()
    delta = min(0.1, now - state["clock"])
    state["clock"] = now

    items = []
    if state["line"]:
        line = state["line"]
        items.append({"text": line["text"], "pos": (line["x"], line["y"], line["z"]),
                      "size": line["size"], "color": c_text.get()})

    for letter in state["letters"]:
        letter["vy"] -= s_fall.get() * delta
        letter["x"] += letter["vx"] * delta
        letter["y"] += letter["vy"] * delta
        letter["z"] += letter["vz"] * delta
        letter["roll"] += 90.0 * delta
        items.append({"text": letter["char"], "pos": (letter["x"], letter["y"], letter["z"]),
                      "size": letter["size"], "color": c_text.get(), "roll": letter["roll"]})

    if items:
        # вся пачка одним draw call; обводка общая, её альфа подгоняется под альфу надписи
        render3d.texts(event, items, font=FONT, outline=Color(255, 238, 255, 220))
```

⚠️ **`size` в блоках.** 0.22 это чуть меньше четверти блока. Кегль экрана (`font("roundbold", 21)`) тут ни при чём,
и мерить строку надо `render3d.text_width`, иначе раскладка букв разъедется.

⚠️ **Строка меняется по `index`.** В припеве одинаковые строки идут подряд, и сравнение по тексту их слепит.

⚠️ **Буквам нужен потолок.** Каждая строка добавляет десятки букв: без обрезки списка они копятся до конца песни.

⚠️ **Одна пачка вместо цикла.** Полсотни отдельных `render3d.text` это полсотни draw call, `texts` рисует их разом.


## 19. Полоска активных баффов (иконки + время)

```python
mod = Module("BuffBar", "Visuals")
bar = Hud("BuffBar", icon="hud/potion", width=120, height=14, x=8, y=40)


@bar.render
def draw(d):
    if not world.ingame():
        return

    active = effects.list()               # снимок берём каждый кадр: время идёт
    d.size(max(20, len(active) * 40), 14) # ширина под число значков
    d.client_rect()

    x = 3
    for eff in active:
        d.effect(eff, x, 2, 10)           # ванильный значок из атласа игры
        d.text(eff.time, x + 12, 4, size=6, color=eff.color)
        x += 40


@events.effect_removed
def on_end(event):
    eff = event.getEffect()
    if event.isExpired() and eff.good:
        notify.effect("Кончился %s" % eff.name, eff, eff.name, eff.color)
```

⚠️ **Эффект — снимок.** `effects.list()` зовут в кадре отрисовки, а не сохраняют в глобальную
переменную: у сохранённого время замрёт.

⚠️ **Порядок стабильный.** Список отсортирован по id, поэтому значки не прыгают местами между
кадрами; сортировать самому по времени — значит получить прыгающий ряд.

⚠️ **Служебные эффекты спрятаны.** Сервер вешает эффекты без частиц и значка, их в списке нет;
нужны — `effects.list(hidden=True)`.
