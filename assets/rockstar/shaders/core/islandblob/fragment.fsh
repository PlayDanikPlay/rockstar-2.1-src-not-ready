#version 150

#moj_import <rockstar:common.glsl>

in vec2 FragCoord;
in vec4 FragColor;

uniform vec2 Size;          // размер квада в px (локальное пространство фигур)
uniform vec2 RectCenter;    // центр пилюли острова (локальные px)
uniform vec2 RectHalf;      // половина размера пилюли
uniform vec4 RectRadius;    // радиусы углов пилюли
uniform vec2 CircleCenter;  // центр кружка (музыка)
uniform float CircleRadius; // радиус кружка
uniform float Smooth;       // мягкость слияния (k у smin) — толщина «шейки» метабола
uniform float Outline;      // ширина обводки в px
uniform vec4 FillColor;     // заливка тела
uniform vec4 OutlineColor;  // цвет обводки
uniform float GlobalAlpha;

out vec4 OutColor;

// Полиномиальный smooth-min: сливает две SDF в одну гладкую поверхность с вогнутой
// «шейкой» между ними — это и есть настоящий metaball для двух известных фигур.
float smin(float a, float b, float k) {
    if (k <= 0.0001) return min(a, b);
    float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}

void main() {
    vec2 p = FragCoord * Size;

    float dRect = roundedBoxSDF(p - RectCenter, RectHalf, RectRadius);
    float dCircle = length(p - CircleCenter) - CircleRadius;
    float d = smin(dRect, dCircle, Smooth);

    // Пиксельный шаг поля -> плавный антиалиас и переход обводки, не зависящий от gui-scale.
    float aa = max(fwidth(d), 1e-4);

    // Обводка НАРУЖУ (outset) — как рамка x-1,y-1,w+2 у обычной пилюли, чтобы переключение
    // metaball <-> обычный фон в конце анимации было бесшовным.
    // fillMask  — тело (d < 0)
    // outerMask — тело + обводка наружу (d < Outline)
    // ring      — сама обводка: непрерывная полоса ВНЕ кромки объединения, включая шейку,
    //             плавно переходящая в кромку обоих частей.
    float fillMask  = 1.0 - smoothstep(0.0, aa, d);
    float outerMask = 1.0 - smoothstep(Outline, Outline + aa, d);
    float ring      = clamp(outerMask - fillMask, 0.0, 1.0);

    float fa = FillColor.a * fillMask;
    float oa = OutlineColor.a * ring;

    // fill (d<0) и ring (0<d<Outline) не пересекаются — простой композит с приоритетом заливки.
    float a = fa + oa * (1.0 - fa);
    if (a <= 0.001) discard;

    vec3 rgb = (FillColor.rgb * fa + OutlineColor.rgb * oa * (1.0 - fa)) / max(a, 1e-4);

    a *= GlobalAlpha;
    a += FragColor.a * 1e-7; // держим атрибут живым
    if (a <= 0.001) discard;

    OutColor = vec4(rgb, a);
}
