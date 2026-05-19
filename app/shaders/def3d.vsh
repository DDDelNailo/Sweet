#version 430 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec2 a_texcoord;
layout(location = 2) in vec3 a_color;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;

out vec2 v_texcoord;
out vec3 v_color;

void main()
{
    gl_Position =
        uProjection
        * uView
        * uModel
        * vec4(a_position, 1.0);

    v_texcoord = a_texcoord;
    v_color = a_color;
}