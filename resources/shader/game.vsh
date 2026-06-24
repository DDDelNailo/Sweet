#version 430 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec2 a_texcoord;
layout(location = 2) in vec3 a_normal;
layout(location = 3) in mat4 model;
layout(location = 7) in mat4 projection;
layout(location = 11) in vec4 iUV;
layout(location = 12) in vec4 iColor;

layout(std140, binding = 1) uniform Camera
{
    mat4 view;
};

out vec2 v_texcoord;
out vec4 v_color;
out vec3 v_normal;
out vec3 v_frag_pos;

void main()
{
    vec4 world_position = model * vec4(a_position, 1.0);
    gl_Position = projection * view * world_position;

    v_frag_pos = vec3(world_position);

    v_texcoord = a_texcoord;
    vec2 flipped_a_texcoord = vec2(a_texcoord.x, 1.0 - a_texcoord.y);
    vec2 uv = flipped_a_texcoord * iUV.zw + iUV.xy;
    v_texcoord = uv;
    
    v_color = iColor;
    
    v_normal = mat3(transpose(inverse(model))) * a_normal;
}