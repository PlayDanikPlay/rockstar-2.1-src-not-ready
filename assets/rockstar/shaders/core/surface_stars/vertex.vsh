#version 150

in vec3 Position;
in vec2 UV0;
in vec4 Color;

uniform mat4 ViewProj;
uniform vec3 Offset;
uniform vec3 CamRight;
uniform vec3 CamUp;
uniform vec4 Tint;
uniform float Time;
uniform float Size;
uniform float Twinkle;
uniform float Spikes;
uniform vec2 Fade;
uniform float PixelScale;

out vec2 Uv;
out vec4 Col;
out float Spike;
out float Rot;
out float Glow;

const float TAU = 6.2831853;
const float LIFT = 0.015;
const float MIN_PX = 8.0;

void main() {
    int corner = int(UV0.x + 0.5);
    int face = int(UV0.y + 0.5);

    int axis = face / 2;
    float dir = (face - axis * 2) == 0 ? 1.0 : -1.0;
    vec3 normal = vec3(axis == 0 ? dir : 0.0, axis == 1 ? dir : 0.0, axis == 2 ? dir : 0.0);

    vec2 local = vec2((corner == 1 || corner == 2) ? 0.5 : -0.5,
                      (corner == 2 || corner == 3) ? 0.5 : -0.5);

    float phase = Color.r;
    float sizeVar = 0.45 + Color.g * Color.g * 1.15;
    float spikeVar = Color.b;
    float bright = Color.a;

    float beat = Time * (0.75 + Color.g * 1.7) + phase * TAU;
    float slow = 0.5 + 0.5 * sin(Time * 0.29 + phase * 23.0);
    float pulse = (0.5 + 0.5 * sin(beat)) * (0.3 + 0.7 * slow);
    float twinkle = mix(1.0, mix(0.12, 1.0, pulse), Twinkle);

    float size = Size * sizeVar * (0.8 + 0.2 * twinkle);

    vec3 center = Position + Offset + normal * (size * 0.35 + LIFT);
    float dist = length(center);
    vec3 toCam = -center / max(dist, 1e-4);

    float shown = max(size, dist * MIN_PX / max(PixelScale, 1.0));
    float shrink = pow(size / shown, 0.65);

    float facing = dot(normal, toCam);
    float lambert = smoothstep(0.0, 0.09, facing) * pow(clamp(facing, 0.0, 1.0), 0.35);

    float far = 1.0 - smoothstep(Fade.x, Fade.y, dist);
    float near = smoothstep(0.30, 1.10, dist);

    float alpha = Tint.a * bright * twinkle * lambert * far * near * shrink;

    Uv = local * 2.0;
    Rot = fract(phase * 1.37 + spikeVar * 0.61) * TAU;
    Spike = Spikes * (0.55 + 0.45 * spikeVar);
    Glow = 0.6 + 0.4 * smoothstep(0.4, 1.4, sizeVar);
    Col = vec4(Tint.rgb, alpha);

    // Отвёрнутая от камеры грань и дальний край затухания — это половина поля, и каждая такая искра
    // до сих пор растеризовала полный квад ради discard. Уводим квад за дальнюю плоскость: все
    // четыре угла считают одно и то же (центр у них общий), поэтому примитив отбрасывается целиком.
    if (alpha < 0.001) {
        gl_Position = vec4(0.0, 0.0, 2.0, 1.0);
        return;
    }

    vec3 offset = CamRight * (local.x * shown) + CamUp * (local.y * shown);
    gl_Position = ViewProj * vec4(center + offset, 1.0);
}
