#version 150

uniform float AmbientLightFactor;
uniform float SkyFactor;
uniform float BlockFactor;
uniform int UseBrightLightmap;
uniform vec3 SkyLightColor;
uniform float NightVisionFactor;
uniform float DarknessScale;
uniform float DarkenWorldFactor;
uniform float BrightnessFactor;
uniform vec3 RockstarNightTint;
uniform float RockstarNightStrength;

in vec2 texCoord;

out vec4 fragColor;

float get_brightness(float level) {
    float curved_level = level / (4.0 - 3.0 * level);
    return mix(curved_level, 1.0, AmbientLightFactor);
}

vec3 notGamma(vec3 x) {
    vec3 nx = 1.0 - x;
    return 1.0 - nx * nx * nx * nx;
}

void main() {
    float block_brightness = get_brightness(floor(texCoord.x * 16) / 15) * BlockFactor;
    float sky_brightness = get_brightness(floor(texCoord.y * 16) / 15) * SkyFactor;

    vec3 color = vec3(
        block_brightness,
        block_brightness * ((block_brightness * 0.6 + 0.4) * 0.6 + 0.4),
        block_brightness * (block_brightness * block_brightness * 0.6 + 0.4)
    );

    if (UseBrightLightmap != 0) {
        color = mix(color, vec3(0.99, 1.12, 1.0), 0.25);
        color = clamp(color, 0.0, 1.0);
    } else {
        color += SkyLightColor * sky_brightness;
        color = mix(color, vec3(0.75), 0.04);

        vec3 darkened_color = color * vec3(0.7, 0.6, 0.6);
        color = mix(color, darkened_color, DarkenWorldFactor);
    }

    if (NightVisionFactor > 0.0) {
        float max_component = max(color.r, max(color.g, color.b));
        if (max_component < 1.0) {
            vec3 bright_color = color / max_component;
            color = mix(color, bright_color, NightVisionFactor);
        }
    }

    if (UseBrightLightmap == 0) {
        color = clamp(color - vec3(DarknessScale), 0.0, 1.0);
    }

    vec3 ng = notGamma(color);
    color = mix(color, ng, BrightnessFactor);
    color = mix(color, vec3(0.75), 0.04);
    color = clamp(color, 0.0, 1.0);

    if (RockstarNightStrength > 0.0) {
        // Skip the (15,15) corner — GUI/hotbar items sample only this pixel and
        // tinting it would colour the inventory/hotbar icons.
        bool guiCorner = texCoord.x >= 15.0 / 16.0 && texCoord.y >= 15.0 / 16.0;
        if (!guiCorner) {
            // Build a deterministic night lightmap from raw block/sky levels.
            // Independent of the user's gamma slider (BrightnessFactor), so the
            // result looks identical for players regardless of brightness setting.
            float bbLevel = floor(texCoord.x * 16.0) / 15.0;
            float sbLevel = floor(texCoord.y * 16.0) / 15.0;
            float bb = bbLevel / (4.0 - 3.0 * bbLevel);
            float sb = sbLevel / (4.0 - 3.0 * sbLevel);
            // Block light dominates at night; sky light is heavily attenuated.
            float lit = max(bb, sb * 0.4);
            // Visibility floor — keeps caves and dark spots navigable.
            lit = mix(0.42, 1.0, lit);
            // Dim/mid areas carry the night tint; bright spots (torches, lava)
            // desaturate smoothly toward white so highlights stay readable.
            float desat = smoothstep(0.55, 1.0, lit);
            vec3 night = mix(RockstarNightTint, vec3(1.0), desat) * lit;
            color = mix(color, night, RockstarNightStrength);
        }
    }

    fragColor = vec4(color, 1.0);
}
