#version 150

in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0; // цвет сцены
uniform sampler2D Sampler1; // глубина сцены

uniform mat4 InvViewProj;
uniform float Ambient; // сколько света достаётся грани, отвёрнутой от источника (0..1)

uniform vec4 L0Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L0Col; // rgb — цвет, a — яркость
uniform vec4 L1Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L1Col; // rgb — цвет, a — яркость
uniform vec4 L2Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L2Col; // rgb — цвет, a — яркость
uniform vec4 L3Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L3Col; // rgb — цвет, a — яркость
uniform vec4 L4Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L4Col; // rgb — цвет, a — яркость
uniform vec4 L5Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L5Col; // rgb — цвет, a — яркость
uniform vec4 L6Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L6Col; // rgb — цвет, a — яркость
uniform vec4 L7Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L7Col; // rgb — цвет, a — яркость
uniform vec4 L8Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L8Col; // rgb — цвет, a — яркость
uniform vec4 L9Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L9Col; // rgb — цвет, a — яркость
uniform vec4 L10Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L10Col; // rgb — цвет, a — яркость
uniform vec4 L11Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L11Col; // rgb — цвет, a — яркость
uniform vec4 L12Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L12Col; // rgb — цвет, a — яркость
uniform vec4 L13Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L13Col; // rgb — цвет, a — яркость
uniform vec4 L14Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L14Col; // rgb — цвет, a — яркость
uniform vec4 L15Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L15Col; // rgb — цвет, a — яркость
uniform vec4 L16Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L16Col; // rgb — цвет, a — яркость
uniform vec4 L17Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L17Col; // rgb — цвет, a — яркость
uniform vec4 L18Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L18Col; // rgb — цвет, a — яркость
uniform vec4 L19Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L19Col; // rgb — цвет, a — яркость
uniform vec4 L20Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L20Col; // rgb — цвет, a — яркость
uniform vec4 L21Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L21Col; // rgb — цвет, a — яркость
uniform vec4 L22Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L22Col; // rgb — цвет, a — яркость
uniform vec4 L23Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L23Col; // rgb — цвет, a — яркость
uniform vec4 L24Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L24Col; // rgb — цвет, a — яркость
uniform vec4 L25Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L25Col; // rgb — цвет, a — яркость
uniform vec4 L26Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L26Col; // rgb — цвет, a — яркость
uniform vec4 L27Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L27Col; // rgb — цвет, a — яркость
uniform vec4 L28Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L28Col; // rgb — цвет, a — яркость
uniform vec4 L29Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L29Col; // rgb — цвет, a — яркость
uniform vec4 L30Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L30Col; // rgb — цвет, a — яркость
uniform vec4 L31Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L31Col; // rgb — цвет, a — яркость
uniform vec4 L32Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L32Col; // rgb — цвет, a — яркость
uniform vec4 L33Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L33Col; // rgb — цвет, a — яркость
uniform vec4 L34Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L34Col; // rgb — цвет, a — яркость
uniform vec4 L35Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L35Col; // rgb — цвет, a — яркость
uniform vec4 L36Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L36Col; // rgb — цвет, a — яркость
uniform vec4 L37Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L37Col; // rgb — цвет, a — яркость
uniform vec4 L38Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L38Col; // rgb — цвет, a — яркость
uniform vec4 L39Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L39Col; // rgb — цвет, a — яркость
uniform vec4 L40Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L40Col; // rgb — цвет, a — яркость
uniform vec4 L41Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L41Col; // rgb — цвет, a — яркость
uniform vec4 L42Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L42Col; // rgb — цвет, a — яркость
uniform vec4 L43Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L43Col; // rgb — цвет, a — яркость
uniform vec4 L44Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L44Col; // rgb — цвет, a — яркость
uniform vec4 L45Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L45Col; // rgb — цвет, a — яркость
uniform vec4 L46Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L46Col; // rgb — цвет, a — яркость
uniform vec4 L47Pos; // xyz — позиция относительно камеры, w — радиус (0 = слот пуст)
uniform vec4 L47Col; // rgb — цвет, a — яркость

out vec4 OutColor;

// Скорость выхода на насыщение. Свет ДОМНОЖАЕТ картинку, а не кладётся сверху: только так
// проявляется текстура блока — иначе получается цветная плёнка.
const float GAIN = 2.0;
// Во столько раз ярче исходного пикселя может стать полностью засвеченная поверхность.
const float BOOST = 1.7;
// Небольшая добавка сверху, чтобы источник читался и на совсем чёрной поверхности.
const float LIFT = 0.12;

vec3 worldFromDepth(vec2 uv, float depth) {
    vec4 clip = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 pos = InvViewProj * clip;
    return pos.xyz / pos.w;
}

/**
 * Нормаль грани из буфера глубины. Наивный cross(dFdx, dFdy) врёт на каждом силуэте: соседний
 * пиксель там принадлежит другой поверхности, и нормаль уезжает поперёк экрана — по краям
 * блоков это давало дрожащие светлые каёмки. Поэтому по каждой оси берём того соседа, у
 * которого скачок глубины меньше: он почти наверняка лежит на той же грани.
 */
vec3 faceNormal(vec2 uv, float depth, vec3 world) {
    vec2 texel = 1.0 / vec2(textureSize(Sampler1, 0));

    vec2 uvL = uv - vec2(texel.x, 0.0);
    vec2 uvR = uv + vec2(texel.x, 0.0);
    vec2 uvD = uv - vec2(0.0, texel.y);
    vec2 uvU = uv + vec2(0.0, texel.y);

    float dL = texture(Sampler1, uvL).r;
    float dR = texture(Sampler1, uvR).r;
    float dD = texture(Sampler1, uvD).r;
    float dU = texture(Sampler1, uvU).r;

    vec3 ddx = abs(dL - depth) < abs(dR - depth)
        ? world - worldFromDepth(uvL, dL)
        : worldFromDepth(uvR, dR) - world;

    vec3 ddy = abs(dD - depth) < abs(dU - depth)
        ? world - worldFromDepth(uvD, dD)
        : worldFromDepth(uvU, dU) - world;

    vec3 n = cross(ddx, ddy);
    float len = length(n);
    // Вырожденный случай (плоскость строго вдоль луча, дыры в глубине) — смотрим в камеру.
    if (len < 1e-8) return normalize(-world);

    n /= len;
    // Камера в начале координат, поэтому разворачиваем нормаль к ней: знак векторного
    // произведения зависит от обхода.
    return dot(n, -world) < 0.0 ? -n : n;
}

// Точечный источник как факел: квадратичное затухание по расстоянию, умноженное на N·L —
// грань, отвёрнутая от партикла, остаётся тёмной, обращённая к нему светится.
vec3 contribution(vec3 world, vec3 normal, vec4 posRad, vec4 col) {
    float radius = posRad.w;
    if (radius <= 0.0001 || col.a <= 0.0001) return vec3(0.0);

    vec3 delta = posRad.xyz - world;
    float d = length(delta);
    if (d >= radius) return vec3(0.0);

    // Квадрат тут врал вдвое: при радиусе 10 на пяти блоках оставалось 25 %, и радиус читался
    // как «половина от выставленного». smoothstep держит середину на 0.5 и всё так же приходит
    // в ноль с нулевой производной — на границе сферы канта не видно.
    float falloff = smoothstep(0.0, 1.0, 1.0 - d / radius);

    float ndotl = d > 0.0001 ? dot(normal, delta / d) : 1.0;
    // Wrapped diffuse вместо mix(Ambient, 1, ndotl): у mix даже полностью отвёрнутая грань
    // получала долю Ambient, из-за чего источник за стеной подсвечивал её лицевую сторону.
    // Здесь Ambient лишь «заворачивает» терминатор за край — при ndotl = -1 вклад строго ноль.
    float lambert = clamp((ndotl + Ambient) / (1.0 + Ambient), 0.0, 1.0);

    return col.rgb * (col.a * falloff * lambert);
}

void main() {
    vec4 src = texture(Sampler0, TexCoord);

    float depth = texture(Sampler1, TexCoord).r;
    if (depth >= 1.0) {
        // Небо: отражать свет нечему.
        OutColor = src;
        return;
    }

    vec3 world = worldFromDepth(TexCoord, depth);
    vec3 normal = faceNormal(TexCoord, depth, world);

    vec3 sum = vec3(0.0);
    sum += contribution(world, normal, L0Pos, L0Col);
    sum += contribution(world, normal, L1Pos, L1Col);
    sum += contribution(world, normal, L2Pos, L2Col);
    sum += contribution(world, normal, L3Pos, L3Col);
    sum += contribution(world, normal, L4Pos, L4Col);
    sum += contribution(world, normal, L5Pos, L5Col);
    sum += contribution(world, normal, L6Pos, L6Col);
    sum += contribution(world, normal, L7Pos, L7Col);
    sum += contribution(world, normal, L8Pos, L8Col);
    sum += contribution(world, normal, L9Pos, L9Col);
    sum += contribution(world, normal, L10Pos, L10Col);
    sum += contribution(world, normal, L11Pos, L11Col);
    sum += contribution(world, normal, L12Pos, L12Col);
    sum += contribution(world, normal, L13Pos, L13Col);
    sum += contribution(world, normal, L14Pos, L14Col);
    sum += contribution(world, normal, L15Pos, L15Col);
    sum += contribution(world, normal, L16Pos, L16Col);
    sum += contribution(world, normal, L17Pos, L17Col);
    sum += contribution(world, normal, L18Pos, L18Col);
    sum += contribution(world, normal, L19Pos, L19Col);
    sum += contribution(world, normal, L20Pos, L20Col);
    sum += contribution(world, normal, L21Pos, L21Col);
    sum += contribution(world, normal, L22Pos, L22Col);
    sum += contribution(world, normal, L23Pos, L23Col);
    sum += contribution(world, normal, L24Pos, L24Col);
    sum += contribution(world, normal, L25Pos, L25Col);
    sum += contribution(world, normal, L26Pos, L26Col);
    sum += contribution(world, normal, L27Pos, L27Col);
    sum += contribution(world, normal, L28Pos, L28Col);
    sum += contribution(world, normal, L29Pos, L29Col);
    sum += contribution(world, normal, L30Pos, L30Col);
    sum += contribution(world, normal, L31Pos, L31Col);
    sum += contribution(world, normal, L32Pos, L32Col);
    sum += contribution(world, normal, L33Pos, L33Col);
    sum += contribution(world, normal, L34Pos, L34Col);
    sum += contribution(world, normal, L35Pos, L35Col);
    sum += contribution(world, normal, L36Pos, L36Col);
    sum += contribution(world, normal, L37Pos, L37Col);
    sum += contribution(world, normal, L38Pos, L38Col);
    sum += contribution(world, normal, L39Pos, L39Col);
    sum += contribution(world, normal, L40Pos, L40Col);
    sum += contribution(world, normal, L41Pos, L41Col);
    sum += contribution(world, normal, L42Pos, L42Col);
    sum += contribution(world, normal, L43Pos, L43Col);
    sum += contribution(world, normal, L44Pos, L44Col);
    sum += contribution(world, normal, L45Pos, L45Col);
    sum += contribution(world, normal, L46Pos, L46Col);
    sum += contribution(world, normal, L47Pos, L47Col);

    // Вклад источников копится линейно, поэтому в гуще партиклов сумма легко уходила за десятку
    // и сцена выбеливалась в молоко. Экспонента насыщает её: сколько бы источников ни сошлось,
    // засветка упирается в BOOST, а разница между «один факел» и «два» остаётся видимой.
    vec3 lightAmount = vec3(1.0) - exp(-sum * GAIN);

    // Ключевое отличие от «цветного тумана»: основной вклад — множитель к уже отрисованному
    // пикселю. Тёмный булыжник становится ярким булыжником своего цвета, подкрашенным светом,
    // а не однородным пятном.
    vec3 lit = src.rgb * (vec3(1.0) + lightAmount * BOOST) + lightAmount * LIFT;

    OutColor = vec4(clamp(lit, 0.0, 1.0), src.a);
}
