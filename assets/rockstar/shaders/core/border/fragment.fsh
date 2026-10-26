#version 150

#moj_import <rockstar:common.glsl>

in vec2 FragCoord; // normalized fragment coord relative to the primitive
in vec4 FragColor;

uniform vec2 Size;
uniform vec4 Radius;
uniform vec2 Smoothness;
uniform float Thickness;
uniform vec4 ColorModulator;

out vec4 OutColor;

void main() {
    vec2 center = Size * 0.5;
    float distance = roundedBoxSDF(center - (FragCoord * Size), center - 1.0, Radius);

    float inner = sdfAA(distance, Smoothness.x);
    float outer = sdfAA(distance, Smoothness.y);

    float alpha = smoothstep(1.0 - Thickness - inner - outer,
        1.0 - Thickness - outer, distance); // internal edge
    alpha *= 1.0 - smoothstep(1.0 - outer, 1.0, distance); // external edge

    vec4 finalColor = vec4(FragColor.rgb, FragColor.a * alpha);

    if (finalColor.a == 0.0) { // alpha test
        discard;
    }

    OutColor = finalColor * ColorModulator;
}