#version 150

#moj_import <rockstar:common.glsl>

in vec2 FragCoord; // нормализованная координата фрагмента [0..1] по примитиву (0,0 — ВЛ, 1,1 — ПН)
in vec4 FragColor;

uniform vec2 Size;        // размер прямоугольника в пикселях
uniform vec4 Radius;      // радиусы скругления углов
uniform vec2 Smoothness;  // (внутреннее, внешнее) сглаживание кольца — как в core/border
uniform float Thickness;  // толщина обводки, px
uniform float DashLength; // длина штриха, px
uniform float GapLength;  // длина зазора, px
uniform vec4 Dashed;      // пунктир ли ребро: x=лево, y=верх, z=право, w=низ (0 — сплошное, 1 — пунктир)
uniform vec4 ColorModulator;

out vec4 OutColor;

// 1 в штрихе, 0 в зазоре (с лёгким AA по обоим краям штриха)
float dashMask(float along) {
    float period = max(DashLength + GapLength, 0.001);
    float m = mod(along, period);
    float rise = smoothstep(-0.5, 0.5, m);                                // нарастание в начале штриха
    float fall = 1.0 - smoothstep(DashLength - 0.5, DashLength + 0.5, m); // спад в конце
    return rise * fall;
}

void main() {
    vec2 p = FragCoord * Size; // px: (0,0) ВЛ → (Size) ПН
    vec2 center = Size * 0.5;

    // кольцо СКРУГЛЁННОЙ рамки (тот же SDF, что у core/border — округлые углы)
    float distance = roundedBoxSDF(center - p, center - 1.0, Radius);
    float inner = sdfAA(distance, Smoothness.x);
    float outer = sdfAA(distance, Smoothness.y);

    float ring = smoothstep(1.0 - Thickness - inner - outer, 1.0 - Thickness - outer, distance); // внутр. край
    ring *= 1.0 - smoothstep(1.0 - outer, 1.0, distance);                                        // внешн. край

    // к какому ребру принадлежит фрагмент + перим. координата s (по часовой от верх-лево, непрерывна на углах
    // одинакового типа: верх→право сшиваются у ВП-угла, т.к. там p.x≈W и p.y≈0 дают s≈W)
    float distL = p.x, distT = p.y, distR = Size.x - p.x, distB = Size.y - p.y;
    float s;
    float dashed;
    if (distT <= distR && distT <= distB && distT <= distL) { s = p.x;                                  dashed = Dashed.y; } // верх
    else if (distR <= distB && distR <= distL)              { s = Size.x + p.y;                         dashed = Dashed.z; } // право
    else if (distB <= distL)                                { s = Size.x + Size.y + (Size.x - p.x);     dashed = Dashed.w; } // низ
    else                                                    { s = 2.0 * Size.x + Size.y + (Size.y - p.y); dashed = Dashed.x; } // лево

    float alpha = ring * mix(1.0, dashMask(s), dashed);

    vec4 finalColor = vec4(FragColor.rgb, FragColor.a * alpha);
    if (finalColor.a <= 0.0) { // alpha test
        discard;
    }
    OutColor = finalColor * ColorModulator;
}
