import sys
import types
import importlib.abc
import importlib.machinery
import math
import os
import json
import inspect
import array as _array

from pyrock import McBridge
from pyrock.classes import (
    PyModule, PyTimer, PyHud, PyNewton, PyCommands,
    PyNotify, PyInventory, PyTheme, PyTarget, PyFunTime, PyKeys, PySkins, PyLang, PyEsp,
    PyProfile, PyMenu, PyEffects, PyContainer, PyBlocks,
)
from pyrock.classes.settings import (
    PySliderSetting, PyBooleanSetting, PyModeSetting, PySelectSetting,
    PyButtonSetting, PyRangeSetting, PyColorSetting, PyBindSetting,
    PyTextSetting, PyTimeSetting, PyInfoSetting, PyGradientSetting,
    PyPositionSetting, PyBezierSetting, PyBlockSetting,
)
from pyrock.utility.render import ColorRGBA, PyAssets, PyRender3D, PyShaders
from pyrock.utility.sound import PySounds
from pyrock.ui import PyScreen


def _unwrap(v):
    return object.__getattribute__(v, "_obj") if isinstance(v, _J) else v


def _unwrap_deep(v):
    if isinstance(v, _J):
        return _unwrap(v)
    if isinstance(v, (list, tuple)):
        return [_unwrap_deep(x) for x in v]
    if isinstance(v, dict):
        return {k: _unwrap_deep(x) for k, x in v.items()}
    return v


def _wrap(v):
    if v is None or isinstance(v, (bool, int, float, str, _J)):
        return v
    return _J(v)


def _java_list(v):
    it = McBridge.iterator(v)
    if it is None:
        return list(v)
    out = []
    while it.hasNext():
        out.append(it.next())
    return out


class _Bound:
    __slots__ = ("_t", "_n")

    def __init__(self, target, name):
        self._t = target
        self._n = name

    def __call__(self, *args):
        return _wrap(McBridge.invoke(self._t, self._n, [_unwrap(a) for a in args]))


class _J:
    __slots__ = ("_obj",)

    def __init__(self, obj):
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name):
        obj = object.__getattribute__(self, "_obj")
        if McBridge.hasField(obj, name):
            return _wrap(McBridge.getField(obj, name))
        return _Bound(obj, name)

    def __setattr__(self, name, value):
        obj = object.__getattribute__(self, "_obj")
        McBridge.setField(obj, name, _unwrap(value))

    def __call__(self, *args):
        obj = object.__getattribute__(self, "_obj")
        if McBridge.isClass(obj):
            return _wrap(McBridge.constructClass(obj, [_unwrap(a) for a in args]))
        raise TypeError("java-объект не вызывается")

    def __iter__(self):
        obj = object.__getattribute__(self, "_obj")
        it = McBridge.iterator(obj)
        if it is None:
            raise TypeError("java-объект не итерируется")
        while it.hasNext():
            yield _wrap(it.next())

    def __eq__(self, other):
        return object.__getattribute__(self, "_obj") == _unwrap(other)

    def __hash__(self):
        return hash(object.__getattribute__(self, "_obj"))

    def __str__(self):
        return str(object.__getattribute__(self, "_obj"))

    def __repr__(self):
        return "<J " + str(object.__getattribute__(self, "_obj")) + ">"


def jimport(named_fqn):
    return _J(McBridge.findClass(named_fqn))


class _McPackage(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        fqn = self.__name__ + "." + name
        try:
            return _J(McBridge.findClass(fqn))
        except Exception:
            raise AttributeError(name)


class _McFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ("net", "net.minecraft"):
            return importlib.machinery.ModuleSpec(fullname, self, is_package=True)
        if fullname.startswith("net.minecraft."):
            last = fullname.rsplit(".", 1)[1]
            if last[:1].islower():
                return importlib.machinery.ModuleSpec(fullname, self, is_package=True)
        return None

    def create_module(self, spec):
        return _McPackage(spec.name)

    def exec_module(self, module):
        pass


if not any(isinstance(f, _McFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _McFinder())


# ─────────────────────────── Песочница скриптов: начало ───────────────────────────
# Скрипты — это настоящий CPython внутри процесса игры, и без ограничений ему доступно всё, что
# доступно процессу. `import ctypes` открывает kernel32, дальше VirtualQuery/ReadProcessMemory
# читают собственную память клиента и складывают её на диск: дамп изнутри, снаружи процесс никто
# не трогал, антидебаг такого не видит. Тот же ctypes (и subprocess) в купленном на маркете
# скрипте — это уже чужой код на машине покупателя. Поэтому FFI, запуск процессов и подгрузка
# сторонних нативок скриптам закрыты.
#
# Три опоры, каждая закрывает свой обход:
#   1. sys.addaudithook — хук нельзя снять (в CPython просто нет такого API), и он ловит не только
#      импорт: ctypes.dlopen/dlsym, запуск процессов (в том числе _winapi.CreateProcess — прямой
#      вход в WinAPI мимо subprocess) и запись в реестр;
#   2. чистка sys.modules — запрещённый модуль, загруженный до нас, отдавался бы из кэша, минуя
#      событие import;
#   3. обёртка над _imp.create_dynamic — туда ходит importlib.machinery.ExtensionFileLoader,
#      единственный способ поднять .pyd мимо события import.
#
# Java-сторона закрыта отдельно, в McBridge/ScriptGuard: без неё запрет ctypes ничего не стоил бы,
# память процесса точно так же читается через jimport("sun.misc.Unsafe").


class ScriptSecurityError(RuntimeError):
    """Скрипт попробовал то, что системе скриптов запрещено."""


class ScriptImportBlocked(ImportError):
    """Запрещённый модуль. Наследник ImportError не случайно: чужие библиотеки проверяют FFI
    через `try: import ctypes / except ImportError` и с обычной ошибкой падали бы целиком."""


_DENIED_MODULES = frozenset({
    "ctypes", "_ctypes",              # FFI: LoadLibrary/GetProcAddress → любой WinAPI
    "cffi", "_cffi_backend",          # то же самое другой библиотекой
    "pymem",                          # готовая обёртка над ReadProcessMemory
})

# События CPython (PEP 578), на которых обрываем скрипт.
#
# `subprocess` и `multiprocessing` сами по себе не запрещены — их импортирует stdlib (asyncio
# тянет subprocess при импорте), и заглушка вместо модуля отняла бы у скриптов весь asyncio.
# Запрещён именно запуск: событие приходит до того, как процесс появится.
_DENIED_EVENTS = frozenset({
    "os.system", "os.kill",
    "subprocess.Popen",
    # Реестр: чтение оставляем (в него ходит та же mimetypes), закрыта запись — автозапуск и
    # закрепление в системе.
    "winreg.CreateKey", "winreg.SetValue", "winreg.DeleteKey", "winreg.DeleteValue",
    "winreg.SaveKey", "winreg.LoadKey", "winreg.ConnectRegistry",
    "winreg.DisableReflectionKey", "winreg.EnableReflectionKey",
})

# Семейства целиком — так новые события следующих версий питона закрыты заранее.
_DENIED_EVENT_PREFIXES = ("ctypes.", "os.exec", "os.spawn", "os.fork", "os.posix_spawn",
                          "os.startfile")

# `_winapi` — прямой вход в WinAPI мимо subprocess: CreateProcess оттуда поднимает процесс, не
# трогая ни одного запрещённого модуля. Закрыт весь модуль, кроме работы с файлами и каналами:
# она ничего не запускает, а asyncio на Windows без неё останется без пайпов.
_WINAPI_ALLOWED = frozenset({
    "_winapi.CreateFile", "_winapi.CreatePipe", "_winapi.CreateNamedPipe",
})

# Записывать в папку рантайма скрипту нельзя: она доверенная (нативки грузятся только оттуда), и
# иначе обход выглядел бы так — скачать свой .pyd, положить рядом с python311.dll и импортировать.
# Значение — номера аргументов события, в которых лежат пути. pip сюда не попадает: он и тренер
# нейро-ауры работают отдельным процессом, у них свой интерпретатор без этого хука.
_PATH_EVENTS = {
    "open": (0,),
    "os.rename": (0, 1),
    "os.remove": (0,),
    "os.unlink": (0,),
    "os.truncate": (0,),
    "os.mkdir": (0,),
    "os.rmdir": (0,),
    "os.symlink": (0, 1),
    "os.link": (0, 1),
    "os.chmod": (0,),
    "shutil.copyfile": (0, 1),
    "shutil.copymode": (1,),
    "shutil.copystat": (1,),
    "shutil.move": (0, 1),
    "shutil.rmtree": (0,),
}

_WRITE_MODES = ("w", "a", "x", "+")

_NATIVE_SUFFIXES = (".pyd", ".dll", ".so", ".dylib")

# Рантайм питона (папка runtime/python клиента) — единственное место, откуда нативкам можно
# грузиться: туда кладём мы и pip. Пустой prefix — не наш случай, но проверять тогда нечего.
_RUNTIME_ROOT = os.path.normcase(os.path.realpath(sys.prefix)) if sys.prefix else ""


def _sandbox_root_module(name):
    return str(name or "").split(".", 1)[0]


def _sandbox_denied_module(name):
    return name in _DENIED_MODULES or _sandbox_root_module(name) in _DENIED_MODULES


def _sandbox_inside_runtime(path):
    if not _RUNTIME_ROOT:
        return False
    try:
        real = os.path.normcase(os.path.realpath(str(path)))
    except Exception:
        return False
    return real == _RUNTIME_ROOT or real.startswith(_RUNTIME_ROOT + os.sep)


def _sandbox_trusted_path(path):
    # Нативка «своя», только если лежит в рантайме. Не знаем, где рантайм, — проверять нечем.
    return True if not _RUNTIME_ROOT else _sandbox_inside_runtime(path)


def _sandbox_deny(what, imported=False):
    try:
        print("[Python] скрипт заблокирован: " + what, file=sys.stderr)
    except Exception:
        pass
    raise (ScriptImportBlocked if imported else ScriptSecurityError)("скриптам запрещено: " + what)


def _sandbox_audit(event, args):
    # Хук зовётся на каждое событие процесса, поэтому сначала самая дешёвая проверка.
    if event in _DENIED_EVENTS or event.startswith(_DENIED_EVENT_PREFIXES):
        _sandbox_deny(event)
    elif event.startswith("_winapi.") and event not in _WINAPI_ALLOWED:
        _sandbox_deny(event)
    elif event == "os.add_dll_directory":
        # Каталог в поиске DLL — это подмена библиотеки под чужой импорт, но запретить вызов
        # целиком нельзя: numpy на Windows зовёт его сам, чтобы найти свои dll в numpy.libs.
        # Поэтому пускаем только внутрь рантайма — своя папка скрипта туда не попадает.
        path = args[0] if args else None
        if not path or not _sandbox_inside_runtime(path):
            _sandbox_deny("каталог DLL со стороны: " + str(path))
    elif event == "import":
        name = args[0] if args else ""
        if _sandbox_denied_module(name):
            _sandbox_deny("import " + str(name), imported=True)
        origin = args[1] if len(args) > 1 else None
        if origin and str(origin).lower().endswith(_NATIVE_SUFFIXES) and not _sandbox_trusted_path(origin):
            _sandbox_deny("нативный модуль со стороны: " + str(origin), imported=True)
    else:
        indexes = _PATH_EVENTS.get(event)
        if not indexes:
            return
        if event == "open":
            mode = args[1] if len(args) > 1 else None
            if not mode or not any(ch in str(mode) for ch in _WRITE_MODES):
                return  # чтение файлов не ограничиваем
        for index in indexes:
            if index < len(args) and args[index] and _sandbox_inside_runtime(args[index]):
                _sandbox_deny("запись в папку рантайма: " + str(args[index]))


def _sandbox_install():
    # Уже загруженный модуль отдаётся из кэша, минуя событие import, поэтому запрещённые из кэша
    # выкидываем: следующий импорт пойдёт полным путём и упрётся в хук. Заглушка вместо модуля
    # тут не годится — библиотеки проверяют FFI как `try: import ctypes / except ImportError`,
    # и с заглушкой проверка проходит, а падает потом в чужом коде и без внятной причины.
    for name in _DENIED_MODULES:
        sys.modules.pop(name, None)

    try:
        import _imp as _sandbox_imp
    except ImportError:
        _sandbox_imp = None

    if _sandbox_imp is not None and hasattr(_sandbox_imp, "create_dynamic"):
        _real_create_dynamic = _sandbox_imp.create_dynamic

        def _guarded_create_dynamic(spec, *rest):
            name = getattr(spec, "name", "") or ""
            origin = getattr(spec, "origin", "") or ""
            if _sandbox_denied_module(name):
                _sandbox_deny("нативный модуль " + str(name), imported=True)
            if origin and not _sandbox_trusted_path(origin):
                _sandbox_deny("нативный модуль со стороны: " + str(origin), imported=True)
            return _real_create_dynamic(spec, *rest)

        _sandbox_imp.create_dynamic = _guarded_create_dynamic

    sys.addaudithook(_sandbox_audit)


if not getattr(sys, "__rockstar_sandbox__", False):
    _sandbox_install()
    sys.__rockstar_sandbox__ = True
# ─────────────────────────── Песочница скриптов: конец ────────────────────────────


def _make_color(*a):
    return ColorRGBA(*[float(x) for x in a])


def _setting_target(args):
    # Позволяет первым аргументом сеттинга передать hud-элемент вместо модуля.
    # Распаковываем Python-обёртку _HudElement в её Java-объект (PyHudElement),
    # чтобы Jep выбрал перегрузку конструктора под SettingsContainer.
    if args and isinstance(args[0], (_HudElement, _EspElement)):
        return (args[0].raw,) + tuple(args[1:])
    return args


class _Factory:
    def __init__(self, cls):
        self._cls = cls

    def __call__(self, *args):
        return self._cls(*_setting_target(args))

    def new(self, *args):
        return self._cls(*_setting_target(args))


class _ColorFactory:
    def __call__(self, *a):
        return _make_color(*a)

    def new(self, *a):
        return _make_color(*a)

    def __getattr__(self, name):
        return getattr(ColorRGBA, name)

    def from_hex(self, value):
        return ColorRGBA.fromHex(str(value))

    def fromHex(self, value):
        return self.from_hex(value)

    def from_int(self, value):
        return ColorRGBA.fromInt(int(value))

    def fromInt(self, value):
        return self.from_int(value)

    def from_hsb(self, hue, saturation, brightness):
        return ColorRGBA.fromHSB(float(hue), float(saturation), float(brightness))

    def fromHSB(self, hue, saturation, brightness):
        return self.from_hsb(hue, saturation, brightness)


class _Assets:
    __slots__ = ("_a",)

    def __init__(self, assets):
        self._a = assets

    def image(self, path, name=None):
        if name is None:
            return self._a.image(str(path))
        return self._a.image(str(name), str(path))

    def texture(self, path, name=None):
        return self.image(path, name)

    def dynamic_texture(self, name, width, height):
        return _DynamicTexture(self._a.dynamicTexture(str(name), int(width), int(height)))

    def dynamicTexture(self, name, width, height):
        return self.dynamic_texture(name, width, height)

    def pcm_stream(self, sample_rate, channels=2):
        return self._a.pcmStream(float(sample_rate), int(channels))

    def pcmStream(self, sample_rate, channels=2):
        return self.pcm_stream(sample_rate, channels)

    def svg(self, name, source=None):
        """Свой значок из svg: имя дальше работает в d.icon(...) и ui.icon(...).

        Источником может быть файл рядом со скриптом, ссылка или сам текст svg.
        """
        if source is None:
            name, source = str(name), str(name)
        return str(self._a.svg(str(name), str(source)))

    def icon(self, name, source=None):
        return self.svg(name, source)

    def svg_text(self, name, svg):
        return str(self._a.svgText(str(name), str(svg)))

    def svgText(self, name, svg):
        return self.svg_text(name, svg)

    def has_svg(self, name):
        return bool(self._a.hasSvg(str(name)))

    def hasSvg(self, name):
        return self.has_svg(name)

    def resource(self, path):
        return self._a.resource(str(path))

    def font(self, name, size=12):
        return self._a.font(str(name), float(size))

    def ttf(self, name, path, size=12, charset=None, glyph_size=0, px_range=0):
        return self.ttf_family(name, path).getFont(float(size))

    def ttf_family(self, name, path, charset=None, glyph_size=0, px_range=0):
        return self._a.ttfFamily(str(name), str(path))

    def ttfFamily(self, name, path, charset=None, glyph_size=0, px_range=0):
        return self.ttf_family(name, path)

    def download(self, url, callback=None):
        return self._a.download(str(url), callback)

    def file(self, url, callback=None):
        return self.download(url, callback)

    def scripts_dir(self):
        return self._a.scriptsDir()

    def scriptsDir(self):
        return self.scripts_dir()

    def assets_dir(self):
        return self._a.assetsDir()

    def assetsDir(self):
        return self.assets_dir()


class _DynamicTexture:
    __slots__ = ("_texture",)

    def __init__(self, texture):
        self._texture = texture

    @property
    def identifier(self):
        return self._texture.identifier()

    @property
    def width(self):
        return int(self._texture.width())

    @property
    def height(self):
        return int(self._texture.height())

    def update(self, rgba):
        self._texture.update(rgba)

    def close(self):
        self._texture.close()


class _Shader:
    __slots__ = ("_s",)

    def __init__(self, shader):
        self._s = shader

    @property
    def name(self):
        return self._s.name()

    @property
    def valid(self):
        return bool(self._s.valid())

    def set(self, name, *values):
        if len(values) == 1 and isinstance(values[0], (list, tuple)):
            values = tuple(values[0])
        count = len(values)
        if count == 1:
            self._s.set(str(name), float(values[0]))
        elif count == 2:
            self._s.set(str(name), float(values[0]), float(values[1]))
        elif count == 3:
            self._s.set(str(name), float(values[0]), float(values[1]), float(values[2]))
        elif count == 4:
            self._s.set(str(name), float(values[0]), float(values[1]), float(values[2]), float(values[3]))
        else:
            raise ValueError("uniform takes 1 to 4 numbers")
        return self

    def set_int(self, name, value):
        self._s.setInt(str(name), int(value))
        return self

    def setInt(self, name, value):
        return self.set_int(name, value)

    def color(self, value, name="Color"):
        self._s.setColor(str(name), value)
        return self

    def matrix(self, name, value):
        self._s.setMatrix(str(name), _unwrap(value))
        return self

    def texture(self, unit, value=None):
        self._s.texture(int(unit), _unwrap(getattr(value, "_texture", value)))
        return self

    def rect(self, ctx, x, y, width, height):
        self._s.rect(_unwrap(ctx), float(x), float(y), float(width), float(height))
        return self

    def fullscreen(self, event):
        self._s.fullscreen(_unwrap(event))
        return self

    def quad3d(self, event, pos, width, height=None, mode="billboard", additive=False, depth=False):
        if not _is_point(pos):
            pos = _unwrap(pos).getPos()
            pos = (pos.x, pos.y, pos.z)
        self._s.quad3d(_unwrap(event), float(pos[0]), float(pos[1]), float(pos[2]),
                       float(width), float(width if height is None else height),
                       str(mode), bool(additive), bool(depth))
        return self

    def quad_3d(self, event, pos, width, height=None, mode="billboard", additive=False, depth=False):
        return self.quad3d(event, pos, width, height, mode, additive, depth)

    def mesh3d(self, event, vertices, origin=(0, 0, 0), mode="triangles",
               colors=False, additive=False, depth=True, cull=False):
        self._s.mesh3d(_unwrap(event), _pack_floats(_flatten_vertices(vertices)),
                       float(origin[0]), float(origin[1]), float(origin[2]),
                       str(mode), bool(colors), bool(additive), bool(depth), bool(cull))
        return self

    def mesh_3d(self, event, vertices, origin=(0, 0, 0), mode="triangles",
                colors=False, additive=False, depth=True, cull=False):
        return self.mesh3d(event, vertices, origin, mode, colors, additive, depth, cull)

    def mesh2d(self, ctx, vertices, mode="triangles", colors=False):
        # На экране вершина это x, y[, u, v][, r, g, b, a]: z всегда ноль, его дописываем сами.
        self._s.mesh2d(_unwrap(ctx), _pack_floats(_flatten2d(vertices, colors)), str(mode), bool(colors))
        return self

    def mesh_2d(self, ctx, vertices, mode="triangles", colors=False):
        return self.mesh2d(ctx, vertices, mode, colors)

    def dispose(self):
        self._s.dispose()

    def close(self):
        self.dispose()


class _ShaderApi:
    __slots__ = ("_f",)

    def __init__(self, factory):
        self._f = factory

    def create(self, name, fragment=None, vertex=None):
        if fragment is None:
            raise ValueError("shader needs a fragment source")
        return _Shader(self._f.create(str(name), None if vertex is None else str(vertex), str(fragment)))

    def __call__(self, name, fragment=None, vertex=None):
        return self.create(name, fragment, vertex)

    def load(self, name, fragment, vertex=None):
        return _Shader(self._f.load(str(name), None if vertex is None else str(vertex), str(fragment)))

    def from_file(self, name, fragment, vertex=None):
        return self.load(name, fragment, vertex)

    def fromFile(self, name, fragment, vertex=None):
        return self.load(name, fragment, vertex)


class _Sound:
    """Звук скрипта: wav, mp3 или ogg из папки скрипта либо по ссылке."""

    __slots__ = ("_s",)

    def __init__(self, sound):
        self._s = sound

    @property
    def path(self):
        return str(self._s.path())

    @property
    def playing(self):
        return bool(self._s.playing())

    @property
    def paused(self):
        return bool(self._s.paused())

    @property
    def position(self):
        return float(self._s.position())

    @property
    def duration(self):
        return float(self._s.duration())

    @property
    def looping(self):
        return bool(self._s.looping())

    def play(self):
        self._s.play()
        return self

    def stop(self):
        self._s.stop()
        return self

    def pause(self):
        self._s.pause()
        return self

    def resume(self):
        self._s.resume()
        return self

    def toggle(self):
        return self.resume() if self.paused else self.pause()

    def volume(self, value=None):
        if value is None:
            return float(self._s.volume())
        self._s.volume(float(value))
        return self

    def speed(self, value=None):
        if value is None:
            return float(self._s.speed())
        self._s.speed(float(value))
        return self

    def pitch(self, value=None):
        return self.speed(value)

    def loop(self, value=True):
        self._s.loop(bool(value))
        return self

    def category(self, name=None):
        if name is None:
            return str(self._s.category())
        self._s.category(str(name))
        return self

    def on_end(self, callback):
        self._s.onEnd(callback)
        return self

    def onEnd(self, callback):
        return self.on_end(callback)


class _SoundApi:
    __slots__ = ("_f",)

    def __init__(self, factory):
        self._f = factory

    @staticmethod
    def _setup(raw, volume, speed, loop, category, on_end):
        if volume is not None:
            raw.volume(float(volume))
        if speed is not None:
            raw.speed(float(speed))
        if loop is not None:
            raw.loop(bool(loop))
        if category is not None:
            raw.category(str(category))
        if on_end is not None:
            raw.onEnd(on_end)
        return raw

    def play(self, path, volume=None, speed=None, loop=None, category=None, overlap=False, on_end=None):
        raw = self._f.create(str(path)) if overlap else self._f.get(str(path))
        self._setup(raw, volume, speed, loop, category, on_end)
        raw.play()
        return _Sound(raw)

    def __call__(self, path, **kwargs):
        return self.play(path, **kwargs)

    def once(self, path, **kwargs):
        kwargs["overlap"] = True
        return self.play(path, **kwargs)

    def loop(self, path, **kwargs):
        kwargs["loop"] = True
        return self.play(path, **kwargs)

    def load(self, path, volume=None, speed=None, loop=None, category=None, on_end=None):
        raw = self._f.get(str(path))
        self._setup(raw, volume, speed, loop, category, on_end)
        return _Sound(raw)

    def stop(self, path=None):
        if path is None:
            self._f.stopAll()
            return None
        return _Sound(self._f.stop(str(path)))

    def stop_all(self):
        self._f.stopAll()

    def stopAll(self):
        self._f.stopAll()

    def playing(self):
        return int(self._f.playing())


def _flatten_vertices(vertices):
    """Список вершин-кортежей в один плоский список; готовые байты и плоский список отдаём как есть."""
    if isinstance(vertices, (bytes, bytearray)):
        return vertices

    flat = list(vertices)
    if flat and isinstance(flat[0], (list, tuple)):
        out = []
        for vertex in flat:
            out.extend(vertex)
        return out
    return flat


def _flatten2d(vertices, colors):
    """Плоский список 2D-вершин в формат вершинного буфера: между y и u вставляется z = 0."""
    flat = _flatten_vertices(vertices)
    if isinstance(flat, (bytes, bytearray)):
        return flat

    stride = 8 if colors else 4
    out = []
    for i in range(0, len(flat) - stride + 1, stride):
        out.extend((flat[i], flat[i + 1], 0.0))
        out.extend(flat[i + 2:i + stride])
    return out


def _is_point(value):
    return isinstance(value, (list, tuple)) and len(value) >= 3


def _pack_floats(values):
    # Пачки фигур уходят в Java одним бинарным куском: иначе Jep боксит каждое число
    # в java.lang.Double, и на сотнях частиц это стоит дороже самой отрисовки.
    if isinstance(values, (bytes, bytearray)):
        return values
    return _array.array("f", values).tobytes()


_TEXT_FACING = {
    "camera": 1, "billboard": 1, "full": 1,
    "y": 2, "yaw": 2, "horizon": 2, "upright": 2,
    "fixed": 0, "world": 0, "flat": 0, "none": 0,
}
_TEXT_ALIGN = {"center": 0, "middle": 0, "left": 1, "right": 2}


def _rgba(color, default=(255.0, 255.0, 255.0, 255.0)):
    if color is None:
        return default
    if isinstance(color, str):
        color = ColorRGBA.fromHex(color)
    elif isinstance(color, (list, tuple)):
        parts = [float(v) for v in color[:4]]
        while len(parts) < 4:
            parts.append(255.0)
        return tuple(parts)
    else:
        color = _unwrap(color)
    # Один вызов через мост вместо четырёх геттеров: на пачке из сотни надписей
    # разбор цветов стоил больше, чем сама отрисовка
    packed = int(color.getRGB())
    return (float((packed >> 16) & 0xFF), float((packed >> 8) & 0xFF),
            float(packed & 0xFF), float((packed >> 24) & 0xFF))


def _text_point(pos):
    # Точка или сущность: у сущности берём середину, как у билборда
    if _is_point(pos):
        return float(pos[0]), float(pos[1]), float(pos[2])
    entity = _unwrap(pos)
    point = entity.getPos()
    return float(point.x), float(point.y) + float(entity.getHeight()) * 0.5, float(point.z)


class _DepthScope:
    """Область действия render3d.depth(): на выходе режим возвращается к прежнему."""
    __slots__ = ("_r", "_previous")

    def __init__(self, renderer, previous):
        self._r = renderer
        self._previous = previous

    def __enter__(self):
        return self._r

    def __exit__(self, kind, value, trace):
        self._r._depth = self._previous
        return False


class _Render3D:
    __slots__ = ("_r", "_world", "_depth")

    def __init__(self, renderer, world):
        self._r = renderer
        self._world = world
        self._depth = False

    def _color(self, color):
        return ColorRGBA.WHITE if color is None else color

    def _through(self, through):
        """Считаться ли с блоками: у вызова свой флаг, а без него берётся режим скрипта."""
        return not self._depth if through is None else bool(through)

    def depth(self, on=True):
        """Учитывать блоки у всего, что скрипт рисует дальше: за стеной ничего видно не будет.

        Режим свой у каждого скрипта и держится до следующего вызова, так что ставить его
        в каждый метод не нужно. Возвращает область: `with render3d.depth():` вернёт
        прежнее значение на выходе. Отдельному вызову флаг `through` всё так же важнее режима."""
        previous = self._depth
        self._depth = bool(on)
        return _DepthScope(self, previous)

    def depth_enabled(self):
        """Стоит ли сейчас режим «считаться с блоками»."""
        return self._depth

    def depthEnabled(self):
        return self.depth_enabled()

    def through_walls(self, on=True):
        """То же самое наоборот: True — рисовать сквозь блоки, как по умолчанию."""
        return self.depth(not on)

    def throughWalls(self, on=True):
        return self.through_walls(on)

    def line(self, event, start, end=None, color=None, through=None):
        if end is None:
            if not isinstance(start, (list, tuple)) or len(start) < 6:
                raise ValueError("line needs (x1,y1,z1,x2,y2,z2) or start/end points")
            x1, y1, z1, x2, y2, z2 = start[:6]
        else:
            if not (_is_point(start) and _is_point(end)):
                raise ValueError("line start/end must be 3D points")
            x1, y1, z1 = start[:3]
            x2, y2, z2 = end[:3]
        self._r.line(_unwrap(event), float(x1), float(y1), float(z1),
                     float(x2), float(y2), float(z2), self._color(color), self._through(through))

    def marker(self, event, pos, size=0.18, color=None, through=None):
        if not _is_point(pos):
            pos = _unwrap(pos).getPos()
            pos = (pos.x, pos.y, pos.z)
        self._r.marker(_unwrap(event), float(pos[0]), float(pos[1]), float(pos[2]),
                       float(size), self._color(color), self._through(through))

    def box(self, event, target, color=None, through=None):
        self._r.box(_unwrap(event), _unwrap(target), self._color(color), self._through(through))

    def box_gradient(self, event, target, bottom_color, top_color, through=None):
        self._r.boxGradient(_unwrap(event), _unwrap(target), bottom_color, top_color, self._through(through))

    def boxGradient(self, event, target, bottom_color, top_color, through=None):
        return self.box_gradient(event, target, bottom_color, top_color, through)

    def filled_box(self, event, target, color=None, through=None):
        self._r.filledBox(_unwrap(event), _unwrap(target), self._color(color), self._through(through))

    def filledBox(self, event, target, color=None, through=None):
        return self.filled_box(event, target, color, through)

    def fill_box(self, event, target, color=None, through=None):
        return self.filled_box(event, target, color, through)

    def filled_box_gradient(self, event, target, bottom_color, top_color, through=None):
        self._r.filledBoxGradient(_unwrap(event), _unwrap(target), bottom_color, top_color, self._through(through))

    def filledBoxGradient(self, event, target, bottom_color, top_color, through=None):
        return self.filled_box_gradient(event, target, bottom_color, top_color, through)

    def glowing_box(self, event, target, color=None, through=None):
        self._r.glowingBox(_unwrap(event), _unwrap(target), self._color(color), self._through(through))

    def glowingBox(self, event, target, color=None, through=None):
        return self.glowing_box(event, target, color, through)

    def box_at(self, event, x, y, z, width, height, depth, color=None, through=None):
        self._r.boxAt(_unwrap(event), float(x), float(y), float(z),
                      float(width), float(height), float(depth), self._color(color), self._through(through))

    def boxAt(self, event, x, y, z, width, height, depth, color=None, through=None):
        return self.box_at(event, x, y, z, width, height, depth, color, through)

    def filled_box_at(self, event, x, y, z, width, height, depth, color=None, through=None):
        self._r.filledBoxAt(_unwrap(event), float(x), float(y), float(z),
                            float(width), float(height), float(depth), self._color(color), self._through(through))

    def filledBoxAt(self, event, x, y, z, width, height, depth, color=None, through=None):
        return self.filled_box_at(event, x, y, z, width, height, depth, color, through)

    def ring(self, event, target, radius=0.8, y_offset=0.05, segments=48, color=None, through=None):
        self._r.ring(_unwrap(event), _unwrap(target), float(radius), float(y_offset), int(segments),
                     self._color(color), self._through(through))

    def target(self, event, target=None, color=None, through=None):
        target = self._world.target() if target is None else target
        if target is None:
            return
        self._r.target(_unwrap(event), _unwrap(target), self._color(color), self._through(through))

    def target_esp(self, event, target=None, color=None, through=None):
        return self.target(event, target, color, through)

    def targetEsp(self, event, target=None, color=None, through=None):
        return self.target_esp(event, target, color, through)

    def billboard(self, event, texture, pos, width=1.0, height=None, color=None, roll=0.0, additive=False,
                  through=None):
        if height is None:
            height = width
        if not _is_point(pos):
            entity = _unwrap(pos)
            p = entity.getPos()
            pos = (p.x, p.y + entity.getHeight() * 0.5, p.z)
        self._r.billboard(_unwrap(event), _unwrap(texture), float(pos[0]), float(pos[1]), float(pos[2]),
                          float(width), float(height), float(roll), self._color(color),
                          bool(additive), self._through(through))

    def effect(self, event, effect, pos, size=0.5, color=None, roll=0.0, additive=False, through=None):
        """Иконка эффекта в мире: точкой или над существом, как билборд."""
        x, y, z = _text_point(pos)
        self._r.effect(_unwrap(event), _effect_arg(effect), x, y, z,
                       float(size), float(roll), self._color(color), bool(additive), self._through(through))

    def billboard_texture(self, event, texture, pos, width=1.0, height=None, color=None, roll=0.0, additive=False,
                          through=None):
        return self.billboard(event, texture, pos, width, height, color, roll, additive, through)

    def billboardTexture(self, event, texture, pos, width=1.0, height=None, color=None, roll=0.0, additive=False,
                         through=None):
        return self.billboard_texture(event, texture, pos, width, height, color, roll, additive, through)

    def billboards(self, event, texture, particles, additive=True, through=None):
        """Пачка частиц одним вызовом: плоский список [x, y, z, size, r, g, b, a] на каждую."""
        if not particles:
            return
        self._r.billboards(_unwrap(event), _unwrap(texture), _pack_floats(particles),
                           bool(additive), self._through(through))

    def billboard_batch(self, event, texture, particles, additive=True, through=None):
        return self.billboards(event, texture, particles, additive, through)

    def billboardBatch(self, event, texture, particles, additive=True, through=None):
        return self.billboards(event, texture, particles, additive, through)

    def lines(self, event, segments, additive=True, through=None):
        """Пачка линий одним вызовом: плоский список [x1, y1, z1, x2, y2, z2, r, g, b, a] на каждую."""
        if not segments:
            return
        self._r.lines(_unwrap(event), _pack_floats(segments), bool(additive), self._through(through))

    def line_batch(self, event, segments, additive=True, through=None):
        return self.lines(event, segments, additive, through)

    def lineBatch(self, event, segments, additive=True, through=None):
        return self.lines(event, segments, additive, through)

    def _font(self, font):
        return None if font is None else (font if isinstance(font, str) else _unwrap(font))

    def _facing(self, facing):
        if facing is None or facing is True:
            return 1
        if facing is False:
            return 0
        if isinstance(facing, str):
            return _TEXT_FACING.get(facing.lower(), 1)
        return int(facing)

    def _align(self, align):
        if isinstance(align, str):
            return _TEXT_ALIGN.get(align.lower(), 0)
        return int(align)

    def _pack_texts(self, items, size, color, yaw, pitch):
        """Пачка надписей в два куска: строки списком, всё остальное — плоскими числами."""
        strings = []
        params = []
        for item in items:
            if isinstance(item, dict):
                value = item.get("text", item.get("value", ""))
                point = item.get("pos", item.get("position"))
                if point is None:
                    point = (item.get("x", 0.0), item.get("y", 0.0), item.get("z", 0.0))
                item_size = item.get("size", size)
                item_color = item.get("color", color)
                item_yaw = item.get("yaw", yaw)
                item_pitch = item.get("pitch", pitch)
                roll = item.get("roll", 0.0)
            elif isinstance(item, (list, tuple)):
                if len(item) < 2:
                    raise ValueError("надпись описывается как (текст, точка[, размер, цвет, наклон])")
                value = item[0]
                point = item[1]
                item_size = item[2] if len(item) > 2 else size
                item_color = item[3] if len(item) > 3 else color
                roll = item[4] if len(item) > 4 else 0.0
                item_yaw = item[5] if len(item) > 5 else yaw
                item_pitch = item[6] if len(item) > 6 else pitch
            else:
                raise ValueError("надпись описывается кортежем или словарём, а не " + type(item).__name__)

            value = str(value)
            if not value:
                continue
            x, y, z = _text_point(point)
            red, green, blue, alpha = _rgba(item_color)
            strings.append(value)
            params.extend((x, y, z, float(item_size), red, green, blue, alpha,
                           float(item_yaw), float(item_pitch), float(roll)))
        return strings, params

    def texts(self, event, items, size=0.25, color=None, font=None,
              outline=None, outline_width=0.06, shadow=None, shadow_offset=None,
              facing=True, yaw=0.0, pitch=0.0, align="center", through=None, additive=False,
              outline_steps=4):
        """Пачка надписей в мире одним draw call.

        У каждой своя точка, размер, цвет и свои углы: yaw, pitch и roll задаются у элемента,
        а параметры вызова остаются значением по умолчанию для тех, кто их не задал."""
        if not items:
            return
        strings, params = self._pack_texts(items, size, color, yaw, pitch)
        if not strings:
            return
        shadow_x, shadow_y = (0.05, 0.07) if shadow_offset is None else (
            float(shadow_offset[0]), float(shadow_offset[1]))
        self._r.texts(_unwrap(event), strings, _pack_floats(params), self._font(font),
                      _unwrap(outline), float(outline_width), int(outline_steps),
                      _unwrap(shadow), shadow_x, shadow_y,
                      self._facing(facing), self._align(align),
                      self._through(through), bool(additive))

    def text_batch(self, event, items, size=0.25, color=None, font=None,
                   outline=None, outline_width=0.06, shadow=None, shadow_offset=None,
                   facing=True, yaw=0.0, pitch=0.0, align="center", through=None, additive=False,
                   outline_steps=4):
        return self.texts(event, items, size, color, font, outline, outline_width, shadow, shadow_offset,
                          facing, yaw, pitch, align, through, additive, outline_steps)

    def text(self, event, text, pos, size=0.25, color=None, font=None,
             outline=None, outline_width=0.06, shadow=None, shadow_offset=None,
             facing=True, yaw=0.0, pitch=0.0, roll=0.0, align="center", through=None, additive=False,
             outline_steps=4):
        """Надпись в точке мира: size — высота заглавных букв в блоках."""
        self.texts(event, [(text, pos, size, color, roll, yaw, pitch)], size, color, font,
                   outline, outline_width, shadow, shadow_offset,
                   facing, yaw, pitch, align, through, additive, outline_steps)

    def text_width(self, text, size=0.25, font=None):
        """Ширина надписи в блоках."""
        return float(self._r.textWidth(str(text), float(size), self._font(font)))

    def textWidth(self, text, size=0.25, font=None):
        return self.text_width(text, size, font)

    def text_height(self, size=0.25, font=None):
        """Шаг между строками многострочной надписи в блоках."""
        return float(self._r.lineHeight(float(size), self._font(font)))

    def line_height(self, size=0.25, font=None):
        return self.text_height(size, font)

    def lineHeight(self, size=0.25, font=None):
        return self.text_height(size, font)

    def letters(self, text, size=0.25, font=None):
        """Строка по буквам: список (символ, смещение слева в блоках, ширина в блоках)."""
        # list(...) снимает java-массив: у обёртки Jep нет части протокола последовательности
        flat = list(self._r.letters(str(text), float(size), self._font(font)))
        return [(chr(int(flat[index])), float(flat[index + 1]), float(flat[index + 2]))
                for index in range(0, len(flat), 3)]

    def image(self, event, texture, pos, width=1.0, height=None, color=None, roll=0.0, additive=False):
        return self.billboard(event, texture, pos, width, height, color, roll, additive)

    def texture(self, event, texture, pos, width=1.0, height=None, color=None, roll=0.0, additive=False):
        return self.billboard(event, texture, pos, width, height, color, roll, additive)


class _Border:
    def __init__(self, client):
        self._c = client

    def _mk(self, a):
        if len(a) == 1:
            return self._c.border(float(a[0]))
        return self._c.border4(float(a[0]), float(a[1]), float(a[2]), float(a[3]))

    def __call__(self, *a):
        return self._mk(a)

    def new(self, *a):
        return self._mk(a)


class _EffectEvent:
    """Событие эффекта: сам эффект приходит той же обёрткой, что и в effects.list().

    Без этого getEffect() отдавал бы голый java-объект, и у одного и того же эффекта
    в событии были бы методы (eff.level()), а в списке — свойства (eff.level).
    """
    __slots__ = ("_e", "_wrapped")

    def __init__(self, event):
        self._e = event if isinstance(event, _J) else _wrap(event)
        self._wrapped = None

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_e"), name)

    def getEffect(self):
        if self._wrapped is None:
            self._wrapped = _Effect(_unwrap(self._e.getEffect()))
        return self._wrapped

    @property
    def effect(self):
        return self.getEffect()

    def __str__(self):
        return str(self._e)

    def __repr__(self):
        return "<effect event %s>" % self.getEffect().id


# Событиям из этого списка нужна своя обёртка: всё остальное уезжает обычным _wrap
_EVENT_WRAPPERS = {
    "effect_added": _EffectEvent,
    "effect_removed": _EffectEvent,
}


def _event_callback(fn, name=None):
    """Событие уходит в скрипт уже в обёртке: всё, что оно вернёт (сущность, пакет, позиция),
    приходит обёрнутым само, и звать wrap() руками не нужно. Ручной wrap() в старых скриптах
    ничего не ломает — обёртка идемпотентна."""
    wrapper = _EVENT_WRAPPERS.get(str(name).lower(), _wrap)

    def handler(event):
        return fn(wrapper(event))

    return handler


class _EventHandle:
    def __init__(self, bridge, name):
        self._bridge = bridge
        self._name = name

    def __call__(self, fn):
        self._bridge.register(self._name, _event_callback(fn, self._name))
        return fn

    def on(self, fn):
        return self(fn)

    def set(self, fn):
        return self(fn)


class _Events:
    def __init__(self, bridge):
        object.__setattr__(self, "_b", bridge)

    def __getattr__(self, name):
        return _EventHandle(object.__getattribute__(self, "_b"), name)

    def getEvent(self, name):
        return _EventHandle(object.__getattribute__(self, "_b"), name)


class _ClientMessages:
    __slots__ = ("_c",)

    def __init__(self, client):
        self._c = client

    def __call__(self, text):
        self.info(text)

    def info(self, text):
        self._c.msg(str(text))

    def msg(self, text):
        self.info(text)

    def warn(self, text):
        self._c.warn(str(text))

    def error(self, text):
        self._c.error(str(text))

    def overlay(self, text):
        self._c.overlay(str(text))


class _ClientModules:
    __slots__ = ("_c",)

    def __init__(self, client):
        self._c = client

    def __call__(self):
        return self.all()

    def all(self):
        return _java_list(self._c.modules())

    def list(self):
        return self.all()

    def find(self, name):
        return self._c.find(str(name))

    def get(self, name):
        return self.find(name)

    def require(self, name):
        module = self.find(name)
        if module is None:
            raise ValueError("модуль не найден: " + str(name))
        return module

    def setting(self, module_name, setting_name):
        return self._c.find(str(module_name), str(setting_name))

    def enabled(self, name):
        module = self.find(name)
        return False if module is None else bool(module.isEnabled())

    def enable(self, name):
        module = self.require(name)
        module.setEnabled(True)
        return module

    def disable(self, name):
        module = self.require(name)
        module.setEnabled(False)
        return module

    def toggle(self, name):
        module = self.require(name)
        module.toggle()
        return module


class _ClientSettings:
    __slots__ = ("_c",)

    def __init__(self, client):
        self._c = client

    def find(self, module_name, setting_name):
        return self._c.find(str(module_name), str(setting_name))

    def get(self, module_name, setting_name):
        return self.find(module_name, setting_name)

    def checkbox(self, *args):
        return PyBooleanSetting(*_setting_target(args))

    def Checkbox(self, *args):
        return self.checkbox(*args)

    def slider(self, *args):
        return PySliderSetting(*_setting_target(args))

    def Slider(self, *args):
        return self.slider(*args)

    def mode(self, *args):
        return PyModeSetting(*_setting_target(args))

    def Mode(self, *args):
        return self.mode(*args)

    def select(self, *args):
        return PySelectSetting(*_setting_target(args))

    def Select(self, *args):
        return self.select(*args)

    def button(self, *args):
        return PyButtonSetting(*_setting_target(args))

    def Button(self, *args):
        return self.button(*args)

    def range(self, *args):
        return PyRangeSetting(*_setting_target(args))

    def Range(self, *args):
        return self.range(*args)

    def color(self, *args):
        return PyColorSetting(*_setting_target(args))

    def ColorSetting(self, *args):
        return self.color(*args)

    def bind(self, *args):
        return PyBindSetting(*_setting_target(args))

    def Bind(self, *args):
        return self.bind(*args)

    def key(self, *args):
        return self.bind(*args)

    def text(self, *args):
        return PyTextSetting(*_setting_target(args))

    def Text(self, *args):
        return self.text(*args)

    def string(self, *args):
        return self.text(*args)

    def time(self, *args):
        return PyTimeSetting(*_setting_target(args))

    def Time(self, *args):
        return self.time(*args)

    def info(self, *args):
        return PyInfoSetting(*_setting_target(args))

    def Info(self, *args):
        return self.info(*args)

    def label(self, *args):
        return self.info(*args)

    def gradient(self, *args):
        return PyGradientSetting(*_setting_target(args))

    def Gradient(self, *args):
        return self.gradient(*args)

    def position(self, *args):
        return PyPositionSetting(*_setting_target(args))

    def Position(self, *args):
        return self.position(*args)

    def bezier(self, *args):
        return PyBezierSetting(*_setting_target(args))

    def Bezier(self, *args):
        return self.bezier(*args)

    def curve(self, *args):
        return self.bezier(*args)

    def blocks(self, *args):
        return PyBlockSetting(*_setting_target(args))

    def Blocks(self, *args):
        return self.blocks(*args)


class _ClientFonts:
    __slots__ = ("_c", "_gv")

    def __init__(self, client, globals_vars):
        self._c = client
        self._gv = globals_vars

    def __call__(self, weight, size):
        return self.get(weight, size)

    def get(self, weight, size):
        return self._gv.font(str(weight), float(size))

    def width(self, weight, size, text):
        return self._c.fontWidth(str(weight), float(size), str(text))

    def height(self, weight, size):
        return self._c.fontHeight(str(weight), float(size))


class _ClientUi:
    __slots__ = ("_c", "_border")

    def __init__(self, client, border):
        self._c = client
        self._border = border

    def cursor(self, cursor_type):
        self._c.cursor(str(cursor_type))

    def menu_opened(self):
        return bool(self._c.menu_opened())

    def menu_open(self):
        return self.menu_opened()

    def border(self, *args):
        return self._border(*args)

    def border4(self, tl, tr, br, bl):
        return self._c.border4(float(tl), float(tr), float(br), float(bl))


class _ClientPaths:
    __slots__ = ("_c",)

    def __init__(self, client):
        self._c = client

    def root(self):
        return self._c.gameDir()

    def game_dir(self):
        return self.root()

    def scripts(self):
        return os.path.join(self.root(), "scripts")

    def runtime(self):
        return os.path.join(self.root(), "runtime")


def _positional_count(fn):
    try:
        signature = inspect.signature(fn)
        params = list(signature.parameters.values())
    except Exception:
        return None

    for param in params:
        if param.kind == param.VAR_POSITIONAL:
            return None

    return len([
        param for param in params
        if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
    ])


class _HudDrawContext:
    __slots__ = ("context", "element", "_fonts", "_border")

    def __init__(self, context, element, fonts, border):
        self.context = context
        self.element = element
        self._fonts = fonts
        self._border = border

    @property
    def x(self):
        return float(self.element.getX())

    @property
    def y(self):
        return float(self.element.getY())

    @property
    def width(self):
        return float(self.element.getWidth())

    @property
    def w(self):
        return self.width

    @property
    def height(self):
        return float(self.element.getHeight())

    @property
    def h(self):
        return self.height

    @property
    def alpha(self):
        return float(self.element.renderAlpha())

    @property
    def drag(self):
        return float(self.element.dragAlpha())

    @property
    def mouse_x(self):
        return int(self.context.getMouseX())

    @property
    def mouse_y(self):
        return int(self.context.getMouseY())

    @property
    def delta(self):
        return float(self.context.getDelta())

    def _xy(self, x, y):
        return self.x + float(x), self.y + float(y)

    def _wh(self, width, height):
        return (
            self.width if width is None else float(width),
            self.height if height is None else float(height),
        )

    def font(self, weight="medium", size=8):
        return self._fonts.get(weight, size)

    def size(self, width, height):
        self.element.size(float(width), float(height))
        return self

    def client_rect(self, x=0, y=0, width=None, height=None, alpha=None,
                    drag=None, squircle=3, radius=None, outline=False):
        px, py = self._xy(x, y)
        w, h = self._wh(width, height)
        a = self.alpha if alpha is None else float(alpha)
        d = self.drag if drag is None else float(drag)
        if radius is None and not outline:
            self.context.drawClientRect(px, py, w, h, a, d, float(squircle))
        elif outline:
            self.context.drawClientRect(px, py, w, h, a, d, float(squircle),
                                        float(7 if radius is None else radius), True)
        else:
            self.context.drawClientRect(px, py, w, h, a, d, float(squircle), float(radius))
        return self

    def rect(self, x=0, y=0, width=None, height=None, color=None):
        px, py = self._xy(x, y)
        w, h = self._wh(width, height)
        self.context.drawRect(px, py, w, h, ColorRGBA.WHITE if color is None else color)
        return self

    def shader(self, shader, x=0, y=0, width=None, height=None):
        px, py = self._xy(x, y)
        w, h = self._wh(width, height)
        shader.rect(self.context, px, py, w, h)
        return self

    def rounded_rect(self, x=0, y=0, width=None, height=None, radius=6, color=None):
        px, py = self._xy(x, y)
        w, h = self._wh(width, height)
        br = self._border(radius) if isinstance(radius, (int, float)) else radius
        self.context.drawRoundedRect(px, py, w, h, br, ColorRGBA.WHITE if color is None else color)
        return self

    def border(self, x=0, y=0, width=None, height=None, radius=6, thickness=1, color=None):
        px, py = self._xy(x, y)
        w, h = self._wh(width, height)
        br = self._border(radius) if isinstance(radius, (int, float)) else radius
        self.context.drawRoundedBorder(px, py, w, h, float(thickness), br,
                                       ColorRGBA.WHITE if color is None else color)
        return self

    def shadow(self, x=0, y=0, width=None, height=None, radius=6, softness=12, color=None):
        px, py = self._xy(x, y)
        w, h = self._wh(width, height)
        br = self._border(radius) if isinstance(radius, (int, float)) else radius
        self.context.drawShadow(px, py, w, h, float(softness), br,
                                ColorRGBA.BLACK.withAlpha(120) if color is None else color)
        return self

    def text(self, value, x=0, y=0, size=7, weight="medium", color=None, font=None,
             outline=None, outline_width=1, outline_steps=0):
        px, py = self._xy(x, y)
        f = font or self.font(weight, size)
        fill = ColorRGBA.WHITE if color is None else color
        if outline is None:
            self.context.drawText(f, str(value), px, py, fill)
        else:
            self.context.drawTextWithOutline(f, str(value), px, py, fill, outline, float(outline_width),
                                             int(outline_steps))
        return self

    def centered_text(self, value, x=0, y=0, size=7, weight="medium", color=None, font=None,
                      outline=None, outline_width=1, outline_steps=0):
        px, py = self._xy(x, y)
        f = font or self.font(weight, size)
        fill = ColorRGBA.WHITE if color is None else color
        if outline is None:
            self.context.drawCenteredText(f, str(value), px, py, fill)
        else:
            self.context.drawCenteredTextWithOutline(f, str(value), px, py, fill, outline, float(outline_width),
                                                     int(outline_steps))
        return self

    def right_text(self, value, x=0, y=0, size=7, weight="medium", color=None, font=None,
                   outline=None, outline_width=1, outline_steps=0):
        px, py = self._xy(x, y)
        f = font or self.font(weight, size)
        fill = ColorRGBA.WHITE if color is None else color
        if outline is None:
            self.context.drawRightText(f, str(value), px, py, fill)
        else:
            self.context.drawRightTextWithOutline(f, str(value), px, py, fill, outline, float(outline_width),
                                                  int(outline_steps))
        return self

    def icon(self, name, x=0, y=0, size=8, color=None):
        px, py = self._xy(x, y)
        self.context.drawIcon(str(name), px, py, float(size), ColorRGBA.WHITE if color is None else color)
        return self

    def item(self, stack, x=0, y=0, size=1):
        px, py = self._xy(x, y)
        self.context.drawItem(_unwrap(stack), px, py, float(size))
        return self

    def effect(self, effect, x=0, y=0, size=10, color=None):
        """Ванильная иконка эффекта: сам эффект или его id строкой."""
        px, py = self._xy(x, y)
        self.context.drawEffect(_effect_arg(effect), px, py, float(size),
                                ColorRGBA.WHITE if color is None else color)
        return self

    def image(self, texture, x=0, y=0, width=None, height=None, radius=0, color=None):
        """Картинка от угла элемента: ассет, обложка трека, аватарка профиля."""
        px, py = self._xy(x, y)
        w, h = self._wh(width, height)
        tint = ColorRGBA.WHITE if color is None else color
        if radius:
            br = self._border(radius) if isinstance(radius, (int, float)) else radius
            self.context.drawRoundedTexture(_unwrap(texture), px, py, w, h, br, tint)
        else:
            self.context.drawTexture(_unwrap(texture), px, py, w, h, tint)
        return self

    def texture(self, texture, x=0, y=0, width=None, height=None, radius=0, color=None):
        return self.image(texture, x, y, width, height, radius, color)

    def raw(self):
        return self.context


_HUD_CELL_KINDS = ("icon", "effect", "dot", "item")


def _hud_cell(cell):
    """Ячейка строки: текст, значок, иконка эффекта или точка статуса."""
    if isinstance(cell, dict):
        out = {}
        for key in ("text", "icon"):
            value = cell.get(key)
            if value is not None:
                out[key] = str(value)
        if "item" in cell:
            item = cell.get("item")
            # пустая строка это слот без предмета: ячейка нарисуется, а предмета в ней не будет
            out["item"] = "" if item is None else (item if isinstance(item, str) else _unwrap(item))
        for key in ("count", "bar"):
            if cell.get(key) is False:
                out[key] = False
        effect = cell.get("effect")
        if effect is not None:
            out["effect"] = _effect_arg(effect)
        dot = cell.get("dot")
        if dot is not None and dot is not False:
            out["dot"] = dot if dot is not True else True
        for key in ("color", "background"):
            value = cell.get(key)
            if value is not None:
                out[key] = value
        if cell.get("fill"):
            out["fill"] = True
        size = cell.get("size")
        if size is not None:
            out["size"] = float(size)
        for src, dst in (("width", "width"), ("w", "width"), ("min_width", "min_width"), ("min", "min_width")):
            value = cell.get(src)
            if value is not None:
                out[dst] = float(value)
        align = cell.get("align")
        if align is not None:
            out["align"] = str(align)
        return out

    if isinstance(cell, ColorRGBA):
        return {"dot": cell}
    return {"text": "" if cell is None else str(cell)}


def _hud_row(row, index):
    key = None
    if isinstance(row, dict):
        key = row.get("key")
        cells = row.get("cells")
        if cells is None:
            cells = row.get("row")
    elif isinstance(row, (list, tuple)):
        cells = row
    else:
        cells = [row]

    cells = [_hud_cell(c) for c in (cells or [])]
    if not cells:
        return None

    # без явного fill растягивается первая текстовая ячейка: так ["Aura", "R"] сразу выглядит
    # кейбиндом, а [{"effect": e}, name, time] - строкой зелья
    if not any(c.get("fill") for c in cells):
        for c in cells:
            if not any(k in c for k in _HUD_CELL_KINDS):
                c["fill"] = True
                break

    if key is None:
        key = next((c["text"] for c in cells if c.get("text")), None)
    return {"key": str(index) if key is None else str(key), "cells": cells}


def _hud_rows(rows):
    if not rows:
        return []
    out = []
    for index, row in enumerate(rows):
        item = _hud_row(row, index)
        if item is not None:
            out.append(item)
    return out


class _HudElement:
    __slots__ = ("_e", "_fonts", "_border")

    def __init__(self, element, fonts, border):
        self._e = element
        self._fonts = fonts
        self._border = border

    @property
    def raw(self):
        return self._e

    @property
    def name(self):
        return self._e.getName()

    @property
    def x(self):
        return float(self._e.getX())

    @x.setter
    def x(self, value):
        self._e.setX(float(value))

    @property
    def y(self):
        return float(self._e.getY())

    @y.setter
    def y(self, value):
        self._e.setY(float(value))

    @property
    def width(self):
        return float(self._e.getWidth())

    @width.setter
    def width(self, value):
        self._e.width(float(value))

    @property
    def height(self):
        return float(self._e.getHeight())

    @height.setter
    def height(self, value):
        self._e.height(float(value))

    @property
    def showing(self):
        return bool(self._e.isShowing())

    @showing.setter
    def showing(self, value):
        self._e.setShowing(bool(value))

    @property
    def icon(self):
        return str(self._e.getIcon())

    @property
    def alpha(self):
        """Прозрачность появления: 0 элемент спрятан, 1 на месте."""
        return float(self._e.renderAlpha())

    @property
    def drag(self):
        """Анимация перетаскивания: 1 пока элемент тащат мышью."""
        return float(self._e.dragAlpha())

    @property
    def selecting(self):
        """Анимация выделения в режиме правки HUD. Имя не select: так называется фабрика настройки."""
        return float(self._e.getSelecting().getValue())

    @property
    def scale(self):
        """Масштаб этого кадра — тот же, которым элемент рисует себя."""
        alpha = self.alpha
        return 0.5 + alpha * 0.5 - 0.05 * self.selecting

    @property
    def dragging(self):
        return bool(self._e.isDragging())

    def show(self):
        self.showing = True
        return self

    def hide(self):
        self.showing = False
        return self

    def pos(self, x, y):
        self._e.position(float(x), float(y))
        return self

    def size(self, width, height):
        self._e.size(float(width), float(height))
        return self

    def render(self, fn):
        self._e.renderer(self._wrap_render(fn))
        return self

    def layout(self, fn):
        self._e.layout(self._wrap_layout(fn))
        return self

    def signature(self, fn):
        self._e.signature(fn)
        return self

    def rows(self, fn):
        """Список строк в стиле кейбиндов клиента: шапка со значком и кейкапы.

        Функция возвращает список строк, строка - список ячеек. Ячейка это текст,
        либо словарь: text, icon, effect, dot, color, background, fill, width, min_width, align."""
        self._e.rows(self._wrap_rows(fn))
        return self

    def every(self, ms):
        """Как часто спрашивать строки, мс. По умолчанию 100."""
        self._e.rowsEvery(float(ms))
        return self

    def title(self, text):
        self._e.listTitle(str(text))
        return self

    def header(self, on=True):
        self._e.listHeader(bool(on))
        return self

    def uniform(self, on=True):
        """Одна длина у всех строк."""
        self._e.listUniform(bool(on))
        return self

    def sort(self, on=True):
        """Лесенка по ширине, как у кейбиндов. Выключишь - строки идут в порядке функции."""
        self._e.listSort(bool(on))
        return self

    def hide_empty(self, on=True):
        self._e.listHideEmpty(bool(on))
        return self

    def gap(self, px):
        """Зазор между ячейками и строками списка. По умолчанию 1, как у клиентских списков."""
        self._e.listGap(float(px))
        return self

    def visible_when(self, fn):
        self._e.visibleWhen(self._wrap_visible(fn))
        return self

    def show_when(self, fn):
        return self.visible_when(fn)

    def checkbox(self, name):
        return PyBooleanSetting(self._e, str(name))

    def slider(self, name):
        return PySliderSetting(self._e, str(name))

    def mode(self, name):
        return PyModeSetting(self._e, str(name))

    def select(self, name):
        return PySelectSetting(self._e, str(name))

    def button(self, name):
        return PyButtonSetting(self._e, str(name))

    def range(self, name):
        return PyRangeSetting(self._e, str(name))

    def color(self, name):
        return PyColorSetting(self._e, str(name))

    def bind(self, name):
        return PyBindSetting(self._e, str(name))

    def text(self, name):
        return PyTextSetting(self._e, str(name))

    def time(self, name):
        return PyTimeSetting(self._e, str(name))

    def info(self, name):
        return PyInfoSetting(self._e, str(name))

    def gradient(self, name):
        return PyGradientSetting(self._e, str(name))

    def position(self, name):
        return PyPositionSetting(self._e, str(name))

    def bezier(self, name):
        return PyBezierSetting(self._e, str(name))

    def blocks(self, name):
        return PyBlockSetting(self._e, str(name))

    def remove(self):
        return bool(self._e.remove())

    def __call__(self, fn):
        return self.render(fn)

    def _wrap_render(self, fn):
        argc = _positional_count(fn)

        def wrapped(context, element):
            draw = _HudDrawContext(context, element, self._fonts, self._border)
            if argc == 0:
                return fn()
            if argc == 1:
                return fn(draw)
            return fn(draw, self)

        return wrapped

    def _wrap_layout(self, fn):
        def builder(java_ui):
            fn(_UiBuilder(java_ui, "", 0.0, 0.0, window=False))

        return builder

    def _wrap_rows(self, fn):
        argc = _positional_count(fn)

        def wrapped():
            return _hud_rows(fn() if argc == 0 else fn(self))

        return wrapped

    def _wrap_visible(self, fn):
        argc = _positional_count(fn)

        def wrapped():
            if argc == 0:
                return bool(fn())
            return bool(fn(self))

        return wrapped

    def __getattr__(self, name):
        return getattr(self._e, name)


class _HudApi:
    __slots__ = ("_h", "_fonts", "_border")

    def __init__(self, hud, fonts, border):
        self._h = hud
        self._fonts = fonts
        self._border = border

    def __call__(self, *args, **kwargs):
        return self.add(*args, **kwargs)

    def add(self, name, icon="hud/player", width=80, height=20, x=8, y=8,
            showing=True, render=None, visible_when=None, show_when=None, layout=None):
        element = _HudElement(
            self._h.add(str(name), str(icon), float(width), float(height),
                        float(x), float(y), bool(showing), None, None),
            self._fonts,
            self._border,
        )
        if layout is not None:
            element.layout(layout)
        elif render is not None:
            element.render(render)
        visible = visible_when if visible_when is not None else show_when
        if visible is not None:
            element.visible_when(visible)
        return element

    def element(self, *args, **kwargs):
        return self.add(*args, **kwargs)

    def list(self, name, icon="hud/player", x=8, y=8, showing=True, rows=None, title=None,
             header=True, uniform=False, sort=True, hide_empty=True, every=100, gap=1,
             visible_when=None):
        """Элемент-список в стиле клиентских кейбиндов, зелий и стафф-листа.

        Строки отдаёт функция rows: список строк, строка - список ячеек."""
        element = self.add(name, icon=icon, x=x, y=y, showing=showing, visible_when=visible_when)
        element.header(header).uniform(uniform).sort(sort).hide_empty(hide_empty).every(every).gap(gap)
        if title is not None:
            element.title(title)
        if rows is not None:
            element.rows(rows)
        return element

    def rows(self, *args, **kwargs):
        return self.list(*args, **kwargs)

    def new(self, *args, **kwargs):
        return self.add(*args, **kwargs)

    def find(self, name):
        element = self._h.find(str(name))
        return None if element is None else _HudElement(element, self._fonts, self._border)

    def get(self, name):
        return self.find(name)

    def remove(self, target):
        if isinstance(target, _HudElement):
            return target.remove()
        return bool(self._h.remove(str(target)))

    def all(self):
        return [_HudElement(element, self._fonts, self._border) for element in _java_list(self._h.all())]

    def mine(self):
        return [_HudElement(element, self._fonts, self._border) for element in _java_list(self._h.mine())]

    @property
    def elements(self):
        """Все элементы HUD клиента словарями: встроенные и скриптовые, с координатами и анимациями.

        Числа те же, которыми HUD рисует себя, поэтому свой слой (события hud_render и
        post_hud_render) двигается вместе с элементами. Значения живые: спрашивай их в
        обработчике, а не запоминай при загрузке."""
        return _py_obj(self._h.elements())

    def info(self, name):
        """Элемент HUD по имени: ключ (hud.targethud), его последний сегмент или перевод."""
        return _py_obj(self._h.element(str(name)))

    def state(self, name):
        return self.info(name)


class _IslandStatus:
    __slots__ = ("_s", "_fonts", "_border")

    def __init__(self, status, fonts, border):
        self._s = status
        self._fonts = fonts
        self._border = border

    @property
    def raw(self):
        return self._s

    @property
    def name(self):
        return self._s.getName()

    @property
    def x(self):
        return float(self._s.getX())

    @property
    def y(self):
        return float(self._s.getY())

    @property
    def width(self):
        return float(self._s.getWidth())

    @property
    def w(self):
        return self.width

    @property
    def height(self):
        return float(self._s.getHeight())

    @property
    def h(self):
        return self.height

    @property
    def alpha(self):
        return float(self._s.renderAlpha())

    @property
    def extended(self):
        return bool(self._s.extended())

    @property
    def expanding(self):
        return float(self._s.extending())

    def size(self, width, height, radius=None):
        if radius is None:
            self._s.size(float(width), float(height))
        else:
            self._s.size(float(width), float(height), float(radius))
        return self

    def radius(self, radius):
        self._s.radius(float(radius))
        return self

    def expandable(self, value=True):
        self._s.expandable(bool(value))
        return self

    def selected(self, value=True):
        self._s.selected(bool(value))
        return self

    def visible_when(self, fn):
        self._s.visibleWhen(self._wrap_visible(fn))
        return self

    def show_when(self, fn):
        return self.visible_when(fn)

    def measure(self, fn):
        self._s.measure(self._wrap_measure(fn))
        return self

    def render(self, fn):
        self._s.renderer(self._wrap_render(fn))
        return self

    def click(self, fn):
        self._s.onClick(self._wrap_click(fn))
        return self

    def on_click(self, fn):
        return self.click(fn)

    def color(self, value):
        if callable(value):
            # colorFn, а не color: у Java-PyIslandStatus две 1-арг перегрузки
            # (PyCallable и ColorRGBA), и Jep для функции выбирает ColorRGBA →
            # "Expected ColorRGBA but received a function". Отдельное имя снимает
            # неоднозначность (как Node.colorFn у UI-нод).
            self._s.colorFn(self._wrap_color(value))
        elif isinstance(value, (list, tuple)):
            self._s.color(_make_color(*value))
        else:
            self._s.color(value)
        return self

    def remove(self):
        return bool(self._s.remove())

    def __call__(self, fn):
        return self.render(fn)

    def _wrap_render(self, fn):
        argc = _positional_count(fn)

        def wrapped(context, status):
            draw = _HudDrawContext(context, status, self._fonts, self._border)
            if argc == 0:
                return fn()
            if argc == 1:
                return fn(draw)
            return fn(draw, self)

        return wrapped

    def _wrap_measure(self, fn):
        argc = _positional_count(fn)

        def wrapped(status):
            if argc == 0:
                return fn()
            return fn(self)

        return wrapped

    def _wrap_visible(self, fn):
        argc = _positional_count(fn)

        def wrapped(status):
            if argc == 0:
                return bool(fn())
            return bool(fn(self))

        return wrapped

    def _wrap_color(self, fn):
        argc = _positional_count(fn)

        def wrapped(status):
            if argc == 0:
                return fn()
            return fn(self)

        return wrapped

    def _wrap_click(self, fn):
        argc = _positional_count(fn)

        def wrapped(mx, my, button, status):
            if argc == 0:
                return fn()
            if argc == 1:
                return fn(self)
            if argc == 3:
                return fn(float(mx), float(my), int(button))
            return fn(float(mx), float(my), int(button), self)

        return wrapped

    def __getattr__(self, name):
        return getattr(self._s, name)


class _IslandApi:
    __slots__ = ("_i", "_fonts", "_border")

    def __init__(self, island, fonts, border):
        self._i = island
        self._fonts = fonts
        self._border = border

    def __call__(self, *args, **kwargs):
        return self.add(*args, **kwargs)

    def add(self, name, width=48, height=15, radius=7, expandable=False,
            render=None, visible_when=None, show_when=None, measure=None, click=None, color=None):
        status = _IslandStatus(
            self._i.add(str(name), float(width), float(height), float(radius), bool(expandable),
                        None, None, None, None),
            self._fonts,
            self._border,
        )
        if render is not None:
            status.render(render)
        visible = visible_when if visible_when is not None else show_when
        if visible is not None:
            status.visible_when(visible)
        if measure is not None:
            status.measure(measure)
        if click is not None:
            status.click(click)
        if color is not None:
            status.color(color)
        return status

    def status(self, *args, **kwargs):
        return self.add(*args, **kwargs)

    def new(self, *args, **kwargs):
        return self.add(*args, **kwargs)

    def find(self, name):
        status = self._i.find(str(name))
        return None if status is None else _IslandStatus(status, self._fonts, self._border)

    def get(self, name):
        return self.find(name)

    def remove(self, target):
        if isinstance(target, _IslandStatus):
            return target.remove()
        return bool(self._i.remove(str(target)))

    def all(self):
        return [_IslandStatus(status, self._fonts, self._border) for status in _java_list(self._i.all())]

    def mine(self):
        return [_IslandStatus(status, self._fonts, self._border) for status in _java_list(self._i.mine())]


class _IslandStatusFactory:
    """Конструктор статуса Dynamic Island — как Module(...) для модулей.
    Делегирует в island.add(...), сам island остаётся менеджером (find/all/remove)."""
    __slots__ = ("_island",)

    def __init__(self, island):
        self._island = island

    def __call__(self, *args, **kwargs):
        return self._island.add(*args, **kwargs)

    def new(self, *args, **kwargs):
        return self._island.add(*args, **kwargs)


class _ClientApi:
    __slots__ = ("_c", "messages", "modules", "settings", "fonts", "ui", "paths", "hud", "island", "music",
                 "commands", "profile", "menu")

    def __init__(self, client, globals_vars, border):
        self._c = client
        self.messages = _ClientMessages(client)
        self.modules = _ClientModules(client)
        self.settings = _ClientSettings(client)
        self.fonts = _ClientFonts(client, globals_vars)
        self.ui = _ClientUi(client, border)
        self.paths = _ClientPaths(client)
        self.music = _Music(client.music())

    def chat(self, text):
        """Сказать в чат от имени игрока: строка уходит на сервер. Со слэша - команда."""
        return bool(self._c.chat(str(text)))

    def say(self, text):
        return self.chat(text)

    def command(self, line):
        """Команда серверу. Слэш в начале не обязателен."""
        return bool(self._c.command(str(line)))

    def cmd(self, line):
        return self.command(line)

    def reconnect(self, delay=1.5):
        """Перезайти на тот же сервер. Пауза нужна: сервер держит прежнюю сессию пару секунд."""
        return bool(self._c.reconnect(float(delay)))

    def disconnect(self):
        """Выйти в меню серверов."""
        return bool(self._c.disconnect())

    def server(self):
        """Адрес сервера или None в одиночной игре."""
        value = self._c.serverAddress()
        return None if value is None else str(value)

    def msg(self, text):
        self.messages.info(text)

    def warn(self, text):
        self.messages.warn(text)

    def error(self, text):
        self.messages.error(text)

    def overlay(self, text):
        self.messages.overlay(text)

    def find(self, module_name, setting_name=None):
        if setting_name is None:
            return self.modules.find(module_name)
        return self.settings.find(module_name, setting_name)

    def module(self, name):
        return self.modules.find(name)

    def setting(self, module_name, setting_name):
        return self.settings.find(module_name, setting_name)

    def list_modules(self):
        return self.modules.all()

    def cursor(self, cursor_type):
        self.ui.cursor(cursor_type)

    def menu_opened(self):
        return self.ui.menu_opened()

    def menu_open(self):
        return self.ui.menu_open()

    def font(self, weight, size):
        return self.fonts.get(weight, size)

    def font_width(self, weight, size, text):
        return self.fonts.width(weight, size, text)

    def fontWidth(self, weight, size, text):
        return self.font_width(weight, size, text)

    def font_height(self, weight, size):
        return self.fonts.height(weight, size)

    def fontHeight(self, weight, size):
        return self.font_height(weight, size)

    def game_dir(self):
        return self.paths.game_dir()

    def gameDir(self):
        return self.game_dir()

    def dynamic_island(self):
        return self.island

    def dynamicIsland(self):
        return self.island

    def border(self, *args):
        return self.ui.border(*args)

    def border4(self, tl, tr, br, bl):
        return self.ui.border4(tl, tr, br, bl)



class _AuraRotationContext:
    __slots__ = ("handler", "attack_distance", "walls", "ray_trace", "move_correction", "target", "rotations")

    def __init__(self, handler, attack_distance, walls, ray_trace, move_correction, target, rotations):
        self.handler = handler
        self.attack_distance = attack_distance
        self.walls = walls
        self.ray_trace = ray_trace
        self.move_correction = move_correction
        self.target = target
        self.rotations = rotations

    def default(self):
        return self.rotations.default(self.target)

    def to(self, entity=None):
        return self.rotations.to(self.target if entity is None else entity)

    def apply(self, yaw, pitch, **kwargs):
        return self.rotations.apply(yaw, pitch, **kwargs)


class _Aura:
    """Регистрация своих режимов ротации в Aura.

    Режим — класс с методами, ровно как RotationMode в клиенте:
        class MyRot:
            name = "My Rot"
            def rotate(self, handler, attack_distance, walls, ray_trace, move_correction, target): ...
            def attack(self): ...               # необязательно
            def can_attack(self): return True   # необязательно
            def target_null(self): ...          # необязательно
            def update(self): ...               # необязательно
        aura.add(MyRot())
    """
    __slots__ = ("_a", "_rotations")

    def __init__(self, java_aura, rotations=None):
        self._a = java_aura
        self._rotations = rotations

    @property
    def module(self):
        return _wrap(self._a.module())

    def _wrap_rotate(self, rotate):
        if rotate is None:
            return None

        # handler / move_correction / target прилетают сырыми из джавы —
        # оборачиваем в _J (ремап-сейф), числа и булы отдаём как есть
        def wrapped(handler, attack_distance, walls, ray_trace, move_correction, target):
            context = _AuraRotationContext(
                _wrap(handler),
                attack_distance,
                walls,
                ray_trace,
                _wrap(move_correction),
                _wrap(target),
                self._rotations,
            )
            if self._wants_context(rotate):
                result = rotate(context)
            else:
                result = rotate(
                    context.handler,
                    context.attack_distance,
                    context.walls,
                    context.ray_trace,
                    context.move_correction,
                    context.target,
                )
            return self._normalize_rotation_result(result)

        return wrapped

    @staticmethod
    def _wants_context(fn):
        try:
            signature = inspect.signature(fn)
            params = list(signature.parameters.values())
        except Exception:
            return False

        for param in params:
            if param.kind == param.VAR_POSITIONAL:
                return False

        positional = [
            param for param in params
            if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
        ]
        return len(positional) <= 1

    @staticmethod
    def _wrap_callback(fn):
        if fn is None:
            return None

        def wrapped():
            return _unwrap_deep(fn())

        return wrapped

    @staticmethod
    def _wrap_bool(fn):
        if fn is None:
            return None

        def wrapped():
            return bool(fn())

        return wrapped

    @staticmethod
    def _normalize_rotation_result(value):
        value = _unwrap_deep(value)
        if value is None:
            return None

        if isinstance(value, (list, tuple)):
            if len(value) < 2:
                raise ValueError("rotation result must contain yaw and pitch")
            return {"yaw": float(value[0]), "pitch": float(value[1])}

        if isinstance(value, dict):
            out = {}
            for key, item in value.items():
                if key in ("rotation", "rot"):
                    out[key] = _Aura._normalize_rotation_result(item)
                else:
                    out[key] = _unwrap_deep(item)
            return out

        yaw, pitch = _Aura._read_yaw_pitch(value)
        if yaw is not None and pitch is not None:
            return {"yaw": float(yaw), "pitch": float(pitch)}

        return value

    @staticmethod
    def _read_yaw_pitch(value):
        def read(names):
            for name in names:
                try:
                    attr = getattr(value, name)
                    return attr() if callable(attr) else attr
                except Exception:
                    pass
            return None

        return read(("yaw", "getYaw")), read(("pitch", "getPitch"))

    def add(self, mode, select=False):
        """Зарегистрировать режим-класс (экземпляр)."""
        name = str(getattr(mode, "name", None) or type(mode).__name__)
        java_mode = self._a.addRotation(
            name,
            self._wrap_rotate(getattr(mode, "rotate", None)),
            self._wrap_callback(getattr(mode, "attack", None)),
            self._wrap_bool(getattr(mode, "can_attack", None)),
            self._wrap_callback(getattr(mode, "target_null", None)),
            self._wrap_callback(getattr(mode, "update", None)),
        )
        if select:
            self._a.selectRotation(name)
        return java_mode

    def add_rotation(self, name, rotate=None, attack=None, can_attack=None,
                     target_null=None, update=None, select=False):
        """Зарегистрировать режим из функций (без класса)."""
        java_mode = self._a.addRotation(
            str(name),
            self._wrap_rotate(rotate),
            self._wrap_callback(attack),
            self._wrap_bool(can_attack),
            self._wrap_callback(target_null),
            self._wrap_callback(update),
        )
        if select:
            self._a.selectRotation(str(name))
        return java_mode

    def rotation(self, name, **kwargs):
        select = kwargs.pop("select", False)

        def deco(fn):
            self.add_rotation(name, rotate=fn, select=select, **kwargs)
            return fn

        return deco

    def select(self, name):
        self._a.selectRotation(str(name))

    def remove(self, rotation):
        if isinstance(rotation, str):
            self._a.removeRotation(rotation)
        else:
            self._a.removeRotation(_unwrap(rotation))

    def has(self, name):
        return self._a.hasRotation(str(name))

    def current(self):
        return self._a.currentRotation()

    def target(self):
        return _wrap(self._a.target())

    @property
    def enabled(self):
        return self._a.isEnabled()

    @enabled.setter
    def enabled(self, value):
        self._a.setEnabled(bool(value))

    @property
    def attack_distance(self):
        return self._a.attackDistance()


class _Rotations:
    """Управление наводкой вне Aura (свои аим-скрипты)."""
    __slots__ = ("_r",)

    def __init__(self, java):
        self._r = java

    def current(self):
        return tuple(self._r.current())

    def player(self):
        return tuple(self._r.player())

    def idling(self):
        return bool(self._r.idling())

    def default(self, target=None):
        return tuple(self._r.defaultAngles(_unwrap(target)))

    def to(self, entity):
        return tuple(self._r.to(_unwrap(entity)))

    def to_point(self, x, y, z):
        return tuple(self._r.toPoint(float(x), float(y), float(z)))

    def gcd(self, from_yaw, from_pitch, to_yaw, to_pitch):
        return tuple(self._r.gcd(float(from_yaw), float(from_pitch), float(to_yaw), float(to_pitch)))

    def gcd_step(self, from_yaw, from_pitch, to_yaw, to_pitch, step, pitch_step=None):
        if pitch_step is None:
            return tuple(self._r.gcdStep(float(from_yaw), float(from_pitch),
                                         float(to_yaw), float(to_pitch), float(step)))
        return tuple(self._r.gcdSteps(float(from_yaw), float(from_pitch),
                                      float(to_yaw), float(to_pitch), float(step), float(pitch_step)))

    def custom_gcd(self, from_yaw, from_pitch, to_yaw, to_pitch, step, pitch_step=None):
        return self.gcd_step(from_yaw, from_pitch, to_yaw, to_pitch, step, pitch_step)

    def vanilla_step(self):
        return float(self._r.vanillaStep())

    def apply(self, yaw, pitch, correction="silent", priority="normal", yaw_speed=180, pitch_speed=180,
              return_speed=180, vanilla_gcd=True, raw_gcd=False):
        correct_gcd = bool(vanilla_gcd) and not bool(raw_gcd)
        self._r.apply(float(yaw), float(pitch), str(correction), str(priority),
                      float(yaw_speed), float(pitch_speed), float(return_speed), correct_gcd)


class _StorageFile:
    """Простое JSON-хранилище на скрипт. Переживает reload и перезапуск."""

    def __init__(self, path):
        self._path = path
        self._data = {}
        self.load()

    def load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                self._data = json.load(handle)
        except Exception:
            self._data = {}
        return self

    def save(self):
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return self

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        return self

    def remove(self, key):
        self._data.pop(key, None)
        return self

    def all(self):
        return dict(self._data)

    def clear(self):
        self._data = {}
        return self

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data


class _Storage:
    __slots__ = ("_dir",)

    def __init__(self, paths):
        self._dir = os.path.join(paths.scripts(), "storage")

    def open(self, name):
        return _StorageFile(os.path.join(self._dir, str(name) + ".json"))

    def __call__(self, name):
        return self.open(name)


class _Vec:
    """Маленькая 3D-математика (списки/кортежи [x, y, z])."""

    @staticmethod
    def add(a, b):
        return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]

    @staticmethod
    def sub(a, b):
        return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]

    @staticmethod
    def scale(a, s):
        return [a[0] * s, a[1] * s, a[2] * s]

    @staticmethod
    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @staticmethod
    def length(a):
        return (a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) ** 0.5

    @staticmethod
    def distance(a, b):
        return _Vec.length(_Vec.sub(a, b))

    @staticmethod
    def normalize(a):
        length = _Vec.length(a)
        return [0.0, 0.0, 0.0] if length == 0 else _Vec.scale(a, 1.0 / length)

    @staticmethod
    def lerp(a, b, t):
        return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]

    @staticmethod
    def clamp(value, low, high):
        return low if value < low else (high if value > high else value)


def _is_instance(value, named_fqn):
    if value is None:
        return False
    return bool(McBridge.isInstance(_unwrap(value), named_fqn))


class _Container:
    """Открытое чужое меню: сундук, шалкер, меню сервера на предметах.

    Слоты нумеруются с нуля: сначала слоты самого контейнера, следом инвентарь игрока.
    Это нумерация сервера, и с номерами из глобала inventory она НЕ совпадает.
    """

    __slots__ = ("_c",)

    def __init__(self, container):
        self._c = container

    @property
    def open(self):
        return bool(self._c.open())

    @property
    def title(self):
        value = self._c.title()
        return None if value is None else str(value)

    @property
    def type(self):
        value = self._c.type()
        return None if value is None else str(value)

    @property
    def size(self):
        """Слотов у самого контейнера, без инвентаря игрока."""
        return int(self._c.size())

    @property
    def total(self):
        """Слотов всего, вместе с инвентарём игрока."""
        return int(self._c.total())

    @property
    def sync_id(self):
        return int(self._c.syncId())

    def stack(self, slot):
        return self._c.stack(int(slot))

    def id(self, slot):
        value = self._c.id(int(slot))
        return None if value is None else str(value)

    def label(self, slot):
        value = self._c.label(int(slot))
        return None if value is None else str(value)

    def count(self, slot):
        return int(self._c.count(int(slot)))

    def lore(self, slot):
        return [str(line) for line in _java_list(self._c.lore(int(slot)))]

    def items(self, with_player=False):
        """Содержимое: по словарю на занятый слот (slot, id, name, count, lore)."""
        return _py_obj(self._c.items(bool(with_player)))

    def find(self, query, with_player=False):
        """Слот с таким предметом или -1. Ищет и по id, и по видимому имени."""
        return int(self._c.find(str(query), bool(with_player)))

    def find_all(self, query, with_player=False):
        return [int(v) for v in _java_list(self._c.findAll(str(query), bool(with_player)))]

    def findAll(self, query, with_player=False):
        return self.find_all(query, with_player)

    def click(self, slot, button=0, mode="pick"):
        """Клик по слоту: button 0 левая, 1 правая; mode pick / shift / drop / swap / clone."""
        return bool(self._c.click(int(slot), int(button), str(mode)))

    def right_click(self, slot):
        return bool(self._c.rightClick(int(slot)))

    def rightClick(self, slot):
        return self.right_click(slot)

    def shift_click(self, slot):
        return bool(self._c.shiftClick(int(slot)))

    def shiftClick(self, slot):
        return self.shift_click(slot)

    def drop(self, slot, stack=False):
        return bool(self._c.drop(int(slot), bool(stack)))

    def close(self):
        return bool(self._c.close())


class _World:
    __slots__ = ("_mc", "_aura", "_b")

    def __init__(self, mc, aura):
        self._mc = mc
        self._aura = aura
        self._b = PyBlocks()

    def ingame(self):
        return self._mc.world is not None and self._mc.player is not None

    def entities(self):
        if self._mc.world is None:
            return []
        return list(self._mc.world.getEntities())

    def living(self):
        return [entity for entity in self.entities() if _is_instance(entity, "net.minecraft.entity.LivingEntity")]

    def players(self):
        if self._mc.world is None:
            return []
        player = self._mc.player
        return [other for other in self._mc.world.getPlayers() if other != player]

    def self(self):
        return self._mc.player

    def target(self):
        return self._aura.target()

    def nearestPlayer(self):
        if self._mc.world is None or self._mc.player is None:
            return None
        best = None
        best_dist = float("inf")
        player = self._mc.player
        for other in self.players():
            dist = float(player.distanceTo(_unwrap(other)))
            if dist < best_dist:
                best = other
                best_dist = dist
        return best

    def nearest_player(self):
        return self.nearestPlayer()

    def time(self):
        return 0 if self._mc.world is None else self._mc.world.getTime()

    # --- измерение ---

    def dimension(self):
        """Полный идентификатор: minecraft:overworld, minecraft:the_nether, minecraft:the_end."""
        value = self._b.dimension()
        return None if value is None else str(value)

    def dimension_name(self):
        """Короткое имя: overworld, the_nether, the_end."""
        value = self._b.dimensionName()
        return None if value is None else str(value)

    def dimensionName(self):
        return self.dimension_name()

    def is_overworld(self):
        return bool(self._b.isOverworld())

    def is_nether(self):
        return bool(self._b.isNether())

    def is_end(self):
        return bool(self._b.isEnd())

    # --- блоки ---

    def block(self, *pos):
        """Идентификатор блока в точке или None, если чанк не загружен."""
        x, y, z = _block_coords(*pos)
        value = self._b.at(x, y, z)
        return None if value is None else str(value)

    def block_name(self, *pos):
        """Имя блока так, как его видит игрок."""
        x, y, z = _block_coords(*pos)
        value = self._b.name(x, y, z)
        return None if value is None else str(value)

    def blockName(self, *pos):
        return self.block_name(*pos)

    def block_info(self, *pos):
        """Всё о блоке разом: id, name, air, liquid, solid, pos, state."""
        x, y, z = _block_coords(*pos)
        info = self._b.info(x, y, z)
        return None if info is None else _py_obj(info)

    def blockInfo(self, *pos):
        return self.block_info(*pos)

    def is_block(self, block_id, *pos):
        x, y, z = _block_coords(*pos)
        return bool(self._b.isBlock(x, y, z, str(block_id)))

    def is_air(self, *pos):
        x, y, z = _block_coords(*pos)
        return bool(self._b.isAir(x, y, z))

    def is_solid(self, *pos):
        x, y, z = _block_coords(*pos)
        return bool(self._b.isSolid(x, y, z))

    def is_liquid(self, *pos):
        x, y, z = _block_coords(*pos)
        return bool(self._b.isLiquid(x, y, z))

    def top(self, x, z=None):
        """Высота верхнего непустого блока в колонке."""
        if z is None:
            x, _, z = _block_coords(x)
        return int(self._b.top(int(x), int(z)))

    def nearest_block(self, block_id, radius=32):
        """Ближайший такой блок: [x, y, z] или None. Ищет от игрока наружу."""
        found = self._b.nearest(str(block_id), int(radius))
        return None if found is None else [int(v) for v in found]

    def nearestBlock(self, block_id, radius=32):
        return self.nearest_block(block_id, radius)

    def find_blocks(self, block_id, radius=32, limit=64):
        """Все такие блоки в радиусе, ближние первыми."""
        return [[int(v) for v in item] for item in self._b.find(str(block_id), int(radius), int(limit))]

    def findBlocks(self, block_id, radius=32, limit=64):
        return self.find_blocks(block_id, radius, limit)

    def known_block(self, block_id):
        """Есть ли такой блок в игре: опечатку в id видно сразу."""
        return bool(self._b.known(str(block_id)))


def _block_coords(*pos):
    """Координаты блока из трёх чисел, списка, сущности или BlockPos/Vec3d."""
    if not pos:
        raise ValueError("нужна позиция: x, y, z или объект с координатами")

    if len(pos) >= 3:
        nums = pos
    elif isinstance(pos[0], (list, tuple)):
        nums = tuple(pos[0])
    else:
        # Только через обёртку _J: имена методов резолвит McBridge, поэтому сущность
        # из события работает так же, как объект из world.* (сырой вызов getX() на
        # ремапнутой сборке не нашёл бы метод).
        obj = pos[0] if isinstance(pos[0], _J) else _wrap(pos[0])
        if not isinstance(obj, _J):
            raise ValueError("нужны три координаты: x, y, z")
        try:
            nums = (obj.getX(), obj.getY(), obj.getZ())
        except Exception:
            nums = (obj.x, obj.y, obj.z)

    if len(nums) < 3:
        raise ValueError("нужны три координаты: x, y, z")
    return tuple(int(math.floor(float(v))) for v in nums[:3])


class _Newton:
    """Пасфайндер Newton: ходьба к точке, полёт на элитре, копка блоков и работа с областью.

    Ни один метод не бросает из-за неготового пасфайндера — вернёт False/None.
    Ход процесса приходит событиями newton_started / newton_path / newton_node /
    newton_finished / newton_failed.
    """
    __slots__ = ("_n",)

    def __init__(self, java):
        self._n = java

    def ready(self):
        return bool(self._n.ready())

    def active(self):
        return bool(self._n.active())

    # --- ходьба и полёт ---

    def goto(self, *pos, radius=0, elytra=False):
        x, y, z = _block_coords(*pos)
        if elytra:
            return bool(self._n.flyTo(x, y, z, True))
        if radius and int(radius) > 0:
            return bool(self._n.goToNear(x, y, z, int(radius)))
        return bool(self._n.goTo(x, y, z))

    def go_to(self, *pos, **kwargs):
        return self.goto(*pos, **kwargs)

    def goto_near(self, *pos, radius=1):
        return self.goto(*pos, radius=radius)

    def goto_xz(self, x, z):
        return bool(self._n.goToXZ(int(math.floor(float(x))), int(math.floor(float(z)))))

    def goto_y(self, y):
        return bool(self._n.goToY(int(math.floor(float(y)))))

    def fly_to(self, *pos, keep_y=True):
        x, y, z = _block_coords(*pos)
        return bool(self._n.flyTo(x, y, z, bool(keep_y)))

    def fly(self, *pos, **kwargs):
        return self.fly_to(*pos, **kwargs)

    # --- блоки и области ---

    def mine(self, block):
        return bool(self._n.mine(str(block)))

    def excavate(self, corner1, corner2, block=None):
        x1, y1, z1 = _block_coords(corner1)
        x2, y2, z2 = _block_coords(corner2)
        return bool(self._n.excavate(x1, y1, z1, x2, y2, z2, None if block is None else str(block)))

    def fill(self, corner1, corner2, block):
        x1, y1, z1 = _block_coords(corner1)
        x2, y2, z2 = _block_coords(corner2)
        return bool(self._n.fill(x1, y1, z1, x2, y2, z2, str(block)))

    def select(self, *pos):
        x, y, z = _block_coords(*pos)
        self._n.select(x, y, z)
        return self

    def clear_selection(self):
        self._n.selectClear()
        return self

    def selection(self):
        raw = self._n.selection()
        if raw is None:
            return None
        values = [int(v) for v in raw]
        return {"min": values[0:3], "max": values[3:6]}

    def excavate_selection(self, block=None):
        return bool(self._n.excavateSelection(None if block is None else str(block)))

    def fill_selection(self, block):
        return bool(self._n.fillSelection(str(block)))

    # --- текущий процесс ---

    def cancel(self):
        self._n.cancel()
        return self

    def stop(self):
        return self.cancel()

    def pause(self):
        return bool(self._n.pause())

    def resume(self):
        return bool(self._n.resume())

    def paused(self):
        return bool(self._n.paused())

    def process(self):
        return self._n.process()

    def status(self):
        return self._n.status()

    def command(self, line):
        return bool(self._n.command(str(line)))

    def path(self):
        steps = int(self._n.pathSteps())
        if steps <= 0:
            return None
        next_node = self._n.nextNode()
        goal = self._n.goalPos()
        return {
            "step": int(self._n.pathStep()),
            "steps": steps,
            "next": None if next_node is None else [int(v) for v in next_node],
            "goal": None if goal is None else [float(v) for v in goal],
        }

    def progress(self):
        steps = int(self._n.pathSteps())
        if steps <= 0:
            return 0.0
        return min(1.0, int(self._n.pathStep()) / steps)

    # --- тумблеры ---

    @property
    def safewalk(self):
        return bool(self._n.safewalk())

    @safewalk.setter
    def safewalk(self, value):
        self._n.setSafewalk(bool(value))

    @property
    def logging(self):
        return bool(self._n.logging())

    @logging.setter
    def logging(self, value):
        self._n.setLogging(bool(value))


class _Bag(dict):
    """Словарь, поля которого читаются и точкой: panel.x это то же самое, что panel["x"].

    Данные из клиента (панель меню, элемент HUD, трек музыки, запись FunTime) приходят
    словарями, и скобки в каждой строке отрисовки читаются тяжело. Это обычный dict со всеми
    его методами — get(), items(), in, распаковка, json.dumps, — просто с точкой в придачу.

    Имена методов самого словаря точкой не перекрываются: bag.keys это метод dict, а значение
    такого ключа берётся скобками (bag["keys"]).
    """

    __slots__ = ()

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


def _py_obj(value):
    """Java-структура в питоновские списки и словари, чтобы скрипт не возился с обёртками."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_py_obj(item) for item in value]
    if isinstance(value, dict):
        return _Bag((key, _py_obj(item)) for key, item in value.items())

    try:
        keys = value.keySet()
    except Exception:
        keys = None
    if keys is not None:
        return _Bag((str(key), _py_obj(value.get(key))) for key in _java_list(keys))

    iterator = McBridge.iterator(value)
    if iterator is not None:
        out = []
        while iterator.hasNext():
            out.append(_py_obj(iterator.next()))
        return out
    return value


class _Notify:
    """Уведомления клиента: строка в Dynamic Island, плашка у прицела, плашка с предметом."""
    __slots__ = ("_n",)

    def __init__(self, java):
        self._n = java

    def __call__(self, text, type="info"):
        return self.island(text, type)

    def island(self, text, type="info"):
        self._n.island(str(text), str(type))
        return self

    def crosshair(self, title, desc="", type="info"):
        self._n.crosshair(str(title), str(desc), str(type))
        return self

    def item(self, text, item="paper", highlight=None, color=None):
        self._n.item(str(text), str(item), None if highlight is None else str(highlight), color)
        return self

    def effect(self, text, effect, highlight=None, color=None):
        self._n.effect(str(text), _effect_arg(effect), None if highlight is None else str(highlight), color)
        return self

    def success(self, text):
        return self.island(text, "success")

    def error(self, text):
        return self.island(text, "error")

    def info(self, text):
        return self.island(text, "info")

    def sound(self):
        self._n.sound()
        return self

    def count(self):
        return int(self._n.count())


class _Inventory:
    """Инвентарь: поиск предметов, счётчики, перекладывание, выбор слота.

    Слоты нумеруются как в игре: 0-8 хотбар, 9-35 рюкзак, 36-39 броня, 40 левая рука.
    """
    __slots__ = ("_i",)

    def __init__(self, java):
        self._i = java

    def selected(self):
        return int(self._i.selected())

    def select(self, slot):
        return bool(self._i.select(int(slot)))

    def stack(self, slot):
        return _wrap(self._i.stack(int(slot)))

    def id(self, slot):
        return self._i.id(int(slot))

    def label(self, slot):
        return self._i.label(int(slot))

    def count(self, slot):
        return int(self._i.count(int(slot)))

    def find(self, item, where="all"):
        slot = int(self._i.find(str(item), str(where)))
        return None if slot < 0 else slot

    def find_all(self, item, where="all"):
        return [int(v) for v in _java_list(self._i.findAll(str(item), str(where)))]

    def total(self, item, where="all"):
        return int(self._i.total(str(item), str(where)))

    def empty(self, where="all"):
        slot = int(self._i.empty(str(where)))
        return None if slot < 0 else slot

    def has(self, item, where="all"):
        return self.find(item, where) is not None

    def hold(self, item):
        slot = int(self._i.hold(str(item)))
        return None if slot < 0 else slot

    def swap(self, first, second):
        return bool(self._i.swap(int(first), int(second)))

    def move(self, source, target):
        return bool(self._i.move(int(source), int(target)))

    def quick_move(self, slot):
        return bool(self._i.quickMove(int(slot)))

    def to_offhand(self, slot):
        return bool(self._i.toOffhand(int(slot)))

    def to_armor(self, slot, piece):
        return bool(self._i.toArmor(int(slot), str(piece)))

    def with_slot(self, slot, action):
        return bool(self._i.withSlot(int(slot), action))

    def durability(self, slot):
        value = float(self._i.durability(int(slot)))
        return None if value < 0 else value

    def enchant(self, slot, name):
        return int(self._i.enchant(int(slot), str(name)))

    def slots(self, where="all"):
        return [int(v) for v in _java_list(self._i.slots(str(where)))]

    def offhand_is(self, item):
        return bool(self._i.offhandIs(str(item)))

    def container_open(self):
        return bool(self._i.containerOpen())

    def items(self, where="all"):
        """Список занятых слотов: (номер, id предмета, количество)."""
        out = []
        for slot in self.slots(where):
            item_id = self.id(slot)
            if item_id is not None:
                out.append((slot, item_id, self.count(slot)))
        return out


class _Effect:
    """Один эффект: имя, уровень, сколько осталось и иконка.

    Объект - снимок на момент запроса: время в нём не идёт, поэтому список берут заново
    каждый кадр, а не держат в переменной скрипта.
    """
    __slots__ = ("_e",)

    def __init__(self, java):
        self._e = java

    @property
    def raw(self):
        """Java-объект эффекта."""
        return self._e

    @property
    def id(self):
        """Полный id: minecraft:speed."""
        return str(self._e.id())

    @property
    def key(self):
        """Короткий id без namespace: speed."""
        return str(self._e.key())

    @property
    def name(self):
        """Название на языке клиента."""
        return str(self._e.name())

    @property
    def label(self):
        """Название с уровнем: Скорость II."""
        return str(self._e.label())

    @property
    def level(self):
        """Уровень с единицы, как в игре."""
        return int(self._e.level())

    @property
    def amplifier(self):
        """Уровень с нуля, как внутри игры."""
        return int(self._e.amplifier())

    @property
    def duration(self):
        """Осталось тиков (20 в секунде). Бесконечный эффект - -1."""
        return int(self._e.duration())

    @property
    def seconds(self):
        """Осталось секунд. Бесконечный эффект - -1."""
        return float(self._e.seconds())

    @property
    def time(self):
        """Оставшееся время строкой: 01:23."""
        return str(self._e.time())

    @property
    def active(self):
        """Висит ли эффект прямо сейчас (у описания типа из info() - False)."""
        return bool(self._e.active())

    @property
    def infinite(self):
        return bool(self._e.infinite())

    @property
    def ambient(self):
        """Эффект от маяка: игра рисует его тусклее."""
        return bool(self._e.ambient())

    @property
    def particles(self):
        return bool(self._e.particles())

    @property
    def visible(self):
        """Показывает ли игра иконку эффекта."""
        return bool(self._e.visible())

    @property
    def hidden(self):
        """Служебный эффект: сервер спрятал и частицы, и иконку."""
        return bool(self._e.hidden())

    @property
    def color(self):
        """Цвет эффекта - тот же, которым игра красит частицы."""
        return self._e.color()

    @property
    def category(self):
        """good - полезный, bad - вредный, neutral - остальные."""
        return str(self._e.category())

    @property
    def good(self):
        return bool(self._e.good())

    @property
    def bad(self):
        return bool(self._e.bad())

    @property
    def atlas(self):
        """Атлас иконок эффектов - нужен, только если рисуешь картинку сам."""
        return self._e.atlas()

    @property
    def uv(self):
        """Кусок атласа под иконку: (u1, u2, v1, v2)."""
        return (float(self._e.u1()), float(self._e.u2()),
                float(self._e.v1()), float(self._e.v2()))

    @property
    def instance(self):
        """Ванильный StatusEffectInstance, либо None у описания типа."""
        return _wrap(self._e.instance())

    def draw(self, ctx, x=0, y=0, size=10, color=None):
        """Нарисовать иконку эффекта в контексте худа, экрана или меню."""
        ctx.effect(self, x, y, size, color)
        return self

    def __str__(self):
        return str(self._e.toString())

    def __repr__(self):
        return "<effect %s>" % self.id

    def __eq__(self, other):
        if isinstance(other, _Effect):
            return self.id == other.id
        if isinstance(other, str):
            return self.id == other or self.key == other
        return NotImplemented

    def __hash__(self):
        return hash(self.id)


def _effect_arg(value):
    """Эффект в том виде, в каком его понимает Java: обёртка, id-строка или ванильный объект."""
    if isinstance(value, _Effect):
        return value.raw
    return _unwrap(value)


class _Effects:
    """Баффы и дебаффы: что висит на игроке, сколько осталось и как нарисовать иконку.

    Список отсортирован по id, поэтому иконки в ряд не прыгают между кадрами. Служебные
    эффекты, у которых сервер спрятал и частицы, и иконку, в список не попадают - нужны,
    зови list(hidden=True).

    Эффект всюду можно назвать строкой: "speed" или "minecraft:speed".
    """
    __slots__ = ("_e",)

    def __init__(self, java):
        self._e = java

    def list(self, hidden=False):
        """Эффекты игрока."""
        return [_Effect(v) for v in _java_list(self._e.list(bool(hidden)))]

    def of(self, entity, hidden=False):
        """Эффекты существа. У чужих клиент знает только то, что прислал сервер."""
        return [_Effect(v) for v in _java_list(self._e.of(_unwrap(entity), bool(hidden)))]

    def get(self, effect, entity=None):
        """Эффект по id, либо None. entity - у кого смотреть, по умолчанию сам игрок."""
        if entity is None:
            java = self._e.get(_effect_arg(effect))
        else:
            java = self._e.get(_effect_arg(effect), _unwrap(entity))
        return None if java is None else _Effect(java)

    def has(self, effect):
        return bool(self._e.has(_effect_arg(effect)))

    def level(self, effect):
        """Уровень с единицы; нет эффекта - 0."""
        return int(self._e.level(_effect_arg(effect)))

    def duration(self, effect):
        """Осталось тиков; нет эффекта - 0, бесконечный - -1."""
        return int(self._e.duration(_effect_arg(effect)))

    def seconds(self, effect):
        """Осталось секунд; нет эффекта - 0, бесконечный - -1."""
        return float(self._e.seconds(_effect_arg(effect)))

    def time(self, effect):
        """Оставшееся время строкой 01:23; нет эффекта - пустая строка."""
        return str(self._e.time(_effect_arg(effect)))

    def info(self, effect):
        """Описание типа (имя, цвет, иконка), даже если эффекта на игроке нет. Неизвестный id - None."""
        java = self._e.info(_effect_arg(effect))
        return None if java is None else _Effect(java)

    def types(self):
        """Все id эффектов, какие знает игра."""
        return [str(v) for v in _java_list(self._e.types())]

    def good(self, hidden=False):
        """Только полезные."""
        return [e for e in self.list(hidden) if e.good]

    def bad(self, hidden=False):
        """Только вредные."""
        return [e for e in self.list(hidden) if e.bad]

    def draw(self, ctx, effect, x=0, y=0, size=10, color=None):
        """Иконка эффекта по id или объекту - в контексте худа, экрана или меню."""
        ctx.effect(effect, x, y, size, color)
        return self

    def __call__(self, hidden=False):
        return self.list(hidden)

    def __iter__(self):
        return iter(self.list())

    def __len__(self):
        return len(self.list())

    def __contains__(self, effect):
        return self.has(effect)


class _Theme:
    """Цвета текущей темы клиента. Работают где угодно, не только в лейауте."""
    __slots__ = ("_t",)

    def __init__(self, java):
        self._t = java

    def __call__(self, name):
        return self.color(name)

    def color(self, name):
        return self._t.color(str(name))

    def accent(self):
        return self._t.accent()

    def text(self):
        return self._t.text()

    def background(self):
        return self._t.background()

    def second(self):
        return self._t.second()

    def outline(self):
        return self._t.outline()

    def on_accent(self):
        return self._t.onAccent()

    def readable(self, background):
        return self._t.readable(background)

    def set_accent(self, color):
        self._t.setAccent(color)
        return self

    def name(self):
        return self._t.name()

    def dark(self):
        return bool(self._t.dark())


class _Profile:
    """Аккаунт игрока в клиенте: ник, uid, роль, срок подписки и аватарка.

    Данные приезжают с сайта уже после запуска, поэтому спрашивать их надо каждый раз, а не
    запоминать при загрузке скрипта: до ответа сайта ник пустой, а роль у всех default
    (profile.loaded говорит, пришёл ли ответ)."""
    __slots__ = ("_p",)

    def __init__(self, java):
        self._p = java

    def __call__(self):
        return self.all()

    @property
    def username(self):
        return str(self._p.username())

    @property
    def name(self):
        return self.username

    @property
    def uid(self):
        return int(self._p.uid())

    @property
    def role(self):
        """Роль строкой: default, user, beta, media, support, moderator, alpha, admin, owner."""
        return str(self._p.role())

    @property
    def staff(self):
        return bool(self._p.staff())

    @property
    def admin(self):
        return bool(self._p.admin())

    @property
    def loaded(self):
        return bool(self._p.loaded())

    def has_role(self, *names):
        return any(self._p.hasRole(str(name)) for name in names)

    def hasRole(self, *names):
        return self.has_role(*names)

    @property
    def subscription(self):
        """Срок подписки строкой ровно так, как его показывает клиент: 05-05-2026 или Навсегда."""
        return str(self._p.subscription())

    @property
    def forever(self):
        return bool(self._p.forever())

    @property
    def expired(self):
        return bool(self._p.expired())

    @property
    def subscription_end(self):
        """Конец подписки в секундах эпохи (как time.time()); None — бессрочно или срок неизвестен."""
        if self.forever:
            return None
        end = int(self._p.subscriptionEnd())
        return None if end <= 0 else end / 1000.0

    @property
    def subscriptionEnd(self):
        return self.subscription_end

    @property
    def subscription_left(self):
        """Сколько осталось до конца подписки в секундах; None — бессрочно или срок неизвестен."""
        end = self.subscription_end
        return None if end is None else float(self._p.subscriptionLeft()) / 1000.0

    @property
    def subscriptionLeft(self):
        return self.subscription_left

    @property
    def days_left(self):
        """Дней до конца подписки: inf у бессрочной, None если срок неизвестен."""
        if self.forever:
            return float("inf")
        days = int(self._p.daysLeft())
        return None if days < 0 else days

    @property
    def daysLeft(self):
        return self.days_left

    @property
    def avatar(self):
        """Своя аватарка готовой текстурой — её сразу можно рисовать (ctx.image, ui.image)."""
        return self._p.avatar()

    @property
    def avatar_url(self):
        return str(self._p.avatarUrl())

    @property
    def avatarUrl(self):
        return self.avatar_url

    def avatar_of(self, name):
        """Аватарка любого пользователя клиента по нику."""
        return self._p.avatarOf(str(name))

    def avatarOf(self, name):
        return self.avatar_of(name)

    @property
    def client(self):
        return str(self._p.clientName())

    @property
    def version(self):
        return str(self._p.clientVersion())

    def all(self):
        return _Bag({
            "username": self.username,
            "uid": self.uid,
            "role": self.role,
            "staff": self.staff,
            "admin": self.admin,
            "loaded": self.loaded,
            "subscription": self.subscription,
            "forever": self.forever,
            "expired": self.expired,
            "subscription_end": self.subscription_end,
            "days_left": self.days_left,
            "avatar_url": self.avatar_url,
            "client": self.client,
            "version": self.version,
        })

    def __repr__(self):
        return "<profile %s uid=%d role=%s>" % (self.username or "?", self.uid, self.role)


class _ClientMenu:
    """Меню клиента: какое открыто, где стоят его панели и на каком месте анимация.

    Числа те же, которыми меню рисует себя, поэтому свой слой под ним (menu_render) или над ним
    (post_menu_render) двигается вместе с ним. Значения живые: панели едут на каждом кадре."""
    __slots__ = ("_m",)

    def __init__(self, java):
        self._m = java

    def __call__(self):
        return self.all()

    def __bool__(self):
        return self.opened

    @property
    def opened(self):
        """Меню на экране или доигрывает закрытие."""
        return bool(self._m.opened())

    @property
    def type(self):
        """panel, modern или None, если меню не открыто."""
        value = self._m.type()
        return None if value is None else str(value)

    @property
    def kind(self):
        return self.type

    @property
    def progress(self):
        """Открытость от 0 до 1: 1 — меню на месте, 0 — его нет."""
        return float(self._m.progress())

    @property
    def open(self):
        """Анимация открытия с её кривой: на отскоке уходит за единицу."""
        return float(self._m.open())

    @property
    def close(self):
        """Закрытие от 0 до 1. Идёт и без экрана: меню догорает квадом, улетающим в мир."""
        return float(self._m.close())

    @property
    def closing(self):
        return bool(self._m.closing())

    @property
    def alpha(self):
        """Прозрачность содержимого: игрок держит клавишу «спрятать меню» — она уезжает к нулю."""
        return float(self._m.alpha())

    @property
    def scale(self):
        """Масштаб этого кадра: 0.7 → 1 на открытии."""
        return float(self._m.scale())

    @property
    def x(self):
        return float(self._m.x())

    @property
    def y(self):
        return float(self._m.y())

    @property
    def width(self):
        return float(self._m.width())

    @property
    def w(self):
        return self.width

    @property
    def height(self):
        return float(self._m.height())

    @property
    def h(self):
        return self.height

    @property
    def panels(self):
        """Панели меню: у panel — по одной на категорию, у modern — одно окно."""
        return _py_obj(self._m.panels())

    def panel(self, name):
        """Панель по имени: combat, movement, visuals, player, other у panel; window у modern."""
        return _py_obj(self._m.panel(str(name)))

    def all(self):
        return _py_obj(self._m.all())

    def __repr__(self):
        return "<menu %s progress=%.2f>" % (self.type or "closed", self.progress)


class _Keys:
    """Клавиши и курсор: keys.G даёт код клавиши, down() отвечает, зажата ли она сейчас."""
    __slots__ = ("_k",)

    def __init__(self, java):
        self._k = java

    def __call__(self, name):
        return self.code(name)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        code = self._k.code(name)
        if code == -1:
            raise AttributeError("нет такой клавиши: %s" % name)
        return code

    def code(self, name):
        return self._k.code(str(name))

    def name(self, key):
        return self._k.name(int(key))

    def down(self, key):
        return bool(self._k.down(key))

    def mouse(self, button=0):
        return bool(self._k.mouse(int(button)))

    def x(self):
        return self._k.x()

    def y(self):
        return self._k.y()

    def cursor(self):
        return (self._k.x(), self._k.y())

    def names(self):
        return _java_list(self._k.names())


class _Lang:
    """Переводы скрипта: ключ вместо готовой строки, а язык подставит клиент.

    Имя настройки, значение режима и описание модуля клиент прогоняет через локализацию сам,
    поэтому Slider(mod, "mymod.speed") в меню появится на языке игрока. Ключ без перевода
    показывается как есть - сразу видно, чего не хватает.
    """
    __slots__ = ("_l",)

    def __init__(self, java):
        self._l = java

    def __call__(self, key, *args):
        return self.get(key, *args)

    def get(self, key, *args):
        text = self._l.get(str(key))
        if not args:
            return text
        try:
            # Подстановка делается тут, а не в Java: %s и %d в питоне и в клиенте пишутся одинаково,
            # зато список аргументов не нужно переносить через мост.
            return text % tuple(_unwrap(a) for a in args)
        except Exception:
            return text

    def add(self, language, entries):
        self._l.add(str(language), {str(k): str(v) for k, v in dict(entries).items()})

    def load(self, data, entries=None):
        if entries is not None:
            self.add(data, entries)
            return
        for language, values in dict(data).items():
            self.add(language, values)

    def load_file(self, path):
        self._l.loadFile(str(path))

    def loadFile(self, path):
        self.load_file(path)

    def current(self):
        return self._l.current()

    def has(self, key):
        return bool(self._l.has(str(key)))

    def clear(self):
        self._l.clear()

    def plural(self, count, *forms):
        if len(forms) == 1 and isinstance(forms[0], (list, tuple)):
            forms = tuple(forms[0])
        if not forms:
            return ""
        one = str(forms[0])
        few = str(forms[1]) if len(forms) > 1 else one
        many = str(forms[2]) if len(forms) > 2 else few
        return self._l.plural(float(count), one, few, many)


def _skin_source(value):
    """Источник облика: динамическую текстуру отдаём её ярлыком, остальное снимает _unwrap."""
    if isinstance(value, _DynamicTexture):
        return value.identifier
    return _unwrap(value)


class _EspElement:
    """Свой элемент ESP: цели отбирает клиент галочками в меню, скрипт только рисует."""
    __slots__ = ("_e",)

    def __init__(self, element):
        self._e = element

    @property
    def raw(self):
        return self._e

    @property
    def name(self):
        return self._e.getName()

    def render(self, fn=None):
        """Рисование одной цели: fn(entity, event). Годится и как декоратор."""
        if fn is None:
            return self.render
        self._e.onRender(self._wrap_pair(fn))
        return fn

    def render_all(self, fn=None):
        """Все цели кадра разом: fn(entities, event). Один вызов питона на кадр."""
        if fn is None:
            return self.render_all

        def wrapped(entities, event):
            return fn([_J(e) for e in _java_list(entities)], _J(event))

        self._e.onRenderAll(wrapped)
        return fn

    def filter(self, fn=None):
        """Своя проверка поверх галочек: вернёт False - цель пропускается."""
        if fn is None:
            return self.filter

        def wrapped(entity):
            return fn(_J(entity))

        self._e.onFilter(wrapped)
        return fn

    def _wrap_pair(self, fn):
        # Сущность и событие приходят сырыми объектами игры: оборачиваем, иначе в релизной
        # сборке у них не работали бы named-имена (getX, getBoundingBox и прочие).
        argc = _positional_count(fn)

        def wrapped(entity, event):
            if argc <= 1:
                return fn(_J(entity))
            return fn(_J(entity), _J(event))

        return wrapped

    def enable_for(self, *targets):
        for target in targets:
            self._e.enableFor(str(target))
        return self

    def enabled(self):
        return bool(self._e.isEnabled())

    def remove(self):
        self._e.remove()


class _Esp:
    """ESP клиента: свои элементы рядом со встроенными."""
    __slots__ = ("_esp",)

    def __init__(self, java):
        self._esp = java

    def __call__(self, *args, **kwargs):
        return self.element(*args, **kwargs)

    def element(self, name, targets=("players",), enable=None):
        if isinstance(targets, str):
            targets = (targets,)
        element = _EspElement(self._esp.element(str(name), ",".join(str(t) for t in targets)))
        if enable:
            if isinstance(enable, str):
                enable = (enable,)
            element.enable_for(*enable)
        return element

    def elements(self):
        return _java_list(self._esp.elements())

    def enabled(self):
        return bool(self._esp.enabled())

    def to_screen(self, x, y=None, z=None):
        if y is None:
            x, y, z = x.getX(), x.getY(), x.getZ()
        point = self._esp.toScreen(float(x), float(y), float(z))
        return None if point is None else (float(point[0]), float(point[1]))


class _Skins:
    """Скин и плащ так, как их видит твой клиент.

    Настоящий скин лежит на серверах Mojang: подмена видна только тебе, остальные игроки
    смотрят на родной скин. Правила снимаются вместе со скриптом.

    Цель: ничего или "self" - ты сам, "all" - все игроки сразу, ник или объект игрока -
    конкретный игрок. Источник: ник, путь к png, ссылка, "optifine:ник" для плаща или
    готовая текстура из assets.image(...).
    """
    __slots__ = ("_s",)

    def __init__(self, java):
        self._s = java

    def set(self, target=None, skin=None, cape=None, elytra=None, model=None):
        self._s.set(_unwrap(target), _skin_source(skin), _skin_source(cape), _skin_source(elytra), model)

    def skin(self, target=None, source=None):
        self._s.skin(_unwrap(target), _skin_source(source))

    def cape(self, target=None, source=None):
        self._s.cape(_unwrap(target), _skin_source(source))

    def elytra(self, target=None, source=None):
        self._s.elytra(_unwrap(target), _skin_source(source))

    def model(self, target=None, name=None):
        self._s.model(_unwrap(target), name)

    def me(self, skin=None, cape=None, elytra=None, model=None):
        self._s.set(None, _skin_source(skin), _skin_source(cape), _skin_source(elytra), model)

    def all(self, skin=None, cape=None, elytra=None, model=None):
        self._s.set("all", _skin_source(skin), _skin_source(cape), _skin_source(elytra), model)

    def hide_cape(self, target=None):
        self._s.cape(_unwrap(target), False)

    def reset(self, target=None):
        self._s.reset(_unwrap(target))

    def clear(self):
        self._s.clear()

    def targets(self):
        return _java_list(self._s.targets())

    def get(self, target=None):
        value = self._s.get(_unwrap(target))
        return _py_obj(value)


class _Target:
    """Выбор цели правилами боевых модулей клиента: тот же фильтр и та же сортировка."""
    __slots__ = ("_t",)

    _FLAGS = (
        ("players", "players"),
        ("animals", "animals"),
        ("mobs", "mobs"),
        ("users", "users"),
        ("invisibles", "invisibles"),
        ("naked", "naked"),
        ("friends", "friends"),
        ("armor_stands", "armorStands"),
        ("exclude_teammates", "excludeTeammates"),
    )

    def __init__(self, java):
        self._t = java

    def _query(self, kwargs):
        query = self._t.query()
        for name, method in self._FLAGS:
            if name in kwargs:
                getattr(query, method)(bool(kwargs[name]))
        if "range" in kwargs and kwargs["range"] is not None:
            query.range(float(kwargs["range"]))
        if "sort" in kwargs and kwargs["sort"] is not None:
            query.sort(str(kwargs["sort"]))
        return query

    def best(self, **kwargs):
        return _wrap(self._t.best(self._query(kwargs)))

    def all(self, **kwargs):
        return [_wrap(entity) for entity in _java_list(self._t.all(self._query(kwargs)))]

    def valid(self, entity, **kwargs):
        return bool(self._t.valid(self._query(kwargs), _unwrap(entity)))

    def current(self):
        return _wrap(self._t.current())

    def living(self):
        return _wrap(self._t.living())

    # приоритетные ники клиента (то же, что команда .target)
    def add(self, name):
        self._t.add(str(name))
        return self

    def remove(self, name):
        self._t.remove(str(name))
        return self

    def clear(self):
        self._t.clear()
        return self

    def is_target(self, name):
        return bool(self._t.isTarget(str(name)))

    def list(self):
        return [str(name) for name in _java_list(self._t.list())]


class _FunTime:
    """Данные FunTime: ивенты, шахты, данжи, города стража, игроки, баны, капча."""
    __slots__ = ("_f",)

    def __init__(self, java):
        self._f = java

    def ready(self):
        return bool(self._f.ready())

    # --- уже собрано трекерами, без сети ---

    def events(self):
        return _py_obj(self._f.events())

    def mines(self):
        return _py_obj(self._f.mines())

    def copper_dungeons(self):
        return _py_obj(self._f.copperDungeons())

    def warden_cities(self):
        return _py_obj(self._f.wardenCities())

    def system_info(self):
        return _py_obj(self._f.systemInfo())

    # --- запросы к серверу: результат приходит в колбэк ---

    def fetch_events(self, callback, params=None):
        self._f.fetchEvents(self._params(params), self._wrap_callback(callback))

    def fetch_mines(self, callback, params=None):
        self._f.fetchMines(self._params(params), self._wrap_callback(callback))

    def fetch_players(self, callback, params=None):
        self._f.fetchPlayers(self._params(params), self._wrap_callback(callback))

    def fetch_bans(self, callback, params=None):
        self._f.fetchBans(self._params(params), self._wrap_callback(callback))

    def fetch_copper_dungeon(self, callback):
        self._f.fetchCopperDungeon(self._wrap_callback(callback))

    def fetch_warden_city(self, callback):
        self._f.fetchWardenCity(self._wrap_callback(callback))

    def solve_captcha(self, base64, callback):
        self._f.solveCaptcha(str(base64), self._wrap_callback(callback))

    @staticmethod
    def _params(params):
        if not params:
            return None
        return {str(key): str(value) for key, value in params.items()}

    @staticmethod
    def _wrap_callback(callback):
        def wrapped(value):
            callback(_py_obj(value))

        return wrapped


class _Music:
    """Музыка из Dynamic Island: сессия ОС, обложка и текст с таймкодами."""
    __slots__ = ("_m",)

    def __init__(self, java):
        self._m = java

    def __call__(self):
        return self.current()

    def active(self):
        return bool(self._m.active())

    def current(self):
        return _py_obj(self._m.current())

    def info(self):
        return self.current()

    def playing(self):
        return bool(self._m.playing())

    def position(self):
        return float(self._m.position())

    def position_ms(self):
        return int(self._m.positionMs())

    def duration(self):
        return int(self._m.duration())

    def duration_ms(self):
        return int(self._m.durationMs())

    def progress(self):
        return float(self._m.progress())

    def bpm(self):
        return float(self._m.bpm())

    def color(self):
        return self._m.color()

    def artwork(self):
        return self._m.artwork()

    def lyrics_synced(self):
        return bool(self._m.lyricsSynced())

    def lyrics(self):
        return _py_obj(self._m.lyrics())

    def lyric_at(self, time_ms):
        return _py_obj(self._m.lyricAt(float(time_ms)))

    def line_at(self, time_ms):
        return self.lyric_at(time_ms)

    def at(self, time_ms):
        return self.lyric_at(time_ms)

    def current_lyric(self):
        return _py_obj(self._m.currentLyric())

    def lyric(self):
        return self.current_lyric()

    def play(self):
        return bool(self._m.play())

    def pause(self):
        return bool(self._m.pause())

    def toggle(self):
        return bool(self._m.toggle())

    def next(self):
        return bool(self._m.next())

    def previous(self):
        return bool(self._m.previous())

    def stop(self):
        return bool(self._m.stop())


class _CommandCtx:
    """Что пришло с командой: имя, аргументы и быстрые ответы в чат."""
    __slots__ = ("name", "args", "_messages")

    def __init__(self, name, args, messages):
        self.name = name
        self.args = args
        self._messages = messages

    def get(self, index, default=None):
        try:
            value = self.args[index]
        except (IndexError, KeyError, TypeError):
            return default
        return default if value is None else value

    def msg(self, text):
        self._messages.info(text)

    def warn(self, text):
        self._messages.warn(text)

    def error(self, text):
        self._messages.error(text)

    def overlay(self, text):
        self._messages.overlay(text)

    def __len__(self):
        return len(self.args)

    def __getitem__(self, index):
        return self.args[index]

    def __iter__(self):
        return iter(self.args)


_ARG_TYPES = {int: "int", float: "float", bool: "bool", str: "str"}


def _command_args(fn, suggests):
    """Аргументы команды из сигнатуры: имя, тип по аннотации, обязательность по умолчанию."""
    try:
        params = list(inspect.signature(fn).parameters.values())
    except Exception:
        return [], False, False

    takes_ctx = bool(params)
    out = []
    vararg = False
    for param in params[1:]:
        if param.kind in (param.KEYWORD_ONLY, param.VAR_KEYWORD):
            continue

        annotation = param.annotation
        if annotation in _ARG_TYPES:
            kind = _ARG_TYPES[annotation]
        elif isinstance(annotation, str):
            kind = annotation.lower()
        else:
            kind = "str"

        is_vararg = param.kind == param.VAR_POSITIONAL
        vararg = vararg or is_vararg
        required = not is_vararg and param.default is inspect.Parameter.empty
        out.append((param.name, kind, required, is_vararg, suggests.get(param.name)))
    return out, takes_ctx, vararg


class _Command:
    """Команда чата, объявленная скриптом. У неё же просят подкоманды."""
    __slots__ = ("_c", "_fn", "_api")

    def __init__(self, java_command, fn, api):
        self._c = java_command
        self._fn = fn
        self._api = api

    @property
    def name(self):
        return self._c.name()

    @property
    def raw(self):
        return self._c

    def sub(self, name, desc="", aliases=None, suggests=None):
        """Декоратор подкоманды: @mycmd.sub("add")."""

        def deco(fn):
            child = self._c.sub(str(name))
            self._api._configure(child, fn, desc, aliases, suggests)
            self._c.install()
            return _Command(child, fn, self._api)

        return deco

    def remove(self):
        return bool(self._c.remove())

    def __call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)


class _Commands:
    """Свои команды чата и справка по чужим."""
    __slots__ = ("_c", "_messages")

    def __init__(self, java, messages):
        self._c = java
        self._messages = messages

    def __call__(self, name, **kwargs):
        return self.add(name, **kwargs)

    def add(self, name, fn=None, desc="", aliases=None, suggests=None):
        """Создать команду. Без fn работает как декоратор: @command("hello")."""
        if fn is None:
            def deco(handler):
                return self.add(name, handler, desc, aliases, suggests)

            return deco

        java_command = self._c.create(str(name))
        self._configure(java_command, fn, desc, aliases, suggests)
        java_command.install()
        return _Command(java_command, fn, self)

    def remove(self, target):
        if isinstance(target, _Command):
            return target.remove()
        return bool(self._c.remove(str(target)))

    def exists(self, name):
        return bool(self._c.exists(str(name)))

    def all(self):
        return _java_list(self._c.names())

    def run(self, line):
        return bool(self._c.run(str(line)))

    def prefix(self):
        return self._c.prefix()

    def _configure(self, java_command, fn, desc, aliases, suggests):
        suggests = dict(suggests or {})
        # Описание для .help берём из docstring, если явного нет: меньше писанины в скрипте.
        text = str(desc or "").strip()
        if not text and getattr(fn, "__doc__", None):
            text = fn.__doc__.strip().split("\n")[0]
        java_command.desc(text)

        for alias in aliases or []:
            java_command.alias(str(alias))

        args, takes_ctx, has_vararg = _command_args(fn, suggests)
        for arg_name, kind, required, is_vararg, arg_suggests in args:
            java_command.arg(str(arg_name), str(kind), bool(required), bool(is_vararg), arg_suggests)

        java_command.handler(self._wrap(fn, takes_ctx, has_vararg))

    def _wrap(self, fn, takes_ctx, has_vararg):
        messages = self._messages

        def handler(name, raw):
            values = raw if isinstance(raw, list) else _java_list(raw)
            values = list(values)

            tail = []
            if has_vararg and values:
                last = values.pop()
                tail = list(last if isinstance(last, list) else _java_list(last))

            # Необязательные аргументы, которых игрок не написал, приходят как None:
            # обрезаем хвост, чтобы сработали значения по умолчанию из сигнатуры.
            while values and values[-1] is None:
                values.pop()

            if not takes_ctx:
                return fn()
            return fn(_CommandCtx(str(name), values + tail, messages), *values, *tail)

        return handler


class _UiCtx:
    __slots__ = ("_b", "_node")

    def __init__(self, builder, node):
        self._b = builder
        self._node = node

    def __enter__(self):
        self._b._stack.append(self._node)
        return self._node

    def __exit__(self, *exc):
        self._b._stack.pop()
        return False


class _UiBuilder:
    """Дерево UI скрипта. Фабрики возвращают Node; контейнеры (column/row) — контекст-менеджеры
    для with-вложенности. Вся композиция пишется в скрипте; Java — только примитивы."""

    def __init__(self, java_ui, title, width, height, window=True):
        self._ui = java_ui
        self._title = title
        self._w = width
        self._h = height
        self._stack = []
        self._rooted = False
        self._window = window

    def _attach(self, node, container):
        if self._stack:
            self._stack[-1].add(node)
        else:
            if container and not self._rooted:
                if self._window:
                    node.window(float(self._w), float(self._h), str(self._title))
                self._rooted = True
            self._ui.addRoot(node)
        return node

    def _style(self, node, kw):
        for k, v in kw.items():
            if v is None:
                continue
            if k == "width": node.width(float(v))
            elif k == "height": node.height(float(v))
            elif k == "size": node.size(float(v[0]), float(v[1]))
            elif k == "min_size": node.minSize(float(v[0]), float(v[1]))
            elif k == "max_size": node.maxSize(float(v[0]), float(v[1]))
            elif k == "gap": node.gap(float(v))
            elif k in ("pad", "padding"):
                if isinstance(v, (tuple, list)):
                    node.pad(float(v[0]), float(v[1]))
                else:
                    node.pad(float(v))
            elif k == "radius": node.radius(float(v))
            elif k == "radius_bottom": node.radiusBottom(float(v))
            elif k == "squircle": node.squircle(float(v))
            elif k == "blur":
                if isinstance(v, (tuple, list)):
                    node.blur(float(v[0]), v[1])
                else:
                    node.blur(float(v))
            elif k == "glass":
                if isinstance(v, (tuple, list)):
                    node.glass(float(v[0]), bool(v[1]))
                elif v is True:
                    node.glass()
                else:
                    node.glass(float(v), True)
            elif k == "fill" and v: node.fill()
            elif k == "fill_width" and v: node.fillWidth()
            elif k == "fill_height" and v: node.fillHeight()
            elif k in ("color", "bg"):
                node.colorFn(v) if callable(v) else node.color(v)
            elif k == "border": node.border(float(v[0]), v[1])
            elif k == "align": node.align(str(v))
            elif k == "justify": node.justify(str(v))
            elif k == "direction": node.direction(str(v))
            elif k == "columns": node.columns(int(v))
            elif k == "wrap" and v: node.wrap()
            elif k == "scroll" and v: node.scrollable()
            elif k == "stack" and v: node.stack()
            elif k == "scrollbar": node.scrollbar(str(v))
            elif k == "stagger": node.stagger(float(v))
            elif k == "draggable":
                node.draggable(str(v)) if isinstance(v, str) else (node.draggable() if v else None)
            elif k == "cursor": node.cursor(str(v))
            elif k == "interactive": node.interactive(bool(v))
            elif k == "fade" and v: node.fade()
            elif k == "center" and v: node.center()
            elif k == "on_click": node.onClick(v)
            elif k == "on_click_pos": node.onClickPos(v)
            elif k == "visible_when": node.visibleWhen(v)
            elif k == "enter": node.enter(str(v))
            elif k == "exit": node.exit(str(v))
            elif k == "enter_slide": node.enterSlide(float(v))
            elif k == "exit_slide": node.exitSlide(float(v))
            elif k == "motion": node.motion(str(v))
            elif k == "sticky" and v: node.sticky()
            elif k == "collapse" and v: node.collapse()
        return node

    # ---- контейнеры (with) ----
    def column(self, **kw):
        return _UiCtx(self, self._style(self._attach(self._ui.column(), True), kw))

    def row(self, **kw):
        return _UiCtx(self, self._style(self._attach(self._ui.row(), True), kw))

    # ---- виджеты-листья ----
    def text(self, value, size=0, weight="medium", color=None, **kw):
        if callable(value):
            node = self._ui.textDyn(value, float(size), str(weight), color)
        else:
            node = self._ui.text(str(value), float(size), str(weight), color)
        return self._style(self._attach(node, False), kw)

    def button(self, label, **kw):
        return self._style(self._attach(self._ui.button(str(label)), False), kw)

    def switch(self, get, set, **kw):
        return self._style(self._attach(self._ui.switchWidget(get, set), False), kw)

    def toggle(self, label, get, set, **kw):
        return self._style(self._attach(self._ui.toggle(str(label), get, set), False), kw)

    def slider(self, label, lo, hi, value=0.0, on_change=None, step=0.0, **kw):
        node = self._ui.slider(str(label), float(lo), float(hi), float(value), on_change, float(step))
        return self._style(self._attach(node, False), kw)

    def slider_bar(self, get, set, lo, hi, step=0.0, **kw):
        node = self._ui.sliderBar(get, set, float(lo), float(hi), float(step))
        return self._style(self._attach(node, False), kw)

    # перекрашиваемые виджеты (для кастомного рендера настроек)
    def toggle_c(self, get, on_click, on=None, off=None, knob=None, **kw):
        return self._style(self._attach(self._ui.toggleC(get, on_click, on, off, knob), False), kw)

    def slider_c(self, get, set, lo, hi, step=0.0, track=None, fill=None, ring=None, inner=None,
                 thumb_radius=-1.0, thumb_border=-1.0, track_height=-1.0, **kw):
        node = self._ui.sliderC(get, set, float(lo), float(hi), float(step), track, fill, ring, inner,
                                float(thumb_radius), float(thumb_border), float(track_height))
        return self._style(self._attach(node, False), kw)

    def text_input(self, get, set, placeholder="", bg=None, color=None, size=0, weight="regular", **kw):
        node = self._ui.textInput(get, set, str(placeholder), bg, color, float(size), str(weight))
        return self._style(self._attach(node, False), kw)

    def swatch(self, get, **kw):
        return self._style(self._attach(self._ui.swatch(get), False), kw)

    def setting(self, s, **kw):
        return self._style(self._attach(self._ui.setting(s), False), kw)

    def icon(self, name, size=10, color=None, **kw):
        return self._style(self._attach(self._ui.icon(str(name), float(size), color), False), kw)

    def image(self, texture, size=10, color=None, radius=0, **kw):
        return self._style(self._attach(self._ui.image(texture, float(size), float(radius), color), False), kw)

    def effect(self, effect, size=12, color=None, **kw):
        """Иконка эффекта. Передал функцию - иконка меняется вместе с тем, что она вернёт."""
        value = effect if callable(effect) else _effect_arg(effect)
        return self._style(self._attach(self._ui.effect(value, float(size), color), False), kw)

    def space(self, px=4):
        return self._attach(self._ui.space(float(px)), False)

    def divider(self, **kw):
        return self._style(self._attach(self._ui.divider(), False), kw)

    def raw(self, element):
        return self._attach(self._ui.node(_unwrap(element)), False)

    # ---- тема-цвета ----
    def color(self, name):
        return self._ui.color(str(name))


class _Menu:
    __slots__ = ("_title", "_w", "_h", "_build", "_screen")

    def __init__(self, title, width, height, build):
        self._title = title
        self._w = width
        self._h = height
        self._build = build
        self._screen = None

    def open(self):
        build, title, w, h = self._build, self._title, self._w, self._h

        def _builder(java_ui):
            build(_UiBuilder(java_ui, title, w, h))

        self._screen = PyScreen(_builder)
        self._screen.open()
        return self

    def close(self):
        if self._screen is not None:
            # closeScreen(), а не close(): close() — override ванильного Screen.close(),
            # после ремапа он зовётся method_25419 и по имени "close" не находится.
            self._screen.closeScreen()

    @property
    def opened(self):
        return self._screen is not None


def screen(title="", width=320, height=240):
    def deco(build):
        return _Menu(title, width, height, build)
    return deco


class _RawDrawContext:
    """Контекст «голого» (immediate) рисования для raw_screen — абсолютные координаты."""
    __slots__ = ("context", "width", "height", "_fonts", "_border")

    def __init__(self, context, width, height, fonts, border):
        self.context = context
        self.width = float(width)
        self.height = float(height)
        self._fonts = fonts
        self._border = border

    @property
    def mouse_x(self):
        return int(self.context.getMouseX())

    @property
    def mouse_y(self):
        return int(self.context.getMouseY())

    @property
    def delta(self):
        return float(self.context.getDelta())

    def font(self, weight="medium", size=8):
        return self._fonts.get(weight, size)

    def rect(self, x, y, w, h, color=None):
        self.context.drawRect(float(x), float(y), float(w), float(h),
                              ColorRGBA.WHITE if color is None else color)
        return self

    def shader(self, shader, x, y, w, h):
        shader.rect(self.context, float(x), float(y), float(w), float(h))
        return self

    def rounded_rect(self, x, y, w, h, radius=6, color=None):
        br = self._border(radius) if isinstance(radius, (int, float)) else radius
        self.context.drawRoundedRect(float(x), float(y), float(w), float(h), br,
                                     ColorRGBA.WHITE if color is None else color)
        return self

    def border(self, x, y, w, h, radius=6, thickness=1, color=None):
        br = self._border(radius) if isinstance(radius, (int, float)) else radius
        self.context.drawRoundedBorder(float(x), float(y), float(w), float(h), float(thickness), br,
                                       ColorRGBA.WHITE if color is None else color)
        return self

    def client_rect(self, x, y, w, h, alpha=1.0, drag=0.0, squircle=3):
        self.context.drawClientRect(float(x), float(y), float(w), float(h),
                                    float(alpha), float(drag), float(squircle))
        return self

    def text(self, value, x, y, size=8, weight="medium", color=None, font=None,
             outline=None, outline_width=1, outline_steps=0):
        f = font or self.font(weight, size)
        fill = ColorRGBA.WHITE if color is None else color
        if outline is None:
            self.context.drawText(f, str(value), float(x), float(y), fill)
        else:
            self.context.drawTextWithOutline(f, str(value), float(x), float(y), fill, outline, float(outline_width),
                                             int(outline_steps))
        return self

    def centered_text(self, value, x, y, size=8, weight="medium", color=None, font=None,
                      outline=None, outline_width=1, outline_steps=0):
        f = font or self.font(weight, size)
        fill = ColorRGBA.WHITE if color is None else color
        if outline is None:
            self.context.drawCenteredText(f, str(value), float(x), float(y), fill)
        else:
            self.context.drawCenteredTextWithOutline(f, str(value), float(x), float(y), fill, outline, float(outline_width),
                                                     int(outline_steps))
        return self

    def right_text(self, value, x, y, size=8, weight="medium", color=None, font=None,
                   outline=None, outline_width=1, outline_steps=0):
        f = font or self.font(weight, size)
        fill = ColorRGBA.WHITE if color is None else color
        if outline is None:
            self.context.drawRightText(f, str(value), float(x), float(y), fill)
        else:
            self.context.drawRightTextWithOutline(f, str(value), float(x), float(y), fill, outline, float(outline_width),
                                                  int(outline_steps))
        return self

    def icon(self, name, x, y, size=8, color=None):
        self.context.drawIcon(str(name), float(x), float(y), float(size),
                              ColorRGBA.WHITE if color is None else color)
        return self

    def effect(self, effect, x, y, size=10, color=None):
        """Ванильная иконка эффекта: сам эффект или его id строкой."""
        self.context.drawEffect(_effect_arg(effect), float(x), float(y), float(size),
                                ColorRGBA.WHITE if color is None else color)
        return self

    def image(self, texture, x, y, w, h, color=None, radius=0):
        tint = ColorRGBA.WHITE if color is None else color
        if radius:
            br = self._border(radius) if isinstance(radius, (int, float)) else radius
            self.context.drawRoundedTexture(_unwrap(texture), float(x), float(y), float(w), float(h), br, tint)
        else:
            self.context.drawTexture(_unwrap(texture), float(x), float(y), float(w), float(h), tint)
        return self

    def texture(self, texture, x, y, w, h, color=None, radius=0):
        return self.image(texture, x, y, w, h, color, radius)

    def raw(self):
        return self.context


class _RawMenu:
    """Экран без лейаута: каждый кадр зовётся render(ctx) с _RawDrawContext (immediate)."""
    __slots__ = ("_title", "_w", "_h", "_render", "_click", "_release", "_key", "_move", "_close", "_fonts", "_border", "_screen")

    def __init__(self, title, width, height, render, fonts, border):
        self._title = title
        self._w = width
        self._h = height
        self._render = render
        self._click = None
        self._release = None
        self._key = None
        self._move = None
        self._close = None
        self._fonts = fonts
        self._border = border
        self._screen = None

    def render(self, fn):
        self._render = fn
        return fn

    def on_click(self, fn):
        self._click = fn
        return fn

    def on_release(self, fn):
        self._release = fn
        return fn

    def on_key(self, fn):
        self._key = fn
        return fn

    def on_mouse_move(self, fn):
        self._move = fn
        return fn

    def on_close(self, fn):
        self._close = fn
        return fn

    def open(self):
        scr = PyScreen()
        scr.immediate(self._wrap_render())
        if self._click is not None:
            scr.onClick(self._wrap_click(self._click))
        if self._release is not None:
            scr.onRelease(self._wrap_click(self._release))
        if self._key is not None:
            scr.onKey(self._wrap_key(self._key))
        if self._move is not None:
            scr.onMouseMove(self._wrap_move(self._move))
        if self._close is not None:
            scr.onClose(self._close)
        scr.open()
        self._screen = scr
        return self

    def close(self):
        if self._screen is not None:
            # closeScreen(), а не close(): close() — override ванильного Screen.close(),
            # после ремапа он зовётся method_25419 и по имени "close" не находится.
            self._screen.closeScreen()

    @property
    def opened(self):
        return self._screen is not None

    def _wrap_render(self):
        fn, fonts, border = self._render, self._fonts, self._border

        def wrapped(context, width, height):
            fn(_RawDrawContext(context, width, height, fonts, border))

        return wrapped

    def _wrap_click(self, fn):
        def wrapped(mx, my, btn):
            fn(float(mx), float(my), str(btn))

        return wrapped

    def _wrap_key(self, fn):
        def wrapped(key, scan, modifiers, pressed):
            fn(int(key), int(scan), int(modifiers), bool(pressed))

        return wrapped

    def _wrap_move(self, fn):
        def wrapped(mx, my):
            fn(float(mx), float(my))

        return wrapped


def __rockstar_make_ns(_events, _client, _mc, _gv, _py_aura=None, _py_rotations=None):
    if _py_aura is None:
        from pyrock.classes.aura import PyAura
        _py_aura = PyAura()
    if _py_rotations is None:
        from pyrock.classes import PyRotations
        _py_rotations = PyRotations()

    _module = _Factory(PyModule)
    _color = _ColorFactory()
    _border = _Border(_client)
    _client_api = _ClientApi(_client, _gv, _border)
    _hud = _HudApi(PyHud(), _client_api.fonts, _border)
    _client_api.hud = _hud
    _island = _IslandApi(_client.island(), _client_api.fonts, _border)
    _client_api.island = _island
    _island_status = _IslandStatusFactory(_island)
    _mc_api = _J(_mc)
    _rotations = _Rotations(_py_rotations)
    _aura = _Aura(_py_aura, _rotations)
    _world = _World(_mc_api, _aura)
    _container = _Container(PyContainer())
    _storage = _Storage(_client_api.paths)
    _vec = _Vec()
    _assets = _Assets(PyAssets())
    _render3d = _Render3D(PyRender3D(), _world)
    _shader = _ShaderApi(PyShaders())
    _sound = _SoundApi(PySounds())
    _newton = _Newton(PyNewton())
    _commands = _Commands(PyCommands(), _client_api.messages)
    _client_api.commands = _commands
    _notify = _Notify(PyNotify())
    _inventory = _Inventory(PyInventory())
    _effects = _Effects(PyEffects())
    _theme = _Theme(PyTheme())
    _target = _Target(PyTarget())
    _funtime = _FunTime(PyFunTime())
    _keys = _Keys(PyKeys())
    _skins = _Skins(PySkins())
    _esp = _Esp(PyEsp())
    _lang = _Lang(PyLang())
    _profile = _Profile(PyProfile())
    _client_api.profile = _profile
    _menu = _ClientMenu(PyMenu())
    _client_api.menu = _menu
    _music = _client_api.music

    def _raw_screen(title="", width=320, height=240):
        def deco(render):
            return _RawMenu(title, width, height, render, _client_api.fonts, _border)
        return deco

    return {
        "Module": _module,
        "Color": _color,
        "ColorRGBA": ColorRGBA,
        "border4": (lambda a, b, c, d: _client.border4(a, b, c, d)),
        "Checkbox": _Factory(PyBooleanSetting),
        "Slider": _Factory(PySliderSetting),
        "Mode": _Factory(PyModeSetting),
        "Select": _Factory(PySelectSetting),
        "Button": _Factory(PyButtonSetting),
        "Range": _Factory(PyRangeSetting),
        "ColorSetting": _Factory(PyColorSetting),
        "Bind": _Factory(PyBindSetting),
        "TextSetting": _Factory(PyTextSetting),
        "TimeSetting": _Factory(PyTimeSetting),
        "Info": _Factory(PyInfoSetting),
        "Gradient": _Factory(PyGradientSetting),
        "PositionSetting": _Factory(PyPositionSetting),
        "Bezier": _Factory(PyBezierSetting),
        "Blocks": _Factory(PyBlockSetting),
        "module": _module,
        "checkbox": _Factory(PyBooleanSetting),
        "slider": _Factory(PySliderSetting),
        "mode": _Factory(PyModeSetting),
        "select": _Factory(PySelectSetting),
        "button": _Factory(PyButtonSetting),
        "colorsetting": _Factory(PyColorSetting),
        "bind": _Factory(PyBindSetting),
        "textsetting": _Factory(PyTextSetting),
        "timesetting": _Factory(PyTimeSetting),
        "info": _Factory(PyInfoSetting),
        "gradient": _Factory(PyGradientSetting),
        "positionsetting": _Factory(PyPositionSetting),
        "bezier": _Factory(PyBezierSetting),
        "blocks": _Factory(PyBlockSetting),
        "color": _color,
        "border": _border,
        "events": _Events(_events),
        "client": _client_api,
        "client_raw": _client,
        "modules": _client_api.modules,
        "settings": _client_api.settings,
        "messages": _client_api.messages,
        "ui": _client_api.ui,
        "hud": _hud,
        "HUD": _hud,
        "Hud": _hud,
        "island": _island,
        "dynamic_island": _island,
        "DynamicIsland": _island,
        "IslandStatus": _island_status,
        "island_status": _island_status,
        "screen": screen,
        "raw_screen": _raw_screen,
        "screen_raw": _raw_screen,
        "paths": _client_api.paths,
        "fonts": _client_api.fonts,
        "assets": _assets,
        "image": _assets.image,
        "texture": _assets.texture,
        "custom_font": _assets.font,
        "customFont": _assets.font,
        "mc": _mc_api,
        "jimport": jimport,
        "wrap": _wrap,
        "unwrap": _unwrap,
        "is_instance": _is_instance,
        "isInstance": _is_instance,
        "font": _client_api.fonts,
        "print": print,
        "aura": _aura,
        "world": _world,
        "newton": _newton,
        "commands": _commands,
        "command": _commands.add,
        "Command": _commands,
        "notify": _notify,
        "inventory": _inventory,
        "inv": _inventory,
        "container": _container,
        "chest": _container,
        "effects": _effects,
        "buffs": _effects,
        "theme": _theme,
        "colors": _theme,
        "target": _target,
        "funtime": _funtime,
        "ft": _funtime,
        "music": _music,
        "keys": _keys,
        "skins": _skins,
        "skin": _skins,
        "lang": _lang,
        "tr": _lang,
        "profile": _profile,
        "account": _profile,
        "user": _profile,
        "menu": _menu,
        "esp": _esp,
        "Esp": _esp,
        "ESP": _esp,
        "rotations": _rotations,
        "render3d": _render3d,
        "render_3d": _render3d,
        "shader": _shader,
        "shaders": _shader,
        "Shader": _shader,
        "sound": _sound,
        "sounds": _sound,
        "audio": _sound,
        "Timer": PyTimer,
        "storage": _storage,
        "Storage": _storage,
        "vec": _vec,
    }
