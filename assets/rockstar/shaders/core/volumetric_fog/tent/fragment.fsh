#version 150

in vec2 TexCoord;

uniform sampler2D Sampler0;
uniform vec2 TexelSize;

out vec4 OutColor;

void main() {
    vec2 offset = TexelSize * 0.5;

    OutColor = 0.25 * (texture(Sampler0, TexCoord + vec2( offset.x,  offset.y))
                     + texture(Sampler0, TexCoord + vec2(-offset.x,  offset.y))
                     + texture(Sampler0, TexCoord + vec2( offset.x, -offset.y))
                     + texture(Sampler0, TexCoord + vec2(-offset.x, -offset.y)));
}
