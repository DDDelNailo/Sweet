#version 430 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec2 a_texcoord;
layout(location = 2) in mat4 model;
layout(location = 6) in mat4 projection;
layout(location = 10) in vec4 iUV;
layout(location = 11) in vec4 iColor;

layout(std140, binding = 0) uniform Camera
{
    mat4 view;
};

out vec2 v_texcoord;
out vec4 v_color;

void main()
{
    gl_Position =
        projection
        * view
        * model
        * vec4(a_position, 1.0);

    v_texcoord = a_texcoord;
    vec2 flipped_a_texcoord = vec2(a_texcoord.x, 1.0 - a_texcoord.y);
    vec2 uv = flipped_a_texcoord * iUV.zw + iUV.xy;
    v_texcoord = uv;
    v_color = iColor;
}