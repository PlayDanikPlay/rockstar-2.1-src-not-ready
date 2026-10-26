#version 150

#moj_import <minecraft:fog.glsl>

uniform sampler2D Sampler0;

uniform vec4 ColorModulator;
uniform float FogStart;
uniform float FogEnd;
uniform vec4 FogColor;

// Проём — конус вдоль луча камера→игрок, и он РАСШИРЯЕТСЯ К КАМЕРЕ: блок у самой камеры закрывает
// пол-экрана и должен раствориться целиком, а стена на глубине игрока закрывает только его самого,
// и дыра там нужна ровно по модели. Конус постоянного угла (был сперва) на глубине игрока выедал
// всё в двух блоках вокруг него, включая стену, у которой он стоит.
uniform vec3 GhostAxis;   // единичное направление камера→игрок
uniform vec3 GhostFrom;   // ноги модели, относительно камеры
uniform vec3 GhostTo;     // голова модели, относительно камеры
uniform vec4 GhostShape;  // x — радиус у камеры, y — насколько он убывает с глубиной,
                          // z — доля радиуса под сердцевину, w — сколько прозрачности снимаем в ней
uniform float GhostBand;  // полоса затухания вокруг порога «перед моделью или уже за ней»

in float vertexDistance;
in vec4 vertexColor;
in vec2 texCoord0;
in vec3 ghostPos;

out vec4 fragColor;

void main() {
    vec4 texel = texture(Sampler0, texCoord0);

    // отсечку считаем по текстуре, а не по итоговому цвету: альфа у призрака своя и как раз уезжает
    // к нулю в проёме — на общем пороге 0.1 он бы не таял, а гас скачком
    if (texel.a < 0.1) {
        discard;
    }

    float depth = dot(ghostPos, GhostAxis);
    float side = length(ghostPos - GhostAxis * depth);
    // радиус у камеры целый, дальше убывает; за камерой (depth < 0) держим его же, иначе проём
    // вывернулся бы наизнанку. Ноль в качестве границы smoothstep — это деление на ноль
    float radius = max(GhostShape.x + GhostShape.y * max(depth, 0.0), 0.001);

    float hole = 1.0 - smoothstep(radius * GhostShape.z, radius, side);

    // Порог глубины меряется от БЛИЖАЙШЕЙ точки модели, а не от её центра. Камера смотрит сверху,
    // поэтому у стены за спиной игрока верхние точки по лучу ближе его центра — от центра они
    // считались бы «перед игроком» и растворялись, хотя закрывают пустоту над головой. От головы
    // же они честно оказываются за ней.
    vec3 body = GhostTo - GhostFrom;
    float along = clamp(dot(ghostPos - GhostFrom, body) / max(dot(body, body), 0.0001), 0.0, 1.0);
    float edge = dot(GhostFrom + body * along, GhostAxis);
    hole *= 1.0 - smoothstep(edge - GhostBand, edge + GhostBand, depth);

    // vertexColor.a несёт не прозрачность, а прогресс растворения: 0 — блок как настоящий.
    // В середине проёма снимается GhostShape.w, а не всё: блок читается насквозь, но остаётся
    float alpha = 1.0 - hole * vertexColor.a * GhostShape.w;
    // без discard прозрачная сердцевина писала бы глубину и срезала слои стены за собой
    if (alpha < 0.004) {
        discard;
    }

    vec4 color = texel * vertexColor * ColorModulator;
    color.a = texel.a * ColorModulator.a * alpha;
    fragColor = linear_fog(color, vertexDistance, FogStart, FogEnd, FogColor);
}
