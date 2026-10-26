#version 150

in vec2 FragCoord; // нормализованная координата фрагмента [0..1] по примитиву
in vec4 FragColor;

uniform vec2 Size;        // размер квада (= область рисования) в пикселях
uniform vec2 P0, P1, P2, P3; // контрольные точки кубической Безье, в пикселях ОТНОСИТЕЛЬНО квада
uniform float Thickness;  // толщина линии, px
uniform vec4 ColorModulator;

out vec4 OutColor;

vec2 cubic(float t) {
    float u = 1.0 - t;
    return u * u * u * P0 + 3.0 * u * u * t * P1 + 3.0 * u * t * t * P2 + t * t * t * P3;
}

// расстояние от точки p до отрезка a-b
float segDist(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);
    return length(pa - ba * h);
}

void main() {
    vec2 p = FragCoord * Size; // px относительно квада — то же пространство, что P0..P3

    // мин. расстояние до кривой: семплим в полилинию и берём ближайший отрезок (distance field → плавный AA)
    const int N = 48;
    float best = 1e9;
    vec2 prev = P0;
    for (int i = 1; i <= N; i++) {
        vec2 cur = cubic(float(i) / float(N));
        best = min(best, segDist(p, prev, cur));
        prev = cur;
    }

    float halfWidth = Thickness * 0.5; // не half: зарезервированное слово GLSL, часть драйверов не компилирует
    float alpha = 1.0 - smoothstep(halfWidth - 0.6, halfWidth + 0.6, best); // 0.6px перо сглаживания

    vec4 col = vec4(FragColor.rgb, FragColor.a * alpha);
    if (col.a <= 0.0) { // alpha test
        discard;
    }
    OutColor = col * ColorModulator;
}
