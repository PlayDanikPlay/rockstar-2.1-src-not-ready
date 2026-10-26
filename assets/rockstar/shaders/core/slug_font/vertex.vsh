#version 150

in vec3 Position;
in vec2 UV0;
in vec4 Color;
in ivec2 UV2;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;

out vec2 TexCoord;
out vec4 FragColor;
out vec2 GlobalPos;
// Номер глифа один на все четыре вершины квадрата — интерполировать его нечем и незачем.
flat out int GlyphIndex;

void main() {
    // UV0 — координата сэмпла в em-квадрате глифа: перо в нуле, ось Y вверх. Дальше по ней
    // и считается всё: и номер полосы, и положение кривых относительно пикселя.
    TexCoord = UV0;
    FragColor = Color;
    GlobalPos = Position.xy;
    // Формат вершин отдаёт UV2 знаковой парой 16-битных, поэтому старшая половина номера
    // едет во втором компоненте: в одну не влезли бы шрифты целиком.
    // Ноль означает «это не буква»: universal-батч кладёт в один дроколл и плашки, и текст.
    GlyphIndex = UV2.x + UV2.y * 32768 - 1;

    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
}
