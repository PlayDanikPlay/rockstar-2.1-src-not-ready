#version 150

in vec3 Position;
in vec2 UV0;
in vec4 Color;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;

flat out float CommandIndex;
out vec2 FragCoord;
out vec2 GlobalPos;
out vec4 FragColor;

void main() {
    CommandIndex = UV0.x;
    int corner = int(UV0.y + 0.5);
    if (corner == 0) FragCoord = vec2(0.0, 0.0);
    else if (corner == 1) FragCoord = vec2(0.0, 1.0);
    else if (corner == 2) FragCoord = vec2(1.0, 1.0);
    else FragCoord = vec2(1.0, 0.0);
    GlobalPos = Position.xy;
    FragColor = Color;
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
}
