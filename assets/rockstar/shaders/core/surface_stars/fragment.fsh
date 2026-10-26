#version 150

in vec2 Uv;
in vec4 Col;
in float Spike;
in float Rot;
in float Glow;

out vec4 OutColor;

const float STAR = 0.50;
const float CORE = 0.0016;
const float HALO = 0.022;
const float ARM = 0.0009;
const float ARM_SOFT = 0.005625;
const float GAIN = 9.0;

void main() {
    float r2 = dot(Uv, Uv);
    if (r2 > 1.0) discard;

    float glow = (CORE / (r2 + CORE) * 0.90 + HALO / (r2 + HALO) * 0.30 * Glow) * (1.0 - r2);

    vec2 sp = Uv / STAR;
    float c = cos(Rot);
    float s = sin(Rot);
    vec2 q = abs(vec2(sp.x * c - sp.y * s, sp.x * s + sp.y * c));
    vec2 q2 = q * q;
    vec2 a = max(vec2(0.0), 1.0 - q);
    vec2 a2 = a * a;

    float needle = a2.x * (ARM / (ARM + q2.y)) + a2.y * (ARM / (ARM + q2.x));
    float soft = a2.x * a.x * (ARM_SOFT / (ARM_SOFT + q2.y)) + a2.y * a.y * (ARM_SOFT / (ARM_SOFT + q2.x));

    float e = (glow + (needle + soft * 0.18) * Spike * 0.55) * Col.a * GAIN;
    float alpha = 1.0 - exp(-e);
    if (alpha <= 0.004) discard;

    vec3 rgb = mix(Col.rgb, vec3(1.0), clamp((e - 1.6) * 0.22, 0.0, 1.0));
    OutColor = vec4(rgb * alpha, alpha);
}
