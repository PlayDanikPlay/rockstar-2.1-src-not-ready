#version 150
// Шапка фрагментного шейдера скрипта: дописывается к тексту автора, если он не начал с
// собственного #version. Ниже приклеивается include/common.glsl, а следом #line 0, чтобы
// номера строк в ошибках компиляции считались от текста автора, а не от шапки.
//
// #version обязан быть ПЕРВЫМ: комментарий перед ним спецификация разрешает, но часть драйверов
// на этом спотыкается, а PyShader.prepare решает по нему же, дописывать шапку или нет.

in vec2 FragCoord;
#define TexCoord FragCoord

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform mat4 InvViewProj;
uniform vec3 CamPos;
uniform vec2 Size;
uniform vec2 Resolution;
uniform vec2 MousePos;
uniform float Time;
uniform float GuiScale;
uniform vec4 Color;
uniform sampler2D Sampler0;
uniform sampler2D Sampler1;
uniform sampler2D Sampler2;
uniform sampler2D Sampler3;

out vec4 fragColor;
#define OutColor fragColor
