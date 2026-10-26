#version 150

#moj_import <rockstar:common.glsl>

in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0;
uniform sampler2D Sampler1;
uniform vec2 Resolution;

out vec4 OutColor;

void main() {
    vec4 tex = texture(Sampler0, TexCoord);

    if (tex.a < 0.01)
        OutColor = texture(Sampler1, TexCoord);
    else
        OutColor = vec4(0.0);
}