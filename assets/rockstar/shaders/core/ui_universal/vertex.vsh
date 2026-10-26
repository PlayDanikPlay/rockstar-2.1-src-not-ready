#version 150

#moj_import <rockstar:rect.glsl>

in vec3 Position; // POSITION_TEXTURE_COLOR_LIGHT vertex attributes
in vec2 UV0;
in vec4 Color;
in ivec2 UV2;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;

out vec2 FragCoord;
out vec2 TexCoord;
out vec4 FragColor;
// Номер глифа, увеличенный на единицу: ноль означает, что примитив — не буква.
flat out int GlyphIndex;

void main() {
    FragCoord = rvertexcoord(gl_VertexID);
    TexCoord = UV0;
    FragColor = Color;
    GlyphIndex = UV2.x + UV2.y * 32768 - 1;

    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
}
