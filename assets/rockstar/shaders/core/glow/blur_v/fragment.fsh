#version 150

#moj_import <rockstar:common.glsl>

in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0;
uniform vec2 Resolution;
uniform float Offset;

out vec4 OutColor;

// See blur_h/fragment.fsh — same 5-tap linear-sampled Gaussian.
const float O1  = 1.3846153846;
const float O2  = 3.2307692308;
const float WC0 = 0.2270270270;
const float WC1 = 0.3162162162;
const float WC2 = 0.0702702703;

void main() {
    vec2 step = vec2(0.0, Resolution.y * Offset);

    vec4 c  = texture(Sampler0, TexCoord) * WC0;
    c += texture(Sampler0, TexCoord + step * O1) * WC1;
    c += texture(Sampler0, TexCoord - step * O1) * WC1;
    c += texture(Sampler0, TexCoord + step * O2) * WC2;
    c += texture(Sampler0, TexCoord - step * O2) * WC2;

    OutColor = c;
}
