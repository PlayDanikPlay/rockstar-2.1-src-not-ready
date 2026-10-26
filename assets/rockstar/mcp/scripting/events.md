# События — полный справочник (58 событий)

## Как подписаться

Три эквивалентных способа (имя события нечувствительно к регистру):

```python
@events.tick
def on_tick(event): ...

events.tick(on_tick)
events.tick.on(on_tick)
events.getEvent("tick").on(on_tick)
```

## Правила

- Колбэк получает **сырой Java-объект события** — вызывай его настоящие геттеры (`event.getEntity()`, `event.getContext()`).
- Отменяемые события: `event.cancel()`, проверка — `event.isCancelled()`.
- **Ошибка внутри обработчика выгружает скрипт** (`[Python Error]` в чат, трейсбек — в `latest.log`) **и убивает автоперезагрузку по сохранению файла**: чтобы поднять скрипт заново, нужен `.py load <имя>`. Защищайся от `None` и оборачивай рискованное в `try/except`.
- **Клавиатура и мышь есть:** `key`, `char_typed`, `mouse`, `scroll`, `mouse_move` (§46-50), коды клавиш — в глобале `keys`. Если действие одно и его достаточно повесить на клавишу, проще бинд модуля (`mod.setKey`) + `module_toggled` или `Button(mod, "Run").action(fn)`: тогда клавишу выбирает игрок, а не скрипт.
- Обработчик снимается автоматически при выгрузке скрипта.
- Событий ровно 58 — список ниже исчерпывающий. Ничего другого не существует.
  В частности, `PostHudRenderEvent` и события чата (`ChatTypeEvent`, `ChatKeyPressEvent`, ...) в клиенте есть, но **скрипту недоступны** (нет `@EventInfo`). `@events.tick` — это тик игрока (`ClientPlayerTickEvent`), тик игры — отдельное событие `game_tick`.
  `render_2d` / `pre_render_2d` приходят только **в игре** (из InGameHud) — вне мира их не будет.

## Объекты из события готовы к работе

Событие приходит в обёртке моста, поэтому named-имена работают и у него самого (`e.getContext()`, `e.getModule()`, `e.getTickDelta()`, `e.cancel()`, `e.setX(...)`), и у всего, что вернули его геттеры (`getEntity()`, `getPacket()`, `getStack()`, `getBlockPos()`, `getVelocity()`, `getMatrices()`, `getCamera()`).

```python
@events.attack
def on_attack(e):
    ent = e.getEntity()
    print(ent.getX())
```

Так же ведут себя объекты из `mc.*` и `world.*` (`world.self()`, `world.players()`, `world.target()`, ...). `wrap(...)` в старых скриптах ничего не ломает: обёртка идемпотентна.

---

## Сводная таблица

| Имя | Отменяемо | Поля |
|---|---|---|
| `tick` | — | (пусто) |
| `motion` | ✅ | x/y/z, yaw, pitch, onGround, sneaking, sprinting (get + set) |
| `input` | — | forward, strafe, jump, sneak, sprint (get + set), setYaw, setYawSmooth, sneakSlowDownMultiplier |
| `move_post` | — | `getSpeed()`, `getMovementInput()` |
| `travel_post` | — | `getOldVelocity()` / `setOldVelocity()` |
| `slowdown` | ✅ | — |
| `attack` | ✅ | `getEntity()` → **`Entity`** (не `LivingEntity`!) |
| `after_attack` | ✅ | `getEntity()` → **`Entity`** |
| `block_break` | ✅ | `getBlockPos()` |
| `block_place` | — | `getPlacePos()`, `getHitPos()`, `getSide()`, `getHand()`, `getStack()` |
| `entity_jump` | ✅ | `getEntity()` (LivingEntity) |
| `pickup` | — | `getEntity()`, `getItemStack()`, `getCount()` |
| `firework` | — | `getEntity()`, `getVelocity()`/`setVelocity()`, `getRocketEntity()` |
| `rotate_camera` | ✅ | `getDeltaYaw()`/`setDeltaYaw()`, `getDeltaPitch()`/`setDeltaPitch()` |
| `send_message` | ✅ | `getMessage()` / `setMessage()` |
| `world_change` | — | (пусто) |
| `send_packet` | ✅ | `getPacket()` / `setPacket()` |
| `receive_packet` | ✅ | `getPacket()` |
| `connect` | — | `getAddress()`, `getInfo()`, `getCookieStorage()` |
| `render_2d` | — | `getContext()`, `getTickDelta()` |
| `pre_render_2d` | — | `getContext()`, `getTickDelta()` |
| `render_3d` | — | `getMatrices()`, `getCamera()`, `getPositionMatrix()`, `getProjectionMatrix()`, `getTickDelta()` |
| `pre_render_3d` | — | те же поля, что у `render_3d` — но мир ещё не нарисован |
| `module_toggled` | — | `getModule()` (PyModule), `isState()` |
| `language_changed` | — | `getCode()` (str) |
| `newton_started` | — | `getProcess()` |
| `newton_path` | — | `getProcess()`, `getSteps()` |
| `newton_node` | — | `getProcess()`, `getX()`, `getY()`, `getZ()`, `getStep()`, `getSteps()` |
| `newton_finished` | — | `getProcess()` |
| `newton_failed` | — | `getProcess()`, `getReason()` |
| `game_tick` | — | (пусто) — тик игры, идёт и вне мира |
| `tick_end` | — | (пусто) — конец тика игрока |
| `keep_sprint` | ✅ | (пусто) — отмена оставляет разгон при ударе |
| `trace` | ✅ | `getYaw()`/`setYaw()`, `getPitch()`/`setPitch()` |
| `collision_shape` | ✅ | `getState()`, `getPos()`, `getShape()`/`setShape()` — 🔥 тысячи вызовов за тик |
| `sound` | — | `getSound()` (SoundInstance) |
| `entity_death` | — | `getEntity()`, `getSource()`, `getKillerEntity()` |
| `finish_eat` | — | `getUser()`, `getStack()` |
| `effect_added` | — | `getEffect()`, `getEntity()`, `isUpgraded()` |
| `effect_removed` | — | `getEffect()`, `getEntity()`, `isExpired()` |
| `start_break_block` | ✅ | `getBlockPos()` |
| `break_totem` | — | `getEntity()`, `getStack()` |
| `set_cooldown` | — | `getCooldown()`/`setCooldown()`, `getCooldownGroup()` |
| `close_screen` | — | `getScreen()` |
| `container_click` | — | `getX()`, `getY()`, `getButton()` — единственное событие мыши |
| `hand_render` | ✅ | `getArm()`, `getSwingProgress()`, `getEquipProgress()`, `getItemStack()`, `getMatrices()` |
| `camera_update` | — | `getCamera()`, `getFocusedEntity()`, `isThirdPerson()`, `isInverseView()`, `getTickDelta()` |
| `game_render` | — | (пусто) — кадр игры, приходит и в меню |
| `notification` | — | `getStyle()`, `getType()`, `getTitle()`, `getText()` |

---

## 1. `tick` — каждый тик игрока

Не отменяемо. Полей нет. Главный поток — тут безопасно трогать `mc`, модули, HUD.

```python
@events.tick
def on_tick(event):
    if not world.ingame():
        return
    p = world.self()
    client.overlay("Y = %.1f" % p.getY())
```

## 2. `motion` — отправка позиции/поворота на сервер

Отменяемо. Поля: `getX/getY/getZ()`, `setX/setY/setZ()`, `getYaw()/setYaw()`, `getPitch()/setPitch()`, `isOnGround()/setOnGround()`, `isSneaking()/setSneaking()`, `isSprinting()/setSprinting()`.

```python
@events.motion
def on_motion(event):
    if mod.isEnabled():
        event.setOnGround(True)        # подмена флага земли
```

## 3. `input` — ввод движения

Не отменяемо. Поля: `getForward()/setForward()`, `getStrafe()/setStrafe()`, `isJump()/setJump()`, `isSneak()/setSneak()`, `isSprint()/setSprint()`,
`setYaw(yaw)` / `setYaw(yaw, direction)`, `setYawSmooth(yaw)` / `setYawSmooth(yaw, direction)`,
`getSneakSlowDownMultiplier()` / `setSneakSlowDownMultiplier(v)` (множитель замедления в приседе — 1.0 убирает его).

```python
@events.input
def on_input(event):
    if mod.isEnabled():
        event.setSprint(True)          # всегда бежим
```

## 4. `move_post` — после расчёта движения

Не отменяемо. Поля: `getSpeed()`, `getMovementInput()`.

```python
@events.move_post
def on_move_post(event):
    if mod.isEnabled():
        client.overlay("speed: %.3f" % event.getSpeed())
```

## 5. `travel_post` — после travel()

Не отменяемо. Поля: `getOldVelocity()`, `setOldVelocity(v)` — это `Vec3d` Minecraft, методы зовутся сразу.

```python
@events.travel_post
def on_travel_post(event):
    old = event.getOldVelocity()
    print(old.x, old.y, old.z)               # у Vec3d это поля
```

## 6. `slowdown` — замедление (еда, щит, натянутый лук)

Отменяемо, полей нет. Отмена = убрать замедление.

```python
@events.slowdown
def on_slowdown(event):
    if mod.isEnabled():
        event.cancel()
```

## 7. `attack` — перед атакой по сущности

Отменяемо. Поле: `getEntity()`.

> ⚠️ **Это `Entity`, а НЕ `LivingEntity`.** Бьём лодку/рамку/стойку — `getHealth()` не существует, скрипт падает и выгружается. Проверяй тип или зови только методы `Entity`.
> Имя: `getNameForScoreboard()` — одна строка вместо возни с `Text`.

```python
@events.attack
def on_attack(event):
    ent = event.getEntity()
    client.msg("Атакую: " + str(ent.getNameForScoreboard()))

    if is_instance(ent, "net.minecraft.entity.LivingEntity"):
        client.msg("HP: %.1f" % float(ent.getHealth()))   # только теперь можно getHealth()
```

## 8. `after_attack` — сразу после атаки

Отменяемо. Поле: `getEntity()` (тоже `Entity`).

```python
@events.after_attack
def on_after_attack(event):
    hits["count"] = hits.get("count", 0) + 1
```

## 9. `block_break` — ломание блока

Отменяемо. Поле: `getBlockPos()` (`BlockPos`, методы зовутся сразу).

```python
@events.block_break
def on_block_break(event):
    pos = event.getBlockPos()
    print("break", pos.getX(), pos.getY(), pos.getZ())
```

## 10. `block_place` — постановка блока

Не отменяемо. Поля: `getPlacePos()`, `getHitPos()`, `getSide()`, `getHand()`, `getStack()` — все возвращают классы Minecraft, готовые к работе.

```python
@events.block_place
def on_block_place(event):
    stack = event.getStack()
    pos = event.getPlacePos()
    print(stack.getCount(), pos.getX(), pos.getY(), pos.getZ())
```

## 11. `entity_jump` — прыжок живой сущности

Отменяемо. Поле: `getEntity()` (LivingEntity).

```python
@events.entity_jump
def on_entity_jump(event):
    ent = event.getEntity()                # слева _J, поэтому == сравнивает сами объекты
    if ent == world.self():
        client.overlay("прыжок")
```

## 12. `pickup` — подбор предмета

Не отменяемо. Поля: `getEntity()`, `getItemStack()`, `getCount()`. `getCount()` — метод события (число), `getEntity()` / `getItemStack()` — объекты Minecraft, готовые к работе.

```python
@events.pickup
def on_pickup(event):
    client.msg("подобрано x%d" % int(event.getCount()))
```

## 13. `firework` — фейерверк (элитры)

Не отменяемо. Поля: `getEntity()`, `getVelocity()` / `setVelocity(v)`, `getRocketEntity()`.

```python
@events.firework
def on_firework(event):
    v = event.getVelocity()                # Vec3d
    print(v.x, v.y, v.z)
```

## 14. `rotate_camera` — поворот камеры мышью

Отменяемо. Поля: `getDeltaYaw()/setDeltaYaw()`, `getDeltaPitch()/setDeltaPitch()`.

```python
@events.rotate_camera
def on_rotate_camera(event):
    if mod.isEnabled():
        event.setDeltaYaw(event.getDeltaYaw() * 0.5)   # снизить чувствительность
```

## 15. `send_message` — исходящее сообщение в чат

Отменяемо. Поля: `getMessage()`, `setMessage(str)`.

```python
@events.send_message
def on_send_message(event):
    msg = str(event.getMessage())
    if msg.startswith("!"):
        event.cancel()                                  # не отправлять
    else:
        event.setMessage(msg + " ")
```

## 16. `world_change` — смена мира

Не отменяемо, полей нет.

```python
@events.world_change
def on_world_change(event):
    cache.clear()
```

## 17. `send_packet` — исходящий пакет

Отменяемо. Поля: `getPacket()`, `setPacket(p)`.

> Тип пакета определяется через `is_instance(obj, "named.Fqn")` — `isinstance` и `getClass().getName()` в релизе бесполезны (обфускация).
> ⚠️ У `PlayerMoveC2SPacket` геттеры `getX()/getY()/getZ()/getYaw()/getPitch()` объявлены с одним аргументом (fallback), а перегрузки резолвятся по числу аргументов → вызов без аргументов упадёт. **Читай поля:** `p.x`, `p.y`, `p.z`, `p.yaw`, `p.pitch`, `p.onGround`.

```python
MOVE = "net.minecraft.network.packet.c2s.play.PlayerMoveC2SPacket"

@events.send_packet
def on_send_packet(event):
    p = event.getPacket()
    if not is_instance(p, MOVE):                 # ловит и наследников ($Full и т.п.)
        return
    client.overlay("y=%.2f ground=%s" % (float(p.y), bool(p.onGround)))
    # event.cancel()      # отменить отправку
```

## 18. `receive_packet` — входящий пакет

Отменяемо. Поле: `getPacket()`.

```python
@events.receive_packet
def on_receive_packet(event):
    if is_instance(event.getPacket(),
                   "net.minecraft.network.packet.s2c.play.EntityVelocityUpdateS2CPacket"):
        event.cancel()                                       # антивелосити
```

## 19. `connect` — подключение к серверу

Не отменяемо. Поля: `getAddress()`, `getInfo()`, `getCookieStorage()`.

```python
@events.connect
def on_connect(event):
    client.msg("Подключаюсь: " + str(event.getAddress()))
```

## 20. `render_2d` — 2D-рендер поверх HUD клиента

Не отменяемо. Поля: `getContext()` (CustomDrawContext), `getTickDelta()`.

```python
@events.render_2d
def on_render_2d(event):
    if not mod.isEnabled():
        return
    ctx = event.getContext()
    ctx.drawRoundedRect(10, 10, 120, 22, border(6), Color(0, 0, 0, 180))
    ctx.drawText(font("medium", 8), "Rockstar", 16, 16, Color(255, 255, 255))
```

## 21. `pre_render_2d` — 2D-рендер ДО HUD клиента

Не отменяемо. Поля те же: `getContext()`, `getTickDelta()`. Рисуй тут фоны/подложки, которые должны быть под интерфейсом клиента.

```python
@events.pre_render_2d
def on_pre_render_2d(event):
    event.getContext().drawRect(0, 0, 60, 4, Color(86, 124, 252))
```

## 22. `render_3d` — 3D-рендер в мире

Не отменяемо. Поля: `getMatrices()`, `getCamera()`, `getPositionMatrix()`, `getProjectionMatrix()`, `getTickDelta()`.
Сам объект события передаётся первым аргументом во все методы `render3d.*`.

```python
@events.render_3d
def on_render_3d(event):
    if not mod.isEnabled():
        return
    for p in world.players():
        render3d.box(event, p, Color(255, 80, 80))
```

## 23. `module_toggled` — модуль включили/выключили

Не отменяемо. Поля: `getModule()` (PyModule), `isState()` (bool — новое состояние).
Это замена отсутствующим `on_enable` / `on_disable`.

```python
@events.module_toggled
def on_module_toggled(event):
    m = event.getModule()
    if m.getName() == "MyModule":
        if event.isState():
            state["start"] = Timer()
            client.msg("MyModule включён")
        else:
            client.msg("MyModule выключен")
```

## 24. `newton_started` — Newton взял задачу

Не отменяемо. Поле: `getProcess()` (str) — `goto`, `mine <id>`, `excavate`, `fill` или `elytra`.
Приходит ДО расчёта маршрута: сколько будет шагов, ещё неизвестно.

```python
@events.newton_started
def on_newton_started(event):
    client.msg("Newton: " + event.getProcess())
```

## 25. `newton_path` — маршрут построен

Не отменяемо. Поля: `getProcess()` (str), `getSteps()` (int — длина маршрута в шагах).
Приходит заново после каждого пересчёта пути. **Только у ходьбы** (`goto`): элитра и копка маршрут по шагам не строят.

```python
@events.newton_path
def on_newton_path(event):
    client.msg("Маршрут: %d шагов" % event.getSteps())
```

## 26. `newton_node` — пройден шаг маршрута

Не отменяемо. Поля: `getProcess()`, `getX()`, `getY()`, `getZ()` (int — блок, на который встали), `getStep()` (номер с 1), `getSteps()` (всего).
За один тик может прийти несколько раз подряд: исполнитель пути проскакивает шаги на инерции.

```python
@events.newton_node
def on_newton_node(event):
    client.overlay("шаг %d/%d" % (event.getStep(), event.getSteps()))
```

## 27. `newton_finished` — задача выполнена

Не отменяемо. Поле: `getProcess()`. Только успешное завершение (дошли, долетели, докопали, заполнили).
Ставить новую задачу прямо тут можно — Newton уже свободен. Это штатный способ обойти цепочку точек.

```python
@events.newton_finished
def on_newton_finished(event):
    newton.goto(NEXT_POINT, radius=1)
```

## 28. `newton_failed` — задача сорвалась или отменена

Не отменяемо. Поля: `getProcess()`, `getReason()` (str).
Причины: `отменён`, `путь не найден`, `слишком много сбоев`, `элитра не надета`, `нет блока в инвентаре`, `посадка не удалась`, `прерван`.

⚠️ `newton.cancel()` и запуск новой задачи поверх старой тоже дают это событие с причиной `отменён` — перезапуск без проверки причины даёт вечный круг.

```python
@events.newton_failed
def on_newton_failed(event):
    if event.getReason() == "отменён":
        return
    client.warn("Newton встал: " + event.getReason())
```

## 29. `game_tick` — тик самой игры

Не отменяемо. Полей нет. В отличие от `tick` приходит и **вне мира**: главное меню, экран загрузки, подключение.
Годится для того, что живёт вне мира (часы в меню, счёт времени сессии). ⚠️ Игрока может не быть — `world.ingame()` обязателен.

```python
@events.game_tick
def on_game_tick(event):
    ticks["n"] += 1
```

## 30. `tick_end` — конец тика игрока

Не отменяемо. Полей нет. `tick` идёт до расчёта тика, `tick_end` — после: тут видно результат (куда реально сдвинулись, изменилась ли скорость).
Менять движение здесь поздно — для этого `tick`, `motion`, `input`.

```python
@events.tick_end
def on_tick_end(event):
    if not world.ingame():
        return
    p = mc.player
    speed = ((p.getX() - last["x"]) ** 2 + (p.getZ() - last["z"]) ** 2) ** 0.5 * 20
    last["x"], last["z"] = p.getX(), p.getZ()
```

## 31. `keep_sprint` — удар гасит разгон

Отменяемо, полей нет. Приходит в момент атаки, перед тем как игра погасит спринт и обрежет скорость.
`event.cancel()` оставляет разгон — это и есть KeepSprint. Приходит на каждый удар, даже когда модуль выключен.

```python
@events.keep_sprint
def on_keep_sprint(event):
    if mod.isEnabled():
        event.cancel()
```

## 32. `trace` — луч взгляда

Отменяемо. Поля: `getYaw()`/`setYaw(v)`, `getPitch()`/`setPitch(v)`.
Этим лучом игра выбирает блок под прицелом и цель удара. `cancel()` пересчитывает луч по углам из события — камера смотрит в одну сторону, взаимодействие идёт в другую. Без `cancel()` подменённые углы ни на что не влияют.

⚠️ Луч пускают и чужие сущности, не только твой игрок. ⚠️ Тот же луч выбирает блок для добычи.

```python
@events.trace
def on_trace(event):
    target = world.target()
    if target is None or not mod.isEnabled():
        return
    yaw, pitch = rotations.to(target)
    event.setYaw(yaw)
    event.setPitch(pitch)
    event.cancel()
```

## 33. `collision_shape` — форма столкновения блока

Отменяемо. Поля: `getState()` (BlockState), `getPos()` (BlockPos), `getShape()`/`setShape(shape)`.
`cancel()` делает блок проходимым; своя форма — `VoxelShapes = jimport("net.minecraft.util.shape.VoxelShapes")`, затем `VoxelShapes.empty()`.

🔥 **САМОЕ ГОРЯЧЕЕ событие клиента**: зовётся на каждый блок рядом с каждой движущейся сущностью, тысячи раз за тик. Обработчик — 2-3 строки с ранним выходом. `print` / `client.msg` здесь вешают игру.
⚠️ Действует только на клиенте: сервер считает блок целым и вернёт игрока назад.

```python
@events.collision_shape
def on_collision(event):
    if not mod.isEnabled():          # выход первой строкой — обязателен
        return
    if "cobweb" in str(event.getState().getBlock()):
        event.cancel()
```

## 34. `sound` — играет звук

Не отменяемо. Поле: `getSound()` (SoundInstance, нужен `wrap`).
Основа детектов: тотем, сундук, кристалл, жемчуг — сервер шлёт звук даже тогда, когда сущность не видна. Имя звука: `str(event.getSound().getId())` → `minecraft:entity.player.levelup`.
Заглушить звук нельзя, событие только наблюдает.

```python
@events.sound
def on_sound(event):
    name = str(event.getSound().getId())
    if "totem" in name:
        client.warn("Рядом сработал тотем")
```

## 35. `entity_death` — существо умерло

Не отменяемо. Поля: `getEntity()` (LivingEntity), `getSource()` (DamageSource или None), `getKillerEntity()` (LivingEntity или None).
Приходит и на дальних мобов, о смерти которых сообщил сервер.

```python
@events.entity_death
def on_death(event):
    killer = event.getKillerEntity()
    if killer is not None and killer.getId() == mc.player.getId():
        kills["n"] += 1
```

## 36. `finish_eat` — предмет доеден

Не отменяемо. Поля: `getUser()` (PlayerEntity), `getStack()` (ItemStack). Оба — объекты Minecraft, нужен `wrap`.
Событие про конец использования, а не про начало. Приходит и на чужих игроков — сверяй `getUser()`.

```python
@events.finish_eat
def on_finish_eat(event):
    if event.getUser().getId() == mc.player.getId():
        client.overlay("съедено: " + str(event.getStack().getItem()))
```

## 37. `start_break_block` — начали ломать блок

Отменяемо. Поле: `getBlockPos()` (нужен `wrap`).
Первый удар по блоку, до начала ломки: `cancel()` запрещает ломку. Контраст: `block_break` приходит, когда блок уже сломан.

```python
@events.start_break_block
def on_start_break(event):
    pos = event.getBlockPos()
    if int(pos.getY()) < 0:
        event.cancel()
```

## 38. `break_totem` — сработал тотем

Не отменяемо. Поля: `getEntity()` (LivingEntity), `getStack()` (ItemStack).
Приходит на любое существо, включая тебя — сверяй `getEntity()`. Видно только тех, кто в зоне прогрузки.

```python
@events.break_totem
def on_totem(event):
    name = str(event.getEntity().getNameForScoreboard())
    client.msg(name + " спалил тотем")
```

## 39. `set_cooldown` — сервер ставит перезарядку

Не отменяемо, но значение подменяемое. Поля: `getCooldown()`/`setCooldown(ticks)`, `getCooldownGroup()` (Identifier).
`setCooldown(0)` убирает серую заливку **на клиенте**. ⚠️ Сервер считает свой кулдаун: раньше времени предмет всё равно не сработает.

```python
@events.set_cooldown
def on_cooldown(event):
    if mod.isEnabled():
        event.setCooldown(0)
```

## 40. `close_screen` — экран закрывается

Не отменяемо. Поле: `getScreen()` (Screen, нужен `wrap`).
Тип экрана проверяют через `is_instance(event.getScreen(), "net.minecraft.client.gui.screen...")`. Событие про закрытие; открытие ловят проверкой `mc.currentScreen` в `tick`.

```python
@events.close_screen
def on_close(event):
    state["chest_open"] = False
```

## 41. `container_click` — клик в контейнере

Не отменяемо. Поля: `getX()`, `getY()` (float, пиксели экрана), `getButton()` (int: 0 левая, 1 правая, 2 колесо).
**Единственное событие мыши в API**, и работает только внутри контейнеров (сундук, печка, верстак, инвентарь). Какой слот под курсором — считают через `mc.currentScreen`.

```python
@events.container_click
def on_click(event):
    client.overlay("клик %d: %.0f, %.0f" % (event.getButton(), event.getX(), event.getY()))
```

## 42. `hand_render` — отрисовка руки

Отменяемо. Поля: `getArm()`, `getSwingProgress()`, `getEquipProgress()`, `getItemStack()`, `getMatrices()` (MatrixStack, нужен `wrap`).
`cancel()` убирает ванильную анимацию замаха; матрицей двигают и вращают руку. ⚠️ Каждый кадр и до двух раз подряд (две руки) — ничего тяжёлого. Матрица валидна только внутри события.

```python
@events.hand_render
def on_hand(event):
    if mod.isEnabled():
        event.cancel()
```

## 43. `camera_update` — камера обновилась

Не отменяемо. Поля: `getCamera()`, `getFocusedEntity()`, `isThirdPerson()`, `isInverseView()`, `getTickDelta()`.
Только чтение: подвинуть камеру через событие нельзя. При включённом FreeCam клиента событие не приходит.

```python
@events.camera_update
def on_camera(event):
    state["third"] = bool(event.isThirdPerson())
```

## 44. `game_render` — кадр игры

Не отменяемо. Полей нет. Приходит **всегда**: в мире, в главном меню, на чужих экранах — в отличие от `render_2d`, который есть только в игре.
Холста нет, рисовать нечем: это место для анимаций и счёта времени, которые потом покажет `render_2d`.

```python
@events.game_render
def on_frame(event):
    phase["t"] += 0.05
```

## 45. `notification` — клиент показал уведомление

Не отменяемо. Поля: `getStyle()` (`island`, `crosshair`, `mini`, `irc`), `getType()` (`success`, `error`, `info`), `getTitle()`, `getText()`.
Приходит на любую плашку клиента: свою, чужого модуля и отправленную скриптом через `notify`.

⚠️ Своё уведомление тоже сюда приходит: `notify` внутри обработчика без проверки зациклит клиент.

```python
@events.notification
def on_notification(event):
    if event.getType() == "error":
        client.overlay("ошибка: " + event.getText())
```
## 46. `key` — клавиша нажата или отпущена

Отменяемо. Поля: `getKey()`, `getName()`, `isPress()`, `isRelease()`, `isRepeat()`, `isShift()`, `isCtrl()`, `isAlt()`, `isScreenOpen()`, `getScancode()`, `getMods()`.
Приходит на нажатие, отпускание и автоповтор, **и в игре, и на открытых экранах**.

⚠️ Сравнивай `getKey()` с `keys.<ИМЯ>`, а не `getName()` со строкой: подпись клавиши зависит от языка клиента.
⚠️ Пока открыт чат, событие приходит как обычно — без `isScreenOpen()` скрипт сработает на буквы, которые игрок печатает.
⚠️ Отменяя нажатие, отменяй и отпускание той же клавиши: съешь только отпускание, и игра будет считать её зажатой.
⚠️ Esc, `.` и клавиши открытия чата клиент отменить не даст (иначе сломанный скрипт запирает игрока). С зажатым F3 событие не приходит.

```python
@events.key
def on_key(event):
    if event.isScreenOpen() or not event.isPress():
        return
    if event.getKey() == keys.G:
        client.msg("нажата G")
```

## 47. `char_typed` — введён символ

Отменяемо. Поля: `getChar()`, `getCodePoint()`, `isShift()`, `isCtrl()`, `isAlt()`, `isScreenOpen()`.
Раскладка, регистр и модификаторы уже применены. На стрелки, Enter, Backspace и Esc **не приходит** — это `key`.

⚠️ Одно нажатие даёт оба события: сначала `key`, потом `char_typed`. Не считай ввод дважды.

```python
@events.char_typed
def on_char(event):
    if event.isScreenOpen():
        typed.append(event.getChar())
```

## 48. `mouse` — кнопка мыши

Отменяемо. Поля: `getButton()`, `getName()`, `isLeft()`, `isRight()`, `isMiddle()`, `isPress()`, `isRelease()`, `getX()`, `getY()`, `isShift()`, `isCtrl()`, `isAlt()`, `isScreenOpen()`.
Координаты курсора — в тех же единицах, в которых рисует `render_2d`.

⚠️ `cancel()` гасит клик для игры целиком: ни удара, ни постановки блока. С зажатым F3 событие не приходит.
⚠️ Клики по своим меню и HUD-элементам ловятся их собственными обработчиками — это событие для них не нужно.

```python
@events.mouse
def on_mouse(event):
    if event.isPress() and event.isRight() and keys.down("LEFT_ALT"):
        event.cancel()
```

## 49. `scroll` — прокрутка колеса

Отменяемо. Поля: `getVertical()`, `getHorizontal()`, `isUp()`, `isDown()`, `getX()`, `getY()`, `isScreenOpen()`.
В игре прокрутка листает хотбар, на экранах прокручивает списки; `cancel()` забирает её себе.

⚠️ Отменять без условия не стоит: игрок потеряет переключение хотбара. Горизонтальная прокрутка у обычной мыши всегда 0.

```python
@events.scroll
def on_scroll(event):
    if keys.down("LEFT_ALT"):
        state["range"] += 0.5 if event.isUp() else -0.5
        event.cancel()
```

## 50. `mouse_move` — курсор сдвинулся

Не отменяемо. Поля: `getX()`, `getY()`, `getDx()`, `getDy()`, `isScreenOpen()`.
В игре камера крутится тем же движением, поэтому событие идёт почти непрерывно.

⚠️ Ничего тяжёлого внутри: складывай позицию в переменную, работай в `render_2d` или в `tick`.
⚠️ Поворот камеры этим событием не остановить — для этого есть `rotate_camera`.

```python
@events.mouse_move
def on_move(event):
    if dragging["on"]:
        panel["x"] += event.getDx()
        panel["y"] += event.getDy()
```

## 51. `language_changed` — игрок сменил язык клиента

Не отменяемо. Поля: `getCode()` — новый язык (`ru_ru`, `en_us`, `uk_ua`, `pl_pl`).

Имена настроек, значения режимов и описания клиент переводит на каждой отрисовке сам — их трогать не нужно.
Пересобирать надо только строки, которые скрипт перевёл один раз и сложил в переменные.

⚠️ Приходит и на старте клиента, когда применяется сохранённый язык.

```python
@events.language_changed
def on_language(event):
    global title
    title = lang("mymod.title")
```

## 52. `menu_render` — слой ПОД меню клиента

Не отменяемо. Поля: `getContext()` — кисточка (`CustomDrawContext`), `getMenu()` — `panel` или `modern`,
`getProgress()` — открытость 0..1 (то же, что `menu.progress`), `isCapture()` — кадр снимается в картинку
для анимации закрытия, `getTickDelta()`.

Идёт каждый кадр, пока меню открыто, ДО того как меню нарисует себя: всё нарисованное ложится под панели.
Координаты панелей и состояние анимации — в глобале `menu` (`menu.panels`, `menu.progress`, `menu.alpha`).

⚠️ Событие уже внутри анимации открытия и в координатах панелей — масштаб руками повторять не нужно.
Нарисованное подпрыгивает вместе с меню и улетает с ним в мир на закрытии.
⚠️ Панели едут каждый кадр (открытие модуля, скролл, перетаскивание окна): читай `menu.panels` в обработчике.
⚠️ Кадр за кадром, как `render_2d`: тяжёлые расчёты тут вешают игру.

```python
@events.menu_render
def under(event):
    ctx = event.getContext()
    for p in menu.panels:
        ctx.drawShadow(p.x - 8, p.y - 8, p.width + 16, p.height + 16,
                       30, border(18), Color(120, 190, 255).withAlpha(110 * menu.progress))
```

## 53. `post_menu_render` — слой НАД меню клиента

Не отменяемо. Поля те же, что у `menu_render`.

То же самое, но ПОСЛЕ отрисовки меню: рамки вокруг панелей, блики, метки поверх интерфейса.

⚠️ Ложится поверх всего меню, включая попапы и подсказки: не закрывай то, по чему игрок кликает.
⚠️ Умножай прозрачность на `menu.alpha`, иначе слой останется висеть, когда меню спрятали клавишей скрытия.

```python
@events.post_menu_render
def over(event):
    ctx = event.getContext()
    fade = menu.progress * menu.alpha
    for p in menu.panels:
        ctx.drawRoundedBorder(p.x, p.y, p.width, p.height,
                              1, border(11), Color(120, 190, 255).withAlpha(180 * fade))
```

## 54. `hud_render` — слой ПОД элементами HUD

Не отменяемо. Поля: `getContext()` — кисточка, `getCount()` — сколько элементов HUD сейчас есть,
`isEditing()` — открыт чат (HUD в режиме правки), `getTickDelta()`.

Идёт каждый кадр, ДО отрисовки элементов HUD клиента: нарисованное ложится под них. Координаты и
анимации всех элементов — в `hud.elements`.

⚠️ Элемент всплывает не только альфой, но и масштабом: слой, который должен сидеть вплотную,
считай от центра с `el.scale`.
⚠️ Спрятанные элементы остаются в списке с `alpha == 0`.
⚠️ Кадр за кадром, как `render_2d`: тяжёлые расчёты тут вешают игру.

```python
@events.hud_render
def under(event):
    ctx = event.getContext()
    for el in hud.elements:
        if el.alpha <= 0.02:
            continue
        ctx.drawRoundedRect(el.x - 4, el.y - 4, el.width + 8, el.height + 8,
                            border(9), Color(120, 190, 255).withAlpha(40 * el.alpha))
```

## 55. `post_hud_render` — слой НАД элементами HUD

Не отменяемо. Поля те же, что у `hud_render`.

То же самое, но ПОСЛЕ отрисовки элементов: рамки, метки, подсказки поверх HUD. Окна правки HUD
рисуются выше, их этот слой не перекрывает.

⚠️ Не закрывай числа и иконки, ради которых HUD и нужен; прозрачность умножай на `el.alpha`.

```python
@events.post_hud_render
def over(event):
    if not event.isEditing():
        return
    ctx = event.getContext()
    for el in hud.elements:
        ctx.drawRoundedBorder(el.x, el.y, el.width, el.height,
                              1, border(7), Color(120, 190, 255).withAlpha(160 * el.alpha))
```

## 56. `effect_added` — выдали эффект

Не отменяемо. Поля: `getEffect()` (эффект, свойства как у `effects.list()`), `getEntity()` (LivingEntity),
`isUpgraded()` (эффект уже висел: подняли уровень или подлили времени).

Приходит и от зелья, и от маяка, и от команды сервера: клиент сравнивает эффекты игрока каждый тик.
Первый тик после входа в мир (и после респавна) событий не даёт — клиент сначала запоминает то, что уже висит.

```python
@events.effect_added
def on_effect(event):
    eff = event.getEffect()
    if eff.bad:
        notify.effect("Повесили %s" % eff.label, eff, eff.label, eff.color)
    else:
        client.msg("%s на %s" % (eff.label, eff.time))
```

⚠️ Эффекты чужих игроков сюда не попадают — сервер их не рассылает.

## 57. `effect_removed` — эффект спал

Не отменяемо. Поля: `getEffect()`, `getEntity()`, `isExpired()` (время вышло само, а не сняли молоком/сервером).

```python
@events.effect_removed
def on_effect_end(event):
    eff = event.getEffect()
    if eff.id == "minecraft:speed" and event.isExpired():
        client.warn("Скорость кончилась")
```

⚠️ Время в эффекте события уже нулевое: это последнее, что клиент видел, а не остаток.
⚠️ При выходе из мира событий не будет — клиент просто забывает список.

## 58. `pre_render_3d` — 3D-рендер ПОД миром

Не отменяемо. Поля те же, что у `render_3d`: `getMatrices()`, `getCamera()`, `getPositionMatrix()`,
`getProjectionMatrix()`, `getTickDelta()`. Событие тоже передаётся первым аргументом в `render3d.*`.

Разница только в моменте: небо уже нарисовано, а блоки и существа — ещё нет. Поэтому нарисованное здесь
прячется за стенами и за спинами, а `render_3d` рисует поверх всего мира.

```python
@events.pre_render_3d
def under_world(event):
    if not world.ingame():
        return
    render3d.ring(event, world.self(), 1.2, 0.02, 48, Color(86, 124, 252, 160))
```

⚠️ Рисуй здесь только то, что должно прятаться за миром: подсветку пола, круги, разметку. Всё, что игрок
обязан видеть сквозь стены (ESP, трассеры, метки целей), делай в `render_3d`.
