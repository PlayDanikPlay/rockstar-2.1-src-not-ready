#version 150

// Состояние адаптивного тона: 0 — светлый тон (фон тёмный), 1 — тёмный (фон светлый).
// Копится между кадрами (ping-pong), поэтому переключение можно анимировать во времени, не таща
// цвет на CPU. Решение по фону БИНАРНОЕ и с гистерезисом — тон не может «зависнуть» серым на
// средне-ярком фоне; промежуточные значения бывают только пока идёт сама анимация перехода.

in vec2 TexCoord;

uniform sampler2D Sampler0;  // размытая копия кадра — фон
uniform sampler2D Sampler1;  // состояние прошлого кадра

uniform vec2 Threshold;      // (lo, hi) яркости — пороги триггера Шмитта
uniform vec2 Probe;          // разброс проб фона в UV
uniform float Rate;          // какую долю пути к цели проходим за этот кадр (1 — мгновенно)

out vec4 OutColor;

float backdropLuma(vec2 uv) {
    return dot(texture(Sampler0, clamp(uv, 0.0, 1.0)).rgb, vec3(0.2126, 0.7152, 0.0722));
}

void main() {
    // Блюр уже усреднил окрестность, крест снимает локальный перекос — тёмная ветка ровно под
    // глифом при светлом фоне вокруг него.
    float luma = backdropLuma(TexCoord) * 2.0
        + backdropLuma(TexCoord + vec2(Probe.x, 0.0)) + backdropLuma(TexCoord - vec2(Probe.x, 0.0))
        + backdropLuma(TexCoord + vec2(0.0, Probe.y)) + backdropLuma(TexCoord - vec2(0.0, Probe.y));
    luma /= 6.0;

    float prev = texture(Sampler1, TexCoord).r;

    // Гистерезис: уйти в тёмный тон можно только выше hi, вернуться в светлый — только ниже lo.
    // На пёстром фоне (листва, вода) яркость болтается вокруг порога, и без этого тон дребезжал бы.
    float target = prev > 0.5 ? step(Threshold.x, luma) : step(Threshold.y, luma);

    float state = mix(prev, target, Rate);
    // Экспонента подходит к цели асимптотически — дожимаем хвост, чтобы в покое было ровно 0 или 1.
    if (abs(target - state) < 0.01) state = target;

    OutColor = vec4(state, state, state, 1.0);
}
