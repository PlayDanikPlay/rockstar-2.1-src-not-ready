#version 150

#moj_import <rockstar:common.glsl>
#moj_import <rockstar:slug.glsl>

// Боковая инфа острова (часы, пинг, иконка сети) красится не одним цветом, посчитанным на CPU,
// а тем, что подходит фону под НЕЙ: готовое решение лежит в Sampler1 — текстуре состояния
// (см. AdaptiveTint), где 0 значит светлый тон, 1 — тёмный, а промежуточные значения бывают
// только пока идёт анимация переключения.
// Решение берётся в одной точке на элемент (AnchorUv, её считает вершинный шейдер), а не под
// каждым пикселем: на границе светлого и тёмного фона пер-пиксельный тон разрезал цифру
// градиентом — половина светлая, половина тёмная. Ни одного glReadPixels: раньше цвет всей
// боковой инфы решала одна проба пикселя в центре экрана, то есть пиксель под самим островом.
//
// Тип примитива, как в ui_universal, определяется по UV — MSDF-глиф (текст или иконка) и
// закруглённая фигура рисуются одним дроколлом:
//   глиф:  номер в вершине (UV — em-координаты глифа) -> Sampler0/2/3
//   фигура: UV = размер примитива в пикселях (всегда > 1), текстура не нужна

in vec2 FragCoord;
in vec2 TexCoord;
flat in int GlyphIndex;
in vec4 FragColor;
in vec2 AnchorUv;    // где спрашивать состояние тона — одинаково для всех пикселей элемента

uniform sampler2D Sampler0;  // контрольные точки кривых
uniform sampler2D Sampler1;  // состояние тона: 0 — светлый, 1 — тёмный
uniform usampler2D Sampler2; // полосы глифов
uniform sampler2D Sampler3;  // таблица глифов

uniform vec4 LightColor;     // тон поверх тёмного фона
uniform vec4 DarkColor;      // тон поверх светлого фона

uniform vec4 Radius;
uniform float RectSmoothness;

uniform float Thickness;

uniform vec4 ColorModulator;

out vec4 OutColor;

void main() {
    float alpha;

    if (GlyphIndex >= 0) {
        // буква текста либо векторный значок — и то, и другое живёт кривыми
        vec2 pixelsPerEm;
        alpha = slugWeight(
                slugCoverage(Sampler0, Sampler2, Sampler3, GlyphIndex, TexCoord, 1.0, pixelsPerEm), Thickness);
    } else {
        // закруглённая фигура, размер в UV
        vec2 size = TexCoord;
        vec2 center = size * 0.5;
        float dist = roundedBoxSDF(center - (FragCoord * size), center - 1.0, Radius);
        alpha = 1.0 - smoothstep(1.0 - sdfAA(dist, RectSmoothness), 1.0, dist);
    }

    alpha *= FragColor.a;
    if (alpha <= 0.0) {
        discard;
    }

    // Готовое решение по фону — уже бинарное и уже сглаженное во времени (AdaptiveTint).
    float state = texture(Sampler1, clamp(AnchorUv, 0.0, 1.0)).r;
    vec4 tint = mix(LightColor, DarkColor, state);

    OutColor = vec4(tint.rgb, alpha * tint.a) * ColorModulator;
}
