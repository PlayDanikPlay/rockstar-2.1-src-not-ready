#version 150

#moj_import <rockstar:common.glsl>

in vec2 FragCoord;
in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0;
uniform vec2 Size;
uniform vec4 Radius;
uniform float Smoothness;
uniform float CornerSmoothness;
uniform float GlobalAlpha;

// DistortStrength -> сила преломления у края (как Strength в jump_shockwave).
// BaseAlpha       -> непрозрачность тела стекла.
// Остальные Fresnel*-юниформы не используются (держим активными в конце).
uniform float FresnelPower;
uniform vec3 FresnelColor;
uniform float FresnelAlpha;
uniform float BaseAlpha;
uniform bool FresnelInvert;
uniform float FresnelMix;
uniform float DistortStrength; // сила искажения у края (роль distortion)
uniform float DistortRadius;   // ширина полосы искажения (px, роль blurRadius)
uniform float Aberration;      // хроматическая аберрация у кромки
uniform float Saturation;      // насыщение преломлённого фона (1 = нейтрально)

out vec4 OutColor;

float roundedBoxSDF(vec2 p, vec2 b, vec4 r, float smoothness) {
    r = min(r, vec4(min(b.x, b.y) * smoothness * 0.5));
    r.xy = (p.x > 0.0) ? r.xy : r.zw;
    r.x  = (p.y > 0.0) ? r.x : r.y;
    vec2 q = abs(p) - b + r.x;
    vec2 q_clamped = max(q, 0.0);
    float len = pow(pow(q_clamped.x, smoothness) + pow(q_clamped.y, smoothness), 1.0 / smoothness);
    return min(max(q.x, q.y), 0.0) + len - r.x;
}

// Мягкое покрытие фигуры (0.5 ровно на кромке, 1 вглубь на ширину band, 0 снаружи) —
// аналитический аналог mask + gaussianBlur из drawLiquidGlass. -p для совпадения скруглений
// с покрытием панели (sdCover).
float glassCoverage(vec2 p, vec2 b, vec4 r, float smoothness, float band) {
    return smoothstep(-band, band, -roundedBoxSDF(-p, b, r, smoothness));
}

void main() {
    vec2 center = Size * 0.5;
    vec2 halfSize = center - 1.0;
    vec2 pos = (FragCoord * Size) - center;

    // Покрытие фигуры (как в оригинале: -pos для совпадения скруглений с остальным UI).
    float sdCover = roundedBoxSDF(-pos, halfSize, Radius, CornerSmoothness);
    float alpha = clamp(0.5 - sdCover / max(fwidth(sdCover), 1e-4), 0.0, 1.0);
    if (alpha < 0.001) discard;

    float minSide = min(halfSize.x, halfSize.y);
    float thickness = clamp(DistortRadius, 2.0, minSide);  // ширина перехода (роль blurRadius)

    // Мягкое покрытие и его градиент БОЛЬШИМ шагом — 1:1 структура из drawLiquidGlass:
    // smoothAlpha = blurred mask, нормаль = normalize(grad(smoothAlpha)). Большой шаг
    // (thickness * 0.6, как stepSize = blurRadius * 0.6) сглаживает углы — отсюда «масляное»
    // стекло без резких изломов нормали (главное отличие от аналитической нормали).
    float bigStep = thickness * 0.6;
    float c  = glassCoverage(pos,                       halfSize, Radius, CornerSmoothness, thickness);
    float cl = glassCoverage(pos + vec2(-bigStep, 0.0), halfSize, Radius, CornerSmoothness, thickness);
    float cr = glassCoverage(pos + vec2( bigStep, 0.0), halfSize, Radius, CornerSmoothness, thickness);
    float cd = glassCoverage(pos + vec2(0.0, -bigStep), halfSize, Radius, CornerSmoothness, thickness);
    float cu = glassCoverage(pos + vec2(0.0,  bigStep), halfSize, Radius, CornerSmoothness, thickness);

    // Градиент покрытия указывает ВНУТРЬ панели (к большему покрытию) — это направление
    // преломления. Те же равные пиксельные шаги по обеим осям, что и в референсе.
    vec2 gradient = vec2(cr - cl, cu - cd);
    vec2 normal = length(gradient) > 1e-4 ? normalize(gradient) : vec2(0.0);

    float distToEdge = 1.0 - c;                        // 1 снаружи -> 0.5 у кромки -> 0 в центре

    // Кривая отклика края — 1:1 из drawLiquidGlass: плавный подъём по полосе + резкий пик
    // у самой кромки.
    float responseCurve = smoothstep(0.0, 1.0, distToEdge * 1.2);
    float edgePeak = smoothstep(0.6, 1.0, distToEdge);
    float strength = mix(responseCurve * 0.6, 1.0, edgePeak);

    // Магнитуда — 1:1 из drawLiquidGlass: refractStrength = strength * distortion * 2.5,
    // смещение по нормали в ДОЛЯХ ректа. DistortStrength играет роль distortion из референса.
    float refractStrength = strength * DistortStrength * 2.5;

    // Доля ректа -> texCoord. FragCoord — нормализованные координаты ректа (0..1), TexCoord —
    // его срез в полноэкранном буфере. Якобиан fwidth(TexCoord)/fwidth(FragCoord) = «весь рект
    // в texCoord» (texExtent) и НЕ зависит от gui-scale (старое Size*fwidth недосчитывало в
    // guiScale раз — отсюда слабое искажение).
    vec2 fragToTex = fwidth(TexCoord) / max(fwidth(FragCoord), vec2(1e-6));
    vec2 refractDir = normal * refractStrength * fragToTex;

    // Хроматическая аберрация (порт): красный смещается сильнее, синий слабее — цветная
    // кайма у кромки. ab — половина расщепления из drawLiquidGlass (aberration * 0.4).
    float ab = Aberration * 0.4;
    vec3 col;
    col.r = texture(Sampler0, clamp(TexCoord + refractDir * (1.0 + ab), 0.0, 1.0)).r;
    col.g = texture(Sampler0, clamp(TexCoord + refractDir,              0.0, 1.0)).g;
    col.b = texture(Sampler0, clamp(TexCoord + refractDir * (1.0 - ab), 0.0, 1.0)).b;

    // Насыщение (порт) + вибранси тёмного стекла: чуть поднимаем насыщенность, чтобы
    // затемнённый фон «играл» сквозь дымку, как у iOS.
    float luma = dot(col, vec3(0.2126, 0.7152, 0.0722));
    col = mix(vec3(luma), col, Saturation * 1.15);

    // Тёмное стекло (как у iOS в тёмной теме): затемняем множителем, а не заливкой к
    // чёрному — цвета и контраст фона сохраняются (преломление остаётся читаемым),
    // просто всё темнее. Белый tint панели убран — от него была серая дымка.
    col *= 0.45;

    // Тонкий световой ободок у кромки (порт fresnel, сильно приглушён — яркий белый
    // на тёмном теле читается как свечение).
    float fresnel = smoothstep(0.0, 1.0, strength) * 0.1;
    col += vec3(fresnel);

    float a = alpha * BaseAlpha * GlobalAlpha;
    // Держим неиспользуемые легаси-юниформы активными (иначе линкер их вырежет и findUniform -> null).
    a += (Smoothness + FresnelPower + FresnelAlpha + FresnelMix
          + FresnelColor.r + FresnelColor.g + FresnelColor.b
          + (FresnelInvert ? 1.0 : 0.0)) * 1e-7;
    a = clamp(a, 0.0, 1.0);
    if (a < 0.001) discard;

    OutColor = vec4(col, a);
}
