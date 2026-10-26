#version 150

// Ванильный core/terrain, переложенный на формат вершин предмета.
//
// Ванильный core/entity (на нём призрак жил раньше) домножает цвет на minecraft_mix_light —
// направленный свет сущностей. Для боковой грани это ~0.5, для нижней 0.4, и всё это поверх уже
// запечённого в вершину затенения стороны: призрак выходил заметно темнее блока, который подменял.
// Тут его нет вовсе, а карта света читается ровно как у меша чанка (minecraft_sample_lightmap,
// а не texelFetch: у второго выборка сдвинута на полтексела и блок оказывается светлее).

#moj_import <minecraft:light.glsl>
#moj_import <minecraft:fog.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV1;
in ivec2 UV2;
in vec3 Normal;

uniform sampler2D Sampler2;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform int FogShape;

out float vertexDistance;
out vec4 vertexColor;
out vec2 texCoord0;
out vec3 ghostPos;

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    vertexDistance = fog_distance(Position, FogShape);
    vertexColor = Color * minecraft_sample_lightmap(Sampler2, UV2);
    texCoord0 = UV0;

    // Position приходит уже относительно камеры (стек кадра — поворот камеры, а сам блок сдвинут
    // на pos - camera), а поворот длин не меняет: проём считается теми же блоками, что и на Java.
    ghostPos = Position;
}
