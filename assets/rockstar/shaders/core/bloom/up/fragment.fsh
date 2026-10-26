#version 150

#moj_import <rockstar:common.glsl>

in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0;
uniform sampler2D Sampler1;
uniform vec2 Resolution;
uniform float Offset;

out vec4 OutColor;

vec4 addmix(vec2 offset) {
    vec4 color = texture(Sampler0, TexCoord + offset);
    color = vec4(color.rgb, color.a < 0.01 ? 0.0 : 1.0);
    return color;
}

void main() {
    vec2 off = vec2((Offset + 0.5) * 0.5 * Resolution);

    vec4 color = texture(Sampler0, TexCoord);

    color += addmix(off);
    color += addmix(-off);
    color += addmix(vec2(off.x, -off.y));
    color += addmix(vec2(-off.x, off.y));

    OutColor = color / 4.0;
}