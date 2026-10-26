#version 150

in vec2 FragCoord;// normalized fragment coord relative to the primitive
in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0;
uniform vec2 Size;// rectangle size
uniform vec4 Radius;// radius for each vertex
uniform vec2 Smoothness;// edge smoothness;
uniform float GlobalAlpha;

uniform vec4 TopLeftColor;
uniform vec4 BottomLeftColor;
uniform vec4 TopRightColor;
uniform vec4 BottomRightColor;

out vec4 OutColor;

vec4 createGradient(vec2 uv, vec4 TopLeftColor, vec4 BottomLeftColor, vec4 BottomRightColor, vec4 TopRightColor) {
    vec4 topColor = mix(TopLeftColor, TopRightColor, uv.x);
    vec4 bottomColor = mix(BottomLeftColor, BottomRightColor, uv.x);
    return mix(topColor, bottomColor, uv.y);
}

float rdist(vec2 pos, vec2 size, vec4 radius) {
    radius = min(radius, vec4(min(size.x, size.y))); // максимум — круг, дальше не ромб
    radius.xy = (pos.x > 0.0) ? radius.xy : radius.wz;
    radius.x  = (pos.y > 0.0) ? radius.x : radius.y;

    vec2 v = abs(pos) - size + radius.x;
    return min(max(v.x, v.y), 0.0) + length(max(v, 0.0)) - radius.x;
}

float ralpha(vec2 size, vec2 coord, vec4 radius, vec2 smoothness) {
    vec2 center = size * 0.5;
    float dist = rdist(center - (coord * size), center - 1.0, radius);
    return 1.0 - smoothstep(1.0 - smoothness.x, smoothness.y, dist);
}

const vec2[4] RECT_VERTICES_COORDS = vec2[] (
vec2(0.0, 0.0),
vec2(0.0, 1.0),
vec2(1.0, 1.0),
vec2(1.0, 0.0)
);

vec2 rvertexcoord(int id) {
    return RECT_VERTICES_COORDS[id % 4];
}

void main() {
    vec4 gradientColor = createGradient(FragCoord, TopLeftColor, BottomLeftColor, BottomRightColor, TopRightColor);

    float alpha = ralpha(Size, FragCoord, Radius, Smoothness);
    vec4 color = vec4(gradientColor.rgb, gradientColor.a * alpha) * texture(Sampler0, TexCoord);

    if (color.a == 0.0) { // alpha test
        discard;
    }

    OutColor = vec4(color.rgb, color.a * GlobalAlpha);
}