#version 430 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec2 a_texcoord;

layout(std140, binding = 0) uniform Camera
{
    mat4 projection;
    mat4 view;
};

out vec2 v_texcoord;

void main()
{
    gl_Position =
        uProjection
        * uView
        * uModel
        * vec4(a_position, 1.0);

    v_texcoord = a_texcoord;
}