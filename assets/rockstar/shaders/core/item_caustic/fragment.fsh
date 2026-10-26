#version 150
// Underwater caustic flow on a 2D quad. The classic ~10 sin/cos analytic
// pattern — cheap and recognisably "watery".

in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0;
uniform float Time;
uniform vec3 Accent;
uniform vec2 ItemCenter;
uniform vec4 ColorModulator;

out vec4 OutColor;

float caustic(vec2 uv, float t) {
    vec2 p = mod(uv * 6.28318, 6.28318) - 250.0;
    vec2 i = p;
    float c = 1.0;
    float inten = 0.005;
    for (int n = 0; n < 5; n++) {
        float tn = t * 0.5 + float(n);
        i = p + vec2(cos(tn - i.x) + sin(tn + i.y),
                     sin(tn - i.y) + cos(tn + i.x));
        c += 1.0 / length(vec2(p.x / (sin(i.x + tn) / inten),
                               p.y / (cos(i.y + tn) / inten)));
    }
    c /= 5.0;
    c = 1.17 - pow(c, 1.4);
    return clamp(pow(abs(c), 8.0), 0.0, 5.0);
}

void main() {
    vec4 mask = texture(Sampler0, TexCoord);
    if (mask.a < 0.01) discard;

    vec3 accent = max(Accent, vec3(0.05));
    float t = Time;

    // Recentre UVs on the item so the pattern visually follows it.
    vec2 uv = TexCoord - ItemCenter + vec2(0.5);

    float c1 = caustic(uv * 1.6, t);
    float c2 = caustic(uv * 2.4 + vec2(0.3, -0.2), t * 0.7);
    float c  = max(c1, c2 * 0.7);

    vec3 deep   = accent * 0.18;
    vec3 mid    = accent * 0.85;
    vec3 bright = mix(accent, vec3(1.0), 0.55);

    vec3 col = mix(deep, mid, smoothstep(0.0, 0.5, c));
    col = mix(col, bright * 2.4, smoothstep(0.5, 1.4, c));

    float edge = smoothstep(0.05, 0.35, mask.a);

    OutColor = vec4(col * edge, mask.a) * ColorModulator;
}
