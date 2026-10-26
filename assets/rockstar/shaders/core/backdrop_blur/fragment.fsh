#version 150

#moj_import <rockstar:common.glsl>

in vec2 FragCoord;
in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0;
uniform vec2 Size;
uniform vec4 Radius;
uniform float Smoothness;   // тонкий AA боков/верха (px)
uniform float FadeStart;    // 0..1 по высоте: до этого блюр полный
uniform float FadeEnd;      // 0..1: тут блюр плавно уходит в ноль
uniform vec2 ClampMin;      // UV-границы окна (с запасом): семплинг НЕ выходит за меню → не берёт небо
uniform vec2 ClampMax;
uniform vec4 ColorModulator;

out vec4 OutColor;

void main() {
    // Мягкий (AA) край рамки — как в squircle_texture. Radius=0 → просто прямоугольник.
    vec2 center = Size * 0.5;
    float dist = roundedBoxSDF(center - (FragCoord * Size), center - 1.0, Radius);
    float edge = 1.0 - smoothstep(1.0 - sdfAA(dist, Smoothness), 1.0, dist);

    // Плавный вертикальный фейд блюра. FragCoord.y: 0 (верх) → 1 (низ).
    float vfade = 1.0 - smoothstep(FadeStart, FadeEnd, FragCoord.y);

    float alpha = edge * vfade;
    if (alpha <= 0.001) discard;

    // Клип семплинга к области окна (с запасом на размах блюра): пиксели у/за краем окна берут
    // ближайший ВНУТРЕННИЙ (без неба) столбец блюра, а не мир за окном.
    vec2 uv = clamp(TexCoord, ClampMin, ClampMax);

    // Цвет = размытый фон (RGB), альфа = маска. FragColor/ColorModulator — тинт/модулятор (обычно белые).
    OutColor = vec4(texture(Sampler0, uv).rgb, alpha) * FragColor * ColorModulator;
}
