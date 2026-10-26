#version 150

uniform sampler2D Sampler0;
uniform vec4 ColorModulator;

in vec2 texCoord0;
in vec4 vertexColor;

out vec4 fragColor;

void main() {
    // Skin alpha defines the silhouette — drop transparent pixels.
    float a = texture(Sampler0, texCoord0).a;
    if (a < 0.1) discard;

    // Per-entity tint comes from the vertex Color attribute (model.render
    // writes the entity's chosen color into every vertex). One shader,
    // every entity gets its own color.
    fragColor = vec4(vertexColor.rgb * ColorModulator.rgb, vertexColor.a * ColorModulator.a);
}
