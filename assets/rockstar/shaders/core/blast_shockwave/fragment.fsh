#version 150

in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0; // цвет
uniform sampler2D Sampler1; // глубина сцены

uniform mat4 InvViewProj;
uniform vec3 CircleCenter;  // центр взрыва относительно камеры
uniform float WorldRadius;  // радиус купола (растёт)
uniform float Thickness;    // не используется — искажается весь объём купола
uniform vec4 RingColor;     // не используется — без цвета
uniform float Strength;

out vec4 OutColor;

const float AMP = 0.026;       // амплитуда искажения
const float RIPPLES = 3.0;     // сколько концентрических волн заполняют купол
const float BLUR = 0.003;      // лёгкий радиальный смаз
const float OCCLUDE_BIAS = 0.05;
const float PI = 3.14159265;

// Ударная волна как 3D-полусфера, привязанная к миру, ЦЕЛИКОМ заполненная искажением: не тонкое
// кольцо-фронт, а весь объём купола рябит концентрическими волнами (как реальная взрывная волна,
// накатывающая на экран). Нижняя половина уходит под землю (кламп полусферы + depth) → купол.
void main() {
    vec2 uv = TexCoord;
    vec3 base = texture(Sampler0, uv).rgb;

    vec2 ndc = uv * 2.0 - 1.0;

    vec4 farClip = vec4(ndc, 1.0, 1.0);
    vec4 farWorld = InvViewProj * farClip;
    farWorld.xyz /= farWorld.w;
    vec3 rayDir = normalize(farWorld.xyz);

    // Центр перед камерой.
    float b = dot(rayDir, CircleCenter);
    if (b <= 0.0) { OutColor = vec4(base, 1.0); return; }

    float cc = dot(CircleCenter, CircleCenter);
    float R = WorldRadius;
    float dPerp = sqrt(max(0.0, cc - b * b)); // перпендикуляр центр→луч (силуэт сферы)
    float t = dPerp / R;                      // 0 в центре диска → 1 на фронте
    if (R <= 1e-4 || t >= 1.02) { OutColor = vec4(base, 1.0); return; } // вне купола

    // Точка на оболочке вдоль луча — для перекрытия и клампа полусферы.
    float inside = max(0.0, R * R - dPerp * dPerp);
    float tHit = b - sqrt(inside);
    if (tHit <= 0.0) tHit = b;
    vec3 hit = rayDir * tHit;

    // Купол = верхняя полусфера.
    if (hit.y < CircleCenter.y) { OutColor = vec4(base, 1.0); return; }

    // Перекрытие геометрией перед куполом (и нижняя полусфера под землёй).
    float depth = texture(Sampler1, uv).r;
    if (depth < 1.0) {
        vec4 clip = vec4(ndc, depth * 2.0 - 1.0, 1.0);
        vec4 sceneW = InvViewProj * clip;
        sceneW.xyz /= sceneW.w;
        float sceneDist = length(sceneW.xyz);
        if (tHit > sceneDist + max(OCCLUDE_BIAS, sceneDist * 0.005)) { OutColor = vec4(base, 1.0); return; }
    }

    // Радиальное направление на экране (градиент силуэтного поля сферы).
    vec2 grad = vec2(dFdx(dPerp), dFdy(dPerp));
    float glen = length(grad);
    if (glen < 1e-6) { OutColor = vec4(base, 1.0); return; }
    vec2 dir = grad / glen;

    // Весь купол рябит: концентрические волны по радиусу, мягко гаснут у самого фронта.
    float edgeFade = smoothstep(1.02, 0.9, t);
    float ripple = sin(t * PI * RIPPLES);
    float amp = AMP * (0.7 + 0.3 * t) * edgeFade * Strength;
    vec2 off = dir * (ripple * amp);

    vec2 suv = clamp(uv + off, vec2(0.0), vec2(1.0));
    vec3 col = texture(Sampler0, suv).rgb;

    // Лёгкий радиальный смаз по объёму купола.
    float step = edgeFade * BLUR * Strength;
    if (step > 1e-5) {
        col += texture(Sampler0, clamp(suv + dir * step,       vec2(0.0), vec2(1.0))).rgb;
        col += texture(Sampler0, clamp(suv - dir * step,       vec2(0.0), vec2(1.0))).rgb;
        col += texture(Sampler0, clamp(suv + dir * step * 2.0, vec2(0.0), vec2(1.0))).rgb;
        col += texture(Sampler0, clamp(suv - dir * step * 2.0, vec2(0.0), vec2(1.0))).rgb;
        col /= 5.0;
    }

    OutColor = vec4(col, 1.0);
}
