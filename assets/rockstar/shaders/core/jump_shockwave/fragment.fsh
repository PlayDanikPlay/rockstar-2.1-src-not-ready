#version 150

in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0;
uniform sampler2D Sampler1;

uniform mat4 InvViewProj;
uniform vec3 CircleCenter;
uniform float WorldRadius;
uniform float Thickness;
uniform vec4 RingColor;
uniform float Strength;

out vec4 OutColor;

const float REFRACT_BASE = 0.04;
const float GLOW = 1.0;
const float OCCLUDE_BIAS = 0.05;

void main() {
    vec2 uv = TexCoord;
    vec3 base = texture(Sampler0, uv).rgb;

    vec2 ndc = uv * 2.0 - 1.0;

    vec4 farClip = vec4(ndc, 1.0, 1.0);
    vec4 farWorld = InvViewProj * farClip;
    farWorld.xyz /= farWorld.w;
    vec3 rayDir = normalize(farWorld.xyz);

    if (abs(rayDir.y) < 1e-4) { OutColor = vec4(base, 1.0); return; }

    float t = CircleCenter.y / rayDir.y;
    if (t <= 0.0) { OutColor = vec4(base, 1.0); return; }

    vec3 hit = rayDir * t;

    float d = length(hit.xz - CircleCenter.xz);
    float ringDist = abs(d - WorldRadius);
    if (Thickness <= 0.0001 || ringDist >= Thickness) { OutColor = vec4(base, 1.0); return; }

    float depth = texture(Sampler1, uv).r;
    if (depth < 1.0) {
        vec4 clip = vec4(ndc, depth * 2.0 - 1.0, 1.0);
        vec4 sceneW = InvViewProj * clip;
        sceneW.xyz /= sceneW.w;
        float sceneDist = length(sceneW.xyz);
        if (t > sceneDist + max(OCCLUDE_BIAS, sceneDist * 0.005)) { OutColor = vec4(base, 1.0); return; }
    }

    float band = 1.0 - (ringDist / Thickness);
    float refrProfile = band * band;
    float bandSq = band * band;
    float glowProfile = bandSq * bandSq;

    float refr = REFRACT_BASE * refrProfile * Strength;
    vec2 grad = vec2(dFdx(d), dFdy(d));
    float glen = length(grad);
    vec2 distortion = vec2(0.0);
    if (glen > 1e-6) {
        vec2 dir = grad / glen;
        float signVal = sign(d - WorldRadius);
        distortion = dir * refr * signVal;
    }

    vec2 finalUv = clamp(uv + distortion, 0.0, 1.0);
    vec3 refracted = texture(Sampler0, finalUv).rgb;

    vec3 glow = RingColor.rgb * (glowProfile * GLOW * RingColor.a);

    OutColor = vec4(refracted + glow, 1.0);
}
