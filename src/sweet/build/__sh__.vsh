#version 430 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec2 a_texcoord;
layout(location = 2) in mat4 model;
layout(location = 6) in mat4 projection;
layout(location = 10) in vec4 iUV;

layout(std140, binding = 0) uniform Camera
{
    mat4 view;
};

out vec2 v_texcoord;

void main()
{
    gl_Position =
        projection
        * view
        * model
        * vec4(a_position, 1.0);
    // gl_Position.w = 1;

    v_texcoord = a_texcoord;

    vec2 uv = a_texcoord * iUV.zw + iUV.xy;

    v_texcoord = uv;
}