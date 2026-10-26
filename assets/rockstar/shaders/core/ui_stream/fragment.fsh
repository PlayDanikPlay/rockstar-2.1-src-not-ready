#version 150

#moj_import <rockstar:slug.glsl>

flat in float CommandIndex;
in vec2 FragCoord;
in vec2 GlobalPos;
in vec4 FragColor;

uniform sampler2D Sampler0;
uniform sampler2D Sampler1;
uniform sampler2D Sampler2;
uniform sampler2D Sampler3;
uniform sampler2D Sampler4;
uniform sampler2D Sampler5;
uniform sampler2D Sampler6;
uniform sampler2D Sampler7;
uniform sampler2D Sampler8;
// Хранилище глифов идёт после страниц текстур: страницы заняты картинками интерфейса.
uniform sampler2D Sampler9;   // контрольные точки кривых
uniform usampler2D Sampler10; // полосы глифов
uniform sampler2D Sampler11;  // таблица глифов
uniform vec4 ColorModulator;

out vec4 OutColor;

vec4 commandTexel(int row, int column) {
    return texelFetch(Sampler0, ivec2(column, row), 0);
}

vec4 decodeCommand(vec4 encoded, vec4 minValue, vec4 maxValue) {
    return mix(minValue, maxValue, encoded);
}

vec4 samplePage(int page, vec2 uv) {
    if (page == 0) return texture(Sampler1, uv);
    if (page == 1) return texture(Sampler2, uv);
    if (page == 2) return texture(Sampler3, uv);
    if (page == 3) return texture(Sampler4, uv);
    if (page == 4) return texture(Sampler5, uv);
    if (page == 5) return texture(Sampler6, uv);
    if (page == 6) return texture(Sampler7, uv);
    if (page == 7) return texture(Sampler8, uv);
    return texture(Sampler8, uv);
}

vec2 pageSize(int page) {
    if (page == 0) return vec2(textureSize(Sampler1, 0));
    if (page == 1) return vec2(textureSize(Sampler2, 0));
    if (page == 2) return vec2(textureSize(Sampler3, 0));
    if (page == 3) return vec2(textureSize(Sampler4, 0));
    if (page == 4) return vec2(textureSize(Sampler5, 0));
    if (page == 5) return vec2(textureSize(Sampler6, 0));
    if (page == 6) return vec2(textureSize(Sampler7, 0));
    if (page == 7) return vec2(textureSize(Sampler8, 0));
    return vec2(textureSize(Sampler8, 0));
}

// Полоса сглаживания края не уже пикселя кадра: расстояние меряется в единицах
// примитива, а матрица может сжать его на экране (см. sdfAA в common.glsl).
float sdfAA(float dist, float smoothness) {
    return max(smoothness, fwidth(dist));
}

float uiBoxSDF(vec2 p, vec2 b, vec4 r, float s) {
    r = min(r, vec4(min(b.x, b.y) * s * 0.5));
    r.xy = (p.x > 0.0) ? r.xy : r.zw;
    r.x = (p.y > 0.0) ? r.x : r.y;
    vec2 q = abs(p) - b + r.x;
    vec2 qc = max(q, 0.0);
    float len = pow(pow(qc.x, s) + pow(qc.y, s), 1.0 / s);
    return min(max(q.x, q.y), 0.0) + len - r.x;
}

void main() {
    int row = int(CommandIndex + 0.5);
    // Границы полей обязаны совпадать с COMMAND_MIN/COMMAND_MAX в LowDrawUiBatch: третье поле
    // теперь хранит номер глифа, и прежний потолок в 64 ужимал его в тысячу раз — на экране от
    // букв оставались отдельные крапины чужих глифов.
    vec4 c0 = decodeCommand(commandTexel(row, 0),
            vec4(0.0, 0.0, 0.0, -1.0), vec4(8.0, 16.0, 32768.0, 1.0));
    vec4 c1 = decodeCommand(commandTexel(row, 1),
            vec4(0.0), vec4(4096.0, 4096.0, 64.0, 64.0));
    vec4 radius = commandTexel(row, 2) * 512.0;
    vec4 border = decodeCommand(commandTexel(row, 3),
            vec4(0.0), vec4(64.0, 64.0, 64.0, 1.0));
    vec4 clip = decodeCommand(commandTexel(row, 4), vec4(-4096.0), vec4(4096.0));
    vec4 uvBounds = decodeCommand(commandTexel(row, 5), vec4(-2.0), vec4(2.0));
    vec4 fade0 = decodeCommand(commandTexel(row, 6),
            vec4(0.0, -4096.0, 0.0, -16.0), vec4(1.0, 4096.0, 4096.0, 16.0));
    vec4 fade1 = decodeCommand(commandTexel(row, 7),
            vec4(-16.0, -16.0, -16.0, 0.0), vec4(16.0, 16.0, 16.0, 1.0));

    if (GlobalPos.x < clip.x || GlobalPos.y < clip.y || GlobalPos.x >= clip.z || GlobalPos.y >= clip.w) discard;

    int mode = int(c0.x + 0.5);
    int page = int(c0.y + 0.5);
    vec2 uv = mix(uvBounds.xy, uvBounds.zw, FragCoord);
    vec4 color = FragColor;

    if (mode == 1 || mode == 2 || mode == 4) {
        if (mode == 1 && border.w > 0.5) {
            vec4 top = mix(commandTexel(row, 8), commandTexel(row, 11), FragCoord.x);
            vec4 bottom = mix(commandTexel(row, 9), commandTexel(row, 10), FragCoord.x);
            color = mix(top, bottom, FragCoord.y);
        }
        vec2 size = c1.xy;
        vec2 center = size * 0.5;
        float dist = uiBoxSDF(center - (FragCoord * size), center - 1.0, radius, c1.z);
        float alpha;
        if (mode == 2) {
            float outer = sdfAA(dist, border.z);
            alpha = smoothstep(1.0 - border.x - border.y - outer,
                    1.0 - border.x - outer, dist);
            alpha *= 1.0 - smoothstep(1.0 - outer, 1.0, dist);
        } else {
            alpha = 1.0 - smoothstep(1.0 - sdfAA(dist, c1.w), 1.0, dist);
        }
        if (mode == 4) color *= samplePage(page, uv);
        color.a *= alpha;
    } else if (mode == 3) {
        // uv тут — em-координаты сэмпла в квадрате глифа, а c0.z — номер глифа плюс единица.
        vec2 pixelsPerEm;
        float alpha = slugCoverage(Sampler9, Sampler10, Sampler11, int(c0.z + 0.5) - 1, uv, c1.w, pixelsPerEm);
        color.a *= slugWeight(alpha, c0.w);
        if (fade0.x > 0.5 && fade0.z > 0.0) {
            float normalizedX = (GlobalPos.x - fade0.y) / fade0.z;
            float fadeAlpha = 1.0;
            if (normalizedX > fade0.w) fadeAlpha *= 1.0 - smoothstep(fade0.w, fade1.x, normalizedX);
            if (fade1.z > 0.001 && normalizedX < fade1.z) fadeAlpha *= smoothstep(fade1.y, fade1.z, normalizedX);
            color.a *= fadeAlpha;
        }
    } else if (mode == 5) {
        color *= samplePage(page, uv);
    }

    if (color.a == 0.0) discard;
    OutColor = color * ColorModulator;
}
