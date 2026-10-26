#version 150
// Вершинный шейдер по умолчанию для шейдеров скриптов. Атрибуты привязываются по именам
// Position (vec3), UV (vec2) и VertColor (vec4, 0..255) — свой вершинник обязан называть их
// так же. У фигур без цвета на вершину атрибут выключен и приходит как (255,255,255,255).

in vec3 Position;
in vec2 UV;
in vec4 VertColor;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;

out vec2 FragCoord;
out vec4 VertexColor;

void main() {
    FragCoord = UV;
    VertexColor = VertColor / 255.0;
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
}
