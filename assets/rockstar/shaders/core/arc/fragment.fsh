#version 150

in vec2 FragCoord;
in vec4 FragColor;

uniform vec2 Size;
uniform float Thickness;
uniform float StartAngle;
uniform float EndAngle;
uniform float Smoothness;
uniform vec4 ColorModulator;

out vec4 OutColor;

const float PI = 3.14159265359;
const float TAU = 6.28318530718;

float arcSDF(vec2 p, float radius, float thickness, float startAngle, float endAngle) {
    float angle = atan(p.y, p.x);
    
    float start = mod(startAngle, TAU);
    float end = mod(endAngle, TAU);
    
    if (start < 0.0) start += TAU;
    if (end < 0.0) end += TAU;
    
    float normalizedAngle = mod(angle + TAU, TAU);
    
    float arcLength = end - start;
    if (arcLength < 0.0) arcLength += TAU;
    
    float angleFromStart = mod(normalizedAngle - start + TAU, TAU);
    
    float dist = abs(length(p) - radius) - thickness * 0.5;
    
    if (angleFromStart <= arcLength) {
        return dist;
    }
    
    float halfThickness = thickness * 0.5;
    
    vec2 startPoint = vec2(cos(start), sin(start)) * radius;
    vec2 endPoint = vec2(cos(end), sin(end)) * radius;
    
    float distToStart = length(p - startPoint) - halfThickness;
    float distToEnd = length(p - endPoint) - halfThickness;
    
    return min(distToStart, distToEnd);
}

void main() {
    vec2 center = Size * 0.5;
    vec2 p = (FragCoord * Size) - center;
    
    float radius = min(center.x, center.y) - Thickness * 0.5 - Smoothness;
    
    float dist = arcSDF(p, radius, Thickness, StartAngle, EndAngle);

    // Антиалиас в экранных пикселях (fwidth), а не фиксированной Smoothness в gui-px:
    // тонкие/мелкие кольца перестают быть «мыльными» и остаются чёткими на любом gui-scale.
    float alpha = clamp(0.5 - dist / max(fwidth(dist), 1e-4), 0.0, 1.0);
    
    vec4 finalColor = vec4(FragColor.rgb, FragColor.a * alpha);
    
    if (finalColor.a < 0.001) {
        discard;
    }
    
    OutColor = finalColor * ColorModulator;
}
