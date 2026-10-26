#version 150
#moj_import <rockstar:common.glsl>

in vec2 FragCoord;
in vec2 TexCoord;
in vec4 FragColor;

uniform sampler2D Sampler0;
uniform vec2 Size;
uniform float Threshold;
uniform float Smooth;
uniform float RadiusPx;
uniform int Iterations;

out vec4 OutColor;

void main(){
    vec2 texSize = textureSize(Sampler0, 0);
    vec2 px = 1.0 / texSize;
    vec2 uv = TexCoord;

    float R = RadiusPx;
    int N = max(Iterations, 1);
    float sum = 0.0;
    float norm = 0.0;
    vec3 colorSum = vec3(0.0);

    for(int i=0;i<N;i++){
        float t = (float(i)+0.5)/float(N);
        float r = t * R;
        float a = 6.2831853 * t * 0.61803398875;

        vec2 offs = vec2(cos(a), sin(a)) * r * px;
        vec4 c = texture(Sampler0, uv + offs);

        float v = c.a;

        float w = exp(- (r*r) / (2.0*R*R));

        sum += v * w;
        colorSum += c.rgb * v * w;
        norm += w;
    }

    float field = (norm > 0.0) ? sum / norm : 0.0;
    vec3 blendedColor = (sum > 0.0) ? colorSum / sum : vec3(0.0);

    float edge = Threshold;
    float s = max(Smooth, 0.5);
    float alpha = smoothstep(edge - s/Size.y, edge + s/Size.y, field);

    if(alpha <= 0.001) discard;

    OutColor = vec4(blendedColor, alpha);
}
