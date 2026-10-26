#version 150

#moj_import <rockstar:slug.glsl>

in vec2 TexCoord;
in vec4 FragColor;
in vec2 GlobalPos;
flat in int GlyphIndex;

uniform sampler2D Sampler0;   // контрольные точки кривых
uniform usampler2D Sampler1;  // полосы: заголовки и адреса кривых
uniform sampler2D Sampler2;   // таблица глифов

uniform float Weight;
uniform float Softness;
uniform vec4 ColorModulator;

uniform int EnableFadeout;
uniform float FadeoutStart;
uniform float FadeoutEnd;
uniform float FadeinStart;
uniform float FadeinEnd;
uniform float MaxWidth;
uniform float TextPosX;

out vec4 OutColor;

void main() {
    if (GlyphIndex < 0) discard;

    vec2 pixelsPerEm;
    float coverage = slugWeight(
            slugCoverage(Sampler0, Sampler1, Sampler2, GlyphIndex, TexCoord, Softness, pixelsPerEm), Weight);

    vec4 color = vec4(FragColor.rgb, FragColor.a * coverage);

    if (EnableFadeout != 0) {
        float fade = 1.0;
        float normalizedX = (GlobalPos.x - TextPosX) / MaxWidth;
        if (normalizedX > FadeoutStart) fade *= 1.0 - smoothstep(FadeoutStart, FadeoutEnd, normalizedX);
        if (FadeinEnd > 0.0 && normalizedX < FadeinEnd) fade *= smoothstep(FadeinStart, FadeinEnd, normalizedX);
        color.a *= fade;
    }

    OutColor = color * ColorModulator;
}
