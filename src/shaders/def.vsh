#version 430 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec2 a_texcoord;
layout(location = 2) in mat4 model;
layout(location = 3) in mat4 projection;
layout(location = 4) in vec4 iUV;

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

    v_texcoord = a_texcoord;

    vec2 uv = a_texcoord * iUV.xy + iUV.zw;

    // v_inv_depth = 1.0 / depth;
    v_texcoord = uv;
}